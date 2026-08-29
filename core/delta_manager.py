"""
core/delta_manager.py — SDD-SURVIVAL-04 / SDD-SURVIVAL-11

Portão de Contenção de Custos de IA — Sincronização Delta.

Discrimina modificações de arquivo entre:
  - Mudanças cosméticas (comentários, espaços, docstrings) → ignora totalmente
  - Mudanças de lógica interna (ifs, returns, variáveis) → marca como DIRTY (SDD-11)
  - Mudanças estruturais (def, class, import) → marca comunidade como DIRTY

A re-sumarização via LLM ocorre exclusivamente sob demanda (Lazy Summarization
JIT), evitando faturas surpresas de API em alterações triviais de código.

Conceitos-chave:
  - SSH (Structural Signature Hash): SHA-256 das linhas de assinatura pública
    (def, class, import, from), ignorando todo o miolo de implementação.
  - LBH (Logical Body Hash): SHA-256 do ast.dump estrutural do código após
    remoção de docstrings via DocstringStripper, detectando drift semântico
    mesmo sem mudança de assinatura. (SDD-SURVIVAL-11)
  - Dirty Flag Propagation: arquivo DIRTY → comunidade DIRTY.
  - Community Reconciliation: quando todos os arquivos de uma comunidade
    estão limpos, a comunidade é reconciliada de volta para CLEAN.
"""

import ast
import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Prefixos que definem linhas de assinatura estrutural pública
_STRUCTURAL_PREFIXES = ("def ", "class ", "import ", "from ")


class DocstringStripper(ast.NodeTransformer):
    """
    Transformador AST que remove docstrings de funções e classes,
    permitindo que o hash lógico do corpo ignore mudanças documentais.
    """

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            val = node.body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                node.body.pop(0)
        return node

    def visit_AsyncFunctionDef(self, node):
        # Trata funções assíncronas da mesma forma
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            val = node.body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                node.body.pop(0)
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr):
            val = node.body[0].value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                node.body.pop(0)
        return node


class DeltaManager:
    """
    Gerencia a sincronização delta entre alterações físicas de arquivos
    e o estado estrutural do grafo de comunidades no SQLite WAL.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    # ── Assinatura Estrutural ──────────────────────────────────────

    _stripper = DocstringStripper()

    def calculate_ssh(self, file_content: str) -> str:
        """
        Extrai linhas de assinatura estrutural (def, class, import, from),
        ignorando lógica interna, comentários e espaços em branco.
        Retorna um hash SHA-256 determinístico da assinatura consolidada.
        """
        structural_lines = [
            stripped
            for line in file_content.splitlines()
            if (stripped := line.strip()).startswith(_STRUCTURAL_PREFIXES)
        ]
        if not structural_lines:
            return ""
        signature = "\n".join(structural_lines)
        return hashlib.sha256(signature.encode("utf-8")).hexdigest()

    def calculate_lbh(self, file_content: str) -> str:
        """
        Calcula o Logical Body Hash (LBH) do código Python:
        parseia a AST, remove docstrings via DocstringStripper,
        gera ast.dump estrutural e retorna o SHA-256.

        Ignora comentários, espaços em branco e docstrings.
        Detecta qualquer mudança de lógica interna (ifs, returns, operadores).

        Retorna string vazia para arquivos não-Python ou com erros de parse.
        """
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            return ""
        cleaned = self._stripper.visit(tree)
        dump = ast.dump(cleaned, annotate_fields=False)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()

    # ── Processamento de Mudança ──────────────────────────────────

    def process_file_change(
        self, file_path: str, new_content: str, community_id: str
    ) -> bool:
        """
        Compara a assinatura estrutural (SSH) e o hash lógico do corpo (LBH)
        do novo conteúdo com a versão armazenada no banco.

        Retorna True se houve mudança estrutural ou semântica (DIRTY),
        False se apenas comentários, espaços ou docstrings foram alterados.
        """
        new_ssh = self.calculate_ssh(new_content)
        new_lbh = self.calculate_lbh(new_content)

        existing = self.db_manager.read_query(
            "SELECT ssh_hash, body_hash FROM files WHERE path = ?;", (file_path,)
        )

        if not existing:
            # Arquivo novo: é uma adição estrutural ao grafo
            return self._insert_new_file(
                file_path, new_content, new_ssh, new_lbh, community_id
            )

        old_ssh = existing[0][0]
        old_lbh = existing[0][1]

        ssh_changed = new_ssh != old_ssh
        lbh_changed = new_lbh != old_lbh

        if not ssh_changed and not lbh_changed:
            # Mudança estritamente cosmética (comentários, espaços, docstrings)
            return self._update_content_only(file_path, new_content, community_id)

        # Mudança estrutural e/ou semântica detectada
        return self._update_structural_change(
            file_path, new_content, new_ssh, new_lbh, community_id
        )

    # ── Lazy Summarization JIT ────────────────────────────────────

    def compile_community_summary_jit(
        self, community_id: str, cloud_llm_mock_callback
    ) -> str:
        """
        Retorna resumo do cache local se a comunidade está limpa.
        Se estiver DIRTY, consolida o conteúdo dos arquivos, aciona
        o callback da LLM, salva o resultado e limpa as flags.
        """
        community = self.db_manager.read_query(
            "SELECT is_dirty, summary_text FROM communities WHERE id = ?;",
            (community_id,),
        )
        if not community:
            raise ValueError(f"Comunidade não encontrada: {community_id}")

        is_dirty, summary_text = community[0]

        # Cache hit: comunidade limpa com resumo existente
        if is_dirty == 0 and summary_text:
            return summary_text

        # Cache miss: recompilação sob demanda
        files = self.db_manager.read_query(
            "SELECT content FROM files WHERE community_id = ?;",
            (community_id,),
        )
        payload = "\n".join(row[0] for row in files)

        new_summary = cloud_llm_mock_callback(payload)

        # Persiste o novo resumo e reconcilia flags
        self.db_manager.write_query(
            "UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;",
            (new_summary, community_id),
        )
        self.db_manager.write_query(
            "UPDATE files SET is_dirty = 0 WHERE community_id = ?;",
            (community_id,),
        )

        return new_summary

    # ── Operações internas de banco ───────────────────────────────

    def _insert_new_file(
        self,
        file_path: str,
        content: str,
        ssh_hash: str,
        body_hash: str,
        community_id: str,
    ) -> bool:
        """Registra arquivo novo no grafo e propaga DIRTY para a comunidade."""
        self.db_manager.write_query(
            "INSERT INTO files (path, content, ssh_hash, body_hash, is_dirty, community_id) "
            "VALUES (?, ?, ?, ?, 1, ?);",
            (file_path, content, ssh_hash, body_hash, community_id),
        )
        self.db_manager.write_query(
            "UPDATE communities SET is_dirty = 1 WHERE id = ?;",
            (community_id,),
        )
        return True

    def _update_content_only(
        self, file_path: str, content: str, community_id: str
    ) -> bool:
        """
        Atualiza apenas o conteúdo (mudança de lógica interna).
        Limpa o dirty flag do arquivo e reconcilia a comunidade se
        todos os seus arquivos estiverem limpos.
        """
        self.db_manager.write_query(
            "UPDATE files SET content = ?, is_dirty = 0 WHERE path = ?;",
            (content, file_path),
        )
        # Reconciliação de comunidade: limpa se nenhum arquivo restante é DIRTY
        dirty_count = self.db_manager.read_query(
            "SELECT COUNT(*) FROM files WHERE community_id = ? AND is_dirty = 1;",
            (community_id,),
        )[0][0]
        if dirty_count == 0:
            self.db_manager.write_query(
                "UPDATE communities SET is_dirty = 0 WHERE id = ?;",
                (community_id,),
            )
        return False

    def _update_structural_change(
        self,
        file_path: str,
        content: str,
        ssh_hash: str,
        body_hash: str,
        community_id: str,
    ) -> bool:
        """Atualiza arquivo com nova assinatura/corpo e propaga DIRTY para a comunidade."""
        self.db_manager.write_query(
            "UPDATE files SET content = ?, ssh_hash = ?, body_hash = ?, is_dirty = 1 "
            "WHERE path = ?;",
            (content, ssh_hash, body_hash, file_path),
        )
        self.db_manager.write_query(
            "UPDATE communities SET is_dirty = 1 WHERE id = ?;",
            (community_id,),
        )
        return True
