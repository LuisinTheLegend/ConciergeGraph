"""
core/delta_manager.py — SDD-SURVIVAL-04

Portão de Contenção de Custos de IA — Sincronização Delta.

Discrimina modificações de arquivo entre:
  - Mudanças de lógica interna (ifs, returns, variáveis) → atualiza base silenciosamente
  - Mudanças estruturais (def, class, import) → marca comunidade como DIRTY

A re-sumarização via LLM ocorre exclusivamente sob demanda (Lazy Summarization
JIT), evitando faturas surpresas de API em alterações triviais de código.

Conceitos-chave:
  - SSH (Structural Signature Hash): SHA-256 das linhas de assinatura pública
    (def, class, import, from), ignorando todo o miolo de implementação.
  - Dirty Flag Propagation: arquivo DIRTY → comunidade DIRTY.
  - Community Reconciliation: quando todos os arquivos de uma comunidade
    estão limpos, a comunidade é reconciliada de volta para CLEAN.
"""

import hashlib
from typing import Any


# Prefixos que definem linhas de assinatura estrutural pública
_STRUCTURAL_PREFIXES = ("def ", "class ", "import ", "from ")


class DeltaManager:
    """
    Gerencia a sincronização delta entre alterações físicas de arquivos
    e o estado estrutural do grafo de comunidades no SQLite WAL.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    # ── Assinatura Estrutural ──────────────────────────────────────

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
        signature = "\n".join(structural_lines)
        return hashlib.sha256(signature.encode("utf-8")).hexdigest()

    # ── Processamento de Mudança ──────────────────────────────────

    def process_file_change(
        self, file_path: str, new_content: str, community_id: str
    ) -> bool:
        """
        Compara a assinatura estrutural do novo conteúdo com a versão
        armazenada no banco. Retorna True se houve mudança estrutural
        (DIRTY), False se apenas lógica interna foi alterada.
        """
        new_ssh = self.calculate_ssh(new_content)

        existing = self.db_manager.read_query(
            "SELECT ssh_hash FROM files WHERE path = ?;", (file_path,)
        )

        if not existing:
            # Arquivo novo: é uma adição estrutural ao grafo
            return self._insert_new_file(file_path, new_content, new_ssh, community_id)

        old_ssh = existing[0][0]

        if new_ssh == old_ssh:
            # Mudança estritamente de lógica interna
            return self._update_content_only(file_path, new_content, community_id)

        # Mudança estrutural detectada
        return self._update_structural_change(
            file_path, new_content, new_ssh, community_id
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
        community_id: str,
    ) -> bool:
        """Registra arquivo novo no grafo e propaga DIRTY para a comunidade."""
        self.db_manager.write_query(
            "INSERT INTO files (path, content, ssh_hash, is_dirty, community_id) "
            "VALUES (?, ?, ?, 1, ?);",
            (file_path, content, ssh_hash, community_id),
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
        community_id: str,
    ) -> bool:
        """Atualiza arquivo com nova assinatura e propaga DIRTY para a comunidade."""
        self.db_manager.write_query(
            "UPDATE files SET content = ?, ssh_hash = ?, is_dirty = 1 WHERE path = ?;",
            (content, ssh_hash, file_path),
        )
        self.db_manager.write_query(
            "UPDATE communities SET is_dirty = 1 WHERE id = ?;",
            (community_id,),
        )
        return True
