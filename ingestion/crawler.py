"""
ingestion/crawler.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Varredura inteligente de filesystem para o Motor de Ingestão Apex.

Responsabilidades:
    - Percorrer recursivamente diretórios de projetos.
    - Respeitar padrões de ignore (.gitignore + IGNORE_DIRS do config).
    - Calcular SHA256 de cada arquivo para detecção de deltas.
    - Comparar hashes com SqliteStore para skip de arquivos inalterados.
    - Classificar arquivos por tipo (code, doc, config, conversation).
    - Detectar arquivos deletados para Garbage Collection.

Integração:
    - SqliteStore.find_node_by_hash(project_uuid, hash) → verifica se já processado.
    - SqliteStore.get_nodes_by_project(project_uuid) → lista nós existentes para GC.
    - Resultado é um CrawlReport consumido pelo Parser/Orchestrator.

Preservação de Identidade (Path-Agnostic ID):
    O doc_id de cada nó é derivado do conteúdo (hash), não do path.
    Se o arquivo mudar de pasta, o hash muda → novo nó é criado.
    Se o arquivo for renomeado sem alterar conteúdo → mesmo hash → reutiliza nó.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import os
from storage import SqliteStore
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("grafo-concierge.crawler")


# ---------------------------------------------------------------------------
# Classificação de arquivos
# ---------------------------------------------------------------------------

class FileCategory(str, Enum):
    """Categorias de arquivo detectadas automaticamente pelo Crawler.

    Mapeamento conforme spec v3.8:
        code         → .py, .js, .ts, .go, .rs, .java, .cpp, .c, .rb
        doc          → .md, .txt, .rst, .adoc
        config       → .json, .yaml, .yml, .toml, .env, .ini, .cfg
        conversation → .log, .chat
        unknown      → extensões não mapeadas
    """
    CODE = "code"
    DOC = "doc"
    CONFIG = "config"
    CONVERSATION = "conversation"
    UNKNOWN = "unknown"


# Mapeamento extensão → categoria (conforme tabela da API v3.8)
EXTENSION_MAP: dict[str, FileCategory] = {
    # Code
    ".py": FileCategory.CODE,
    ".js": FileCategory.CODE,
    ".ts": FileCategory.CODE,
    ".tsx": FileCategory.CODE,
    ".jsx": FileCategory.CODE,
    ".go": FileCategory.CODE,
    ".rs": FileCategory.CODE,
    ".java": FileCategory.CODE,
    ".cpp": FileCategory.CODE,
    ".c": FileCategory.CODE,
    ".h": FileCategory.CODE,
    ".hpp": FileCategory.CODE,
    ".rb": FileCategory.CODE,
    ".cs": FileCategory.CODE,
    ".swift": FileCategory.CODE,
    ".kt": FileCategory.CODE,
    ".php": FileCategory.CODE,
    ".lua": FileCategory.CODE,
    ".sh": FileCategory.CODE,
    ".bash": FileCategory.CODE,
    ".ps1": FileCategory.CODE,
    ".sql": FileCategory.CODE,
    ".r": FileCategory.CODE,
    ".scala": FileCategory.CODE,
    ".ex": FileCategory.CODE,
    ".exs": FileCategory.CODE,
    # Doc
    ".md": FileCategory.DOC,
    ".txt": FileCategory.DOC,
    ".rst": FileCategory.DOC,
    ".adoc": FileCategory.DOC,
    ".org": FileCategory.DOC,
    # Config
    ".json": FileCategory.CONFIG,
    ".yaml": FileCategory.CONFIG,
    ".yml": FileCategory.CONFIG,
    ".toml": FileCategory.CONFIG,
    ".env": FileCategory.CONFIG,
    ".ini": FileCategory.CONFIG,
    ".cfg": FileCategory.CONFIG,
    ".xml": FileCategory.CONFIG,
    ".properties": FileCategory.CONFIG,
    # Conversation
    ".log": FileCategory.CONVERSATION,
    ".chat": FileCategory.CONVERSATION,
}


# ---------------------------------------------------------------------------
# CrawlResult — resultado individual de um arquivo escaneado
# ---------------------------------------------------------------------------

@dataclass
class CrawlResult:
    """Resultado da varredura de um único arquivo.

    Attributes:
        absolute_path: Caminho absoluto no filesystem.
        relative_path: Caminho relativo ao source_path do projeto.
        file_hash: SHA256 do conteúdo do arquivo.
        category: Classificação automática (code, doc, config, conversation).
        extension: Extensão do arquivo (ex: '.py').
        size_bytes: Tamanho em bytes.
        is_new: True se o hash não existe no SqliteStore (arquivo novo ou modificado).
        existing_node_id: Se não é novo, o ID do nó existente no SQLite.
    """
    absolute_path: str
    relative_path: str
    file_hash: str
    category: FileCategory
    extension: str
    size_bytes: int
    is_new: bool = True
    existing_node_id: Optional[int] = None


@dataclass
class CrawlReport:
    """Relatório consolidado de uma operação de crawl.

    Attributes:
        new_files: Arquivos novos ou modificados (para processamento).
        unchanged_files: Arquivos cujo hash não mudou (skip).
        deleted_node_ids: IDs de nós no SQLite cujos arquivos não existem mais (GC).
        categories: Contagem por categoria.
        total_scanned: Total de arquivos escaneados.
    """
    new_files: list[CrawlResult] = field(default_factory=list)
    unchanged_files: list[CrawlResult] = field(default_factory=list)
    deleted_node_ids: list[int] = field(default_factory=list)
    categories: dict[str, int] = field(default_factory=dict)
    total_scanned: int = 0


# ---------------------------------------------------------------------------
# GitignoreParser — parser robusto de .gitignore
# ---------------------------------------------------------------------------

class GitignoreParser:
    """Parser de .gitignore com suporte a padrões comuns.

    Suporta:
        - Comentários (# ...) e linhas em branco.
        - Negação (! padrão → não ignora).
        - Diretórios explícitos (dir/ → só diretórios).
        - Wildcards (*, **, ?).
        - Padrões ancorados (começando com /).

    Limitações:
        - Não suporta .gitignore aninhados em subdiretórios (apenas o da raiz).
        - Padrões complexos com range [a-z] são tratados como glob simples.
    """

    def __init__(self) -> None:
        """Inicializa o parser com listas vazias."""
        self._patterns: list[str] = []
        self._negations: list[str] = []
        self._dir_only_patterns: list[str] = []

    def load(self, gitignore_path: str) -> None:
        """Carrega e parseia um arquivo .gitignore.

        Ignora linhas em branco e comentários.
        Padrões de negação (!) são armazenados separadamente.
        Padrões de diretório (terminados em /) são armazenados separadamente.

        Args:
            gitignore_path: Caminho absoluto do .gitignore.
        """
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as f:
                raw_lines = f.readlines()
        except (OSError, IOError) as e:
            logger.warning("Não foi possível ler .gitignore em %s: %s", gitignore_path, e)
            return

        for line in raw_lines:
            # Remove trailing whitespace (mantém leading para padrões com espaço)
            stripped = line.rstrip()

            # Ignora linhas vazias e comentários
            if not stripped or stripped.startswith("#"):
                continue

            # Remove trailing espaço escapado (\\ no final)
            if stripped.endswith("\\ "):
                stripped = stripped[:-2] + " "

            # Padrões de negação
            if stripped.startswith("!"):
                negation = stripped[1:].strip()
                if negation:
                    self._negations.append(negation)
                continue

            # Padrões de diretório (terminados em /)
            if stripped.endswith("/"):
                self._dir_only_patterns.append(stripped.rstrip("/"))
                # Também adiciona como padrão normal para o conteúdo do diretório
                self._patterns.append(stripped.rstrip("/"))
                self._patterns.append(stripped.rstrip("/") + "/**")
                continue

            # Remove barra inicial (ancora ao root, mas nós tratamos relativo)
            if stripped.startswith("/"):
                stripped = stripped[1:]

            self._patterns.append(stripped)

        logger.debug(
            "GitignoreParser: %d padrões carregados, %d negações, %d dir-only",
            len(self._patterns), len(self._negations), len(self._dir_only_patterns),
        )

    def should_ignore(self, relative_path: str, is_dir: bool = False) -> bool:
        """Verifica se um path relativo deve ser ignorado.

        A lógica segue a semântica do Git:
            1. Se o path corresponde a algum padrão de ignore → True.
            2. Se o path corresponde a um padrão de negação → False (override).
            3. Padrões dir-only só se aplicam a diretórios.

        Args:
            relative_path: Caminho relativo ao root do projeto (forward slashes).
            is_dir: True se o path é um diretório.

        Returns:
            True se deve ser ignorado.
        """
        # Normaliza para forward slashes
        normalized = relative_path.replace("\\", "/")
        # Extrai o nome base para matching simples (ex: 'node_modules')
        basename = normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized

        # Verifica negações primeiro (override)
        for neg_pattern in self._negations:
            if self._matches(normalized, neg_pattern) or self._matches(basename, neg_pattern):
                return False

        # Verifica padrões de diretório
        if is_dir:
            for dir_pattern in self._dir_only_patterns:
                if self._matches(normalized, dir_pattern) or self._matches(basename, dir_pattern):
                    return True

        # Verifica padrões gerais
        for pattern in self._patterns:
            if self._matches(normalized, pattern) or self._matches(basename, pattern):
                return True

        return False

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        """Verifica se um path corresponde a um padrão glob.

        Suporta:
            - fnmatch wildcards (*, ?, [seq])
            - ** (glob recursivo — match de qualquer profundidade)

        Args:
            path: Path normalizado (forward slashes).
            pattern: Padrão glob.

        Returns:
            True se o path corresponde ao padrão.
        """
        # ** → qualquer subdiretório
        if "**" in pattern:
            # Transforma 'dir/**/file' em match recursivo
            # Divide pelo '**' e verifica as partes
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix = parts[0].rstrip("/")
                suffix = parts[1].lstrip("/")
                if prefix and not path.startswith(prefix):
                    return False
                if suffix and not fnmatch.fnmatch(path.rsplit("/", 1)[-1], suffix):
                    return False
                if prefix and suffix:
                    return True
                if not prefix and suffix:
                    return fnmatch.fnmatch(path.rsplit("/", 1)[-1], suffix)
                if prefix and not suffix:
                    return path.startswith(prefix)
                return True  # ** sozinho → ignora tudo

        # Padrão contém / → match contra path completo
        if "/" in pattern:
            return fnmatch.fnmatch(path, pattern)

        # Padrão simples → match contra cada componente do path
        components = path.split("/")
        for component in components:
            if fnmatch.fnmatch(component, pattern):
                return True

        return False


# ---------------------------------------------------------------------------
# ProjectCrawler — Motor de varredura
# ---------------------------------------------------------------------------

class ProjectCrawler:
    """Varredura inteligente de filesystem com Delta Detection.

    Fluxo:
        1. Carrega padrões de ignore (.gitignore + IGNORE_DIRS).
        2. Percorre recursivamente o source_path.
        3. Calcula SHA256 de cada arquivo.
        4. Consulta SqliteStore para verificar se o hash já existe.
        5. Classifica arquivo por extensão.
        6. Detecta nós órfãos (arquivos deletados) para Garbage Collection.

    Args:
        sqlite_store: Instância do SqliteStore para consulta de hashes.
        ignore_dirs: Lista de diretórios extras a ignorar (merge com DEFAULT_IGNORE_DIRS).
    """

    # Diretórios ignorados por padrão (conforme ConciergeConfig.IGNORE_DIRS)
    DEFAULT_IGNORE_DIRS: set[str] = {
        ".git", "node_modules", ".next", "dist", "build",
        "__pycache__", ".venv", "venv", ".env", ".idea",
        ".vscode", ".mypy_cache", ".pytest_cache", "coverage",
        ".tox", "egg-info", ".eggs", ".cache", ".gradle",
        "target", "vendor", "bower_components",
    }

    # Tamanho máximo de arquivo para ingestão (10 MB)
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024

    # Tamanho do bloco de leitura para hash (64 KB — eficiência de memória)
    _HASH_BLOCK_SIZE: int = 65536

    def __init__(
        self,
        sqlite_store: "SqliteStore",
        ignore_dirs: Optional[set[str]] = None,
    ) -> None:
        """Inicializa o Crawler.

        Args:
            sqlite_store: Fachada SQLite para consulta de hashes existentes.
            ignore_dirs: Diretórios extras a ignorar (merge com DEFAULT_IGNORE_DIRS).
        """
        self._store = sqlite_store
        self._ignore_dirs = self.DEFAULT_IGNORE_DIRS.copy()
        if ignore_dirs:
            self._ignore_dirs.update(ignore_dirs)

        # GitignoreParser será carregado por crawl() se existir .gitignore
        self._gitignore: Optional[GitignoreParser] = None

        logger.info(
            "ProjectCrawler inicializado: %d padrões de ignore ativos.",
            len(self._ignore_dirs),
        )

    def crawl(
        self,
        source_path: str,
        project_uuid: str,
    ) -> CrawlReport:
        """Executa varredura completa de um diretório de projeto.

        Fluxo:
            1. Valida source_path.
            2. Carrega .gitignore (se existir).
            3. Percorre arquivos recursivamente.
            4. Para cada arquivo: hash → classify → delta check.
            5. Detecta nós órfãos (Garbage Collection).
            6. Retorna CrawlReport com new_files, unchanged e deleted.

        Args:
            source_path: Diretório raiz do projeto a escanear.
            project_uuid: UUID do projeto (para filtro de nós no SQLite).

        Returns:
            CrawlReport com o inventário completo da varredura.

        Raises:
            FileNotFoundError: Se source_path não existe.
            NotADirectoryError: Se source_path não é um diretório.
        """
        root = Path(source_path).resolve()

        # --- Validação de entrada ---
        if not root.exists():
            raise FileNotFoundError(f"source_path não existe: {source_path}")
        if not root.is_dir():
            raise NotADirectoryError(f"source_path não é um diretório: {source_path}")

        logger.info("Crawl iniciado: %s (projeto: %s)", root, project_uuid)

        # --- Carrega .gitignore da raiz do projeto ---
        self._gitignore = GitignoreParser()
        gitignore_file = root / ".gitignore"
        if gitignore_file.is_file():
            self._gitignore.load(str(gitignore_file))
            logger.info(".gitignore encontrado e carregado: %s", gitignore_file)

        # --- Percorre recursivamente ---
        report = CrawlReport()
        current_hashes: set[str] = set()

        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
            current_dir = Path(dirpath)
            relative_dir = current_dir.relative_to(root)

            # Filtra diretórios IN-PLACE (os.walk topdown=True respeita isso)
            dirnames[:] = [
                d for d in dirnames
                if not self._should_ignore_dir(d, str(relative_dir / d))
            ]

            for filename in filenames:
                filepath = current_dir / filename
                relative_filepath = str(relative_dir / filename).replace("\\", "/")

                # Pula arquivos ocultos (começam com .)
                if filename.startswith(".") and filename != ".env":
                    continue

                # Verifica .gitignore
                if self._gitignore and self._gitignore.should_ignore(relative_filepath, is_dir=False):
                    logger.debug("Ignorado (.gitignore): %s", relative_filepath)
                    continue

                # Verifica se é arquivo regular e legível
                if not filepath.is_file():
                    continue

                # Verifica tamanho máximo
                try:
                    size_bytes = filepath.stat().st_size
                except OSError as e:
                    logger.warning("Não foi possível ler stat de %s: %s", filepath, e)
                    continue

                if size_bytes > self.MAX_FILE_SIZE_BYTES:
                    logger.debug(
                        "Arquivo excede MAX_FILE_SIZE (%d bytes): %s",
                        size_bytes, relative_filepath,
                    )
                    continue

                # Pula arquivos vazios (0 bytes)
                if size_bytes == 0:
                    continue

                # --- Calcula SHA256 ---
                file_hash = self.compute_file_hash(str(filepath))
                if file_hash is None:
                    # Erro na leitura — skip (já logado pelo compute_file_hash)
                    continue

                current_hashes.add(file_hash)

                # --- Classifica ---
                category = self.classify_file(filename)
                extension = Path(filename).suffix.lower()

                # --- Delta Check via SqliteStore ---
                existing_node = self._store.find_node_by_hash(project_uuid, file_hash)

                result = CrawlResult(
                    absolute_path=str(filepath),
                    relative_path=relative_filepath,
                    file_hash=file_hash,
                    category=category,
                    extension=extension,
                    size_bytes=size_bytes,
                    is_new=(existing_node is None),
                    existing_node_id=existing_node["id"] if existing_node else None,
                )

                if result.is_new:
                    report.new_files.append(result)
                else:
                    report.unchanged_files.append(result)

                # Contagem por categoria
                cat_key = category.value
                report.categories[cat_key] = report.categories.get(cat_key, 0) + 1
                report.total_scanned += 1

        # --- Detecta nós órfãos para Garbage Collection ---
        report.deleted_node_ids = self._detect_deleted_nodes(project_uuid, current_hashes)

        logger.info(
            "Crawl concluído: %d escaneados, %d novos, %d inalterados, %d deletados (GC).",
            report.total_scanned,
            len(report.new_files),
            len(report.unchanged_files),
            len(report.deleted_node_ids),
        )

        return report

    def compute_file_hash(self, filepath: str) -> Optional[str]:
        """Calcula SHA256 do conteúdo de um arquivo.

        Lê o arquivo em blocos de 64KB para eficiência de memória.
        Retorna None em caso de erro de leitura (Semantic Fallback).

        Args:
            filepath: Caminho absoluto do arquivo.

        Returns:
            Hash SHA256 hexadecimal (64 caracteres) ou None se falhou.
        """
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while True:
                    block = f.read(self._HASH_BLOCK_SIZE)
                    if not block:
                        break
                    sha256.update(block)
            return sha256.hexdigest()
        except (OSError, IOError, PermissionError) as e:
            logger.warning("Falha ao calcular hash de %s: %s", filepath, e)
            return None

    def classify_file(self, filename: str) -> FileCategory:
        """Classifica um arquivo pela extensão.

        Args:
            filename: Nome do arquivo (basename, ex: 'main.py').

        Returns:
            FileCategory correspondente (ou UNKNOWN para extensões não mapeadas).
        """
        ext = Path(filename).suffix.lower()
        return EXTENSION_MAP.get(ext, FileCategory.UNKNOWN)

    def _should_ignore_dir(self, dirname: str, relative_path: str) -> bool:
        """Verifica se um diretório deve ser ignorado.

        Avalia contra:
            - DEFAULT_IGNORE_DIRS + ignore_dirs customizados.
            - Padrões do .gitignore.
            - Diretórios ocultos (começam com . exceto .github, .husky).

        Args:
            dirname: Nome do diretório (basename).
            relative_path: Caminho relativo ao root.

        Returns:
            True se deve ser ignorado.
        """
        # Diretórios da lista de ignore
        if dirname in self._ignore_dirs:
            return True

        # Diretórios ocultos (exceto exceções úteis)
        ALLOWED_HIDDEN = {".github", ".husky", ".circleci", ".gitlab"}
        if dirname.startswith(".") and dirname not in ALLOWED_HIDDEN:
            return True

        # Verifica .gitignore
        if self._gitignore and self._gitignore.should_ignore(
            relative_path.replace("\\", "/"), is_dir=True
        ):
            return True

        return False

    def _detect_deleted_nodes(
        self,
        project_uuid: str,
        current_hashes: set[str],
    ) -> list[int]:
        """Detecta nós no SQLite cujos arquivos não existem mais no disco.

        Compara os hashes dos arquivos atuais com os nós do tipo 'file'
        do projeto no SQLite. Nós cujo file_hash não está em current_hashes
        são marcados para Garbage Collection.

        SEGURANÇA: Apenas nós com type='file' são considerados.
        Nós de tipo 'directory', 'cluster' ou 'project' nunca são deletados
        por esta rotina.

        Args:
            project_uuid: UUID do projeto.
            current_hashes: Conjunto de hashes dos arquivos que existem agora.

        Returns:
            Lista de node_ids órfãos para remoção.
        """
        orphan_ids: list[int] = []

        try:
            # Busca todos os nós do tipo 'file' com file_hash preenchido
            all_nodes = self._store.get_nodes_by_project(project_uuid)

            for node in all_nodes:
                # Apenas nós do tipo 'file' com hash
                if node.get("type") != "file":
                    continue

                node_hash = node.get("file_hash")
                if not node_hash:
                    continue

                # Se o hash não existe mais no filesystem → arquivo deletado
                if node_hash not in current_hashes:
                    orphan_ids.append(node["id"])
                    logger.debug(
                        "Nó órfão detectado (GC): id=%d, label=%s, hash=%s",
                        node["id"], node.get("label", "?"), node_hash[:16],
                    )

        except Exception as e:
            logger.error("Falha na detecção de nós deletados (GC): %s", e)

        if orphan_ids:
            logger.warning(
                "Garbage Collection: %d nós órfãos detectados no projeto %s.",
                len(orphan_ids), project_uuid,
            )
        else:
            logger.debug("Garbage Collection: nenhum nó órfão detectado.")

        return orphan_ids
