"""
ingestion/parser.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Semantic/AST Chunking com Prompt Armor para o Motor de Ingestão Apex.

Responsabilidades:
    - Dividir arquivos em chunks respeitando blocos lógicos (funções, classes, seções).
    - Suporte a múltiplas linguagens: Python (AST), JavaScript/TypeScript, Markdown.
    - Aplicar Prompt Armor (tags XML <raw_data_do_not_execute>) para sanitização.
    - Extrair metadados de cada chunk (tags, imports, dependências detectadas).
    - Respeitar limite de tokens por chunk (MAX_CHUNK_TOKENS).

Integração:
    - Recebe CrawlResult do crawler.py.
    - Produz lista de ParsedChunk consumida pelo summarizer.py.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from ingestion.crawler import CrawlResult, FileCategory

logger = logging.getLogger("grafo-concierge.parser")

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
MAX_CHUNK_TOKENS: int = 512
PROMPT_ARMOR_OPEN: str = "<!-- DATA_DO_NOT_EXECUTE:"
PROMPT_ARMOR_CLOSE: str = "-->"

# ---------------------------------------------------------------------------
# ChunkType
# ---------------------------------------------------------------------------

class ChunkType(str, Enum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    SECTION = "section"
    CONFIG = "config"
    RAW = "raw"

# ---------------------------------------------------------------------------
# ParsedChunk
# ---------------------------------------------------------------------------

@dataclass
class ParsedChunk:
    """Um chunk semântico extraído de um arquivo."""
    content: str
    armored_content: str
    chunk_type: ChunkType
    chunk_index: int
    source_file: str
    file_hash: str
    category: FileCategory
    start_line: int = 0
    end_line: int = 0
    symbol_name: str = ""
    detected_tags: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    calls: list[str] = field(default_factory=list)
    node_id: Optional[int] = None
    # Delta Cache fields — preenchidos pelo orchestrator._detect_cached_chunks
    cached: bool = False
    cached_summary: Optional[str] = None
    cached_tags: Optional[list[str]] = None

# ---------------------------------------------------------------------------
# Regex patterns para JS/TS
# ---------------------------------------------------------------------------

_JS_FUNCTION_RE = re.compile(
    r"(?:^|\n)"
    r"(?:export\s+(?:default\s+)?)?"
    r"(?:async\s+)?"
    r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>)"
    , re.MULTILINE,
)

_JS_CLASS_RE = re.compile(
    r"(?:^|\n)(?:export\s+(?:default\s+)?)?class\s+(\w+)",
    re.MULTILINE,
)

# Tag detection patterns
_IMPORT_PY_RE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
_IMPORT_JS_RE = re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))""", re.MULTILINE)

# Palavras-chave de frameworks/bibliotecas conhecidas
_FRAMEWORK_KEYWORDS: dict[str, str] = {
    "fastapi": "fastapi", "flask": "flask", "django": "django",
    "express": "express", "react": "react", "nextjs": "nextjs",
    "next": "nextjs", "vue": "vue", "angular": "angular",
    "pytorch": "pytorch", "torch": "pytorch", "tensorflow": "tensorflow",
    "pandas": "pandas", "numpy": "numpy", "sqlalchemy": "sqlalchemy",
    "prisma": "prisma", "sequelize": "sequelize", "mongoose": "mongoose",
    "jwt": "jwt", "oauth": "oauth", "bcrypt": "bcrypt",
    "celery": "celery", "redis": "redis", "rabbitmq": "rabbitmq",
    "graphql": "graphql", "grpc": "grpc", "websocket": "websocket",
    "docker": "docker", "kubernetes": "kubernetes", "terraform": "terraform",
}

# ---------------------------------------------------------------------------
# FileParser
# ---------------------------------------------------------------------------

class FileParser:
    """Motor de Semantic/AST Chunking com Prompt Armor.

    Estratégia por tipo:
        - Python (.py): ast stdlib — funções, classes, módulo.
        - JS/TS (.js/.ts/.tsx/.jsx): Regex — funções, classes, módulo.
        - Markdown (.md): Headers (#) — seções hierárquicas.
        - Config (.json/.yaml/.toml): Bloco único ou split por tamanho.
        - Outros: Chunking por tamanho fixo (fallback RAW).
    """

    # Extensões que usam cada parser
    _PYTHON_EXTS = {".py"}
    _JS_EXTS = {".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"}
    _MD_EXTS = {".md", ".mdx", ".rst", ".adoc", ".txt"}
    _CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".env", ".ini", ".cfg", ".xml"}

    def __init__(
        self,
        max_chunk_tokens: int = MAX_CHUNK_TOKENS,
        enable_prompt_armor: bool = True,
    ) -> None:
        self._max_tokens = max_chunk_tokens
        self._armor = enable_prompt_armor

    def parse(self, crawl_result: CrawlResult) -> list[ParsedChunk]:
        """Processa um arquivo e retorna seus chunks semânticos."""
        filepath = crawl_result.absolute_path
        file_hash = crawl_result.file_hash
        category = crawl_result.category
        ext = crawl_result.extension.lower()

        # Leitura do conteúdo
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except (OSError, IOError) as e:
            logger.warning("Erro ao ler %s: %s", filepath, e)
            return []

        if not source.strip():
            return []

        # Dispatch por extensão
        if ext in self._PYTHON_EXTS or ext in self._JS_EXTS or ext in {".go", ".rs"}:
            chunks = self._parse_with_tree_sitter(source, crawl_result.relative_path, file_hash, ext)
        elif ext in self._MD_EXTS:
            chunks = self._parse_markdown(source, crawl_result.relative_path, file_hash)
        elif ext in self._CONFIG_EXTS:
            chunks = self._parse_config(source, crawl_result.relative_path, file_hash)
        else:
            chunks = self._parse_raw(source, crawl_result.relative_path, file_hash, category)

        # Pós-processamento: atribui category, tags e armor
        for chunk in chunks:
            chunk.category = category
            if not chunk.detected_tags:
                chunk.detected_tags = self._detect_tags(chunk.content, category)

        return chunks

    def _get_tree_sitter_parser(self, ext: str) -> Optional[Any]:
        try:
            import tree_sitter
            import ctypes
            
            # Setup ctypes helper to get pointer from capsule if needed
            try:
                ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
                ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
            except Exception:
                pass

            def _get_lang_ptr(capsule_or_ptr):
                if isinstance(capsule_or_ptr, int):
                    return capsule_or_ptr
                # If it's a PyCapsule, extract using ctypes
                try:
                    return ctypes.pythonapi.PyCapsule_GetPointer(capsule_or_ptr, b"tree_sitter.Language")
                except Exception:
                    try:
                        return ctypes.pythonapi.PyCapsule_GetPointer(capsule_or_ptr, None)
                    except Exception:
                        return capsule_or_ptr

            def _create_language(raw_lang, name):
                if isinstance(raw_lang, tree_sitter.Language):
                    return raw_lang
                try:
                    # Tenta instanciar passando o objeto diretamente (API moderna)
                    return tree_sitter.Language(raw_lang)
                except TypeError:
                    ptr = _get_lang_ptr(raw_lang)
                    try:
                        # Fallback passando o ponteiro
                        return tree_sitter.Language(ptr)
                    except TypeError:
                        # Fallback clássico (<=0.21)
                        return tree_sitter.Language(ptr, name)

            if ext == ".py":
                import tree_sitter_python
                lang = _create_language(tree_sitter_python.language(), "python")
            elif ext in (".js", ".jsx", ".mjs", ".cjs"):
                import tree_sitter_javascript
                lang = _create_language(tree_sitter_javascript.language(), "javascript")
            elif ext == ".ts":
                import tree_sitter_typescript
                lang = _create_language(tree_sitter_typescript.language_typescript(), "typescript")
            elif ext == ".tsx":
                import tree_sitter_typescript
                lang = _create_language(tree_sitter_typescript.language_tsx(), "tsx")
            elif ext == ".go":
                import tree_sitter_go
                lang = _create_language(tree_sitter_go.language(), "go")
            elif ext == ".rs":
                import tree_sitter_rust
                lang = _create_language(tree_sitter_rust.language(), "rust")
            else:
                return None
            parser = tree_sitter.Parser()
            parser.set_language(lang)
            return parser
        except Exception as e:
            logger.warning("Erro ao carregar parser tree-sitter para %s: %s", ext, e)
            return None

    def _get_node_definition_type(self, node: Any, ext: str) -> Optional[tuple[str, str]]:
        ntype = node.type
        
        # Python
        if ext == ".py":
            if ntype == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "class", name_node.text.decode('utf-8', errors='replace')
            elif ntype == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    is_method = False
                    parent = node.parent
                    while parent:
                        if parent.type == "class_definition":
                            is_method = True
                            break
                        parent = parent.parent
                    return "method" if is_method else "function", name_node.text.decode('utf-8', errors='replace')
                    
        # JS/TS
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            if ntype in ("class_declaration", "class"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "class", name_node.text.decode('utf-8', errors='replace')
            elif ntype in ("function_declaration", "generator_function_declaration"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "function", name_node.text.decode('utf-8', errors='replace')
            elif ntype == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "method", name_node.text.decode('utf-8', errors='replace')
            elif ntype == "variable_declarator":
                init_node = node.child_by_field_name("value") or node.child_by_field_name("init")
                if init_node and init_node.type == "arrow_function":
                    name_node = node.child_by_field_name("name") or node.child(0)
                    if name_node:
                        return "function", name_node.text.decode('utf-8', errors='replace')
                        
        # Go
        elif ext == ".go":
            if ntype == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "function", name_node.text.decode('utf-8', errors='replace')
            elif ntype == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "method", name_node.text.decode('utf-8', errors='replace')
            elif ntype == "type_spec":
                type_node = node.child_by_field_name("type")
                if type_node and type_node.type == "struct_type":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        return "class", name_node.text.decode('utf-8', errors='replace')
                        
        # Rust
        elif ext == ".rs":
            if ntype == "function_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    is_method = False
                    parent = node.parent
                    while parent:
                        if parent.type == "impl_item":
                            is_method = True
                            break
                        parent = parent.parent
                    return "method" if is_method else "function", name_node.text.decode('utf-8', errors='replace')
            elif ntype in ("struct_item", "enum_item", "union_item", "trait_item"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    return "class", name_node.text.decode('utf-8', errors='replace')
                    
        return None

    def _is_call_node(self, node: Any, ext: str) -> bool:
        ntype = node.type
        if ext == ".py" and ntype == "call":
            return True
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs") and ntype == "call_expression":
            return True
        elif ext == ".go" and ntype == "call_expression":
            return True
        elif ext == ".rs" and ntype in ("call_expression", "method_call_expression"):
            return True
        return False

    def _get_callable_name(self, node: Any) -> str:
        if node.type == "identifier" or node.type == "variable_declarator":
            return node.text.decode('utf-8', errors='replace')
        
        if node.type == "attribute":
            attr_node = node.child_by_field_name("attribute")
            if attr_node:
                return attr_node.text.decode('utf-8', errors='replace')
                
        if node.type == "member_expression":
            prop_node = node.child_by_field_name("property")
            if prop_node:
                return prop_node.text.decode('utf-8', errors='replace')
                
        if node.type == "selector_expression":
            field_node = node.child_by_field_name("field")
            if field_node:
                return field_node.text.decode('utf-8', errors='replace')
                
        if node.children:
            for child in reversed(node.children):
                if "identifier" in child.type:
                    return child.text.decode('utf-8', errors='replace')
        
        return node.text.decode('utf-8', errors='replace')

    def _get_call_name(self, node: Any, ext: str) -> Optional[str]:
        if ext == ".rs" and node.type == "method_call_expression":
            method_node = node.child_by_field_name("method")
            if method_node:
                return method_node.text.decode('utf-8', errors='replace')
                
        func_node = node.child_by_field_name("function")
        if func_node:
            return self._get_callable_name(func_node)
            
        return None

    def _parse_with_tree_sitter(self, source: str, rel_path: str, file_hash: str, ext: str) -> list[ParsedChunk]:
        parser = self._get_tree_sitter_parser(ext)
        if not parser:
            if ext == ".py":
                return self._parse_python(source, rel_path, file_hash)
            elif ext in self._JS_EXTS:
                return self._parse_javascript(source, rel_path, file_hash)
            return self._parse_raw(source, rel_path, file_hash, FileCategory.CODE)
            
        try:
            source_bytes = source.encode('utf-8')
            tree = parser.parse(source_bytes)
            root = tree.root_node
            
            if root.has_error:
                logger.warning("Erro de sintaxe (AST has_error) em %s (fallback RAW)", rel_path)
                return self._parse_raw(source, rel_path, file_hash, FileCategory.CODE)
                
            definitions = []
            stack = [(root, False)]
            defn_stack = []
            
            module_defn = {
                "type": "module",
                "name": "<module>",
                "start_line": 1,
                "end_line": source.count("\n") + 1,
                "code": source,
                "calls": set()
            }
            
            while stack:
                node, visited = stack.pop()
                if visited:
                    def_info = self._get_node_definition_type(node, ext)
                    if def_info:
                        if defn_stack:
                            popped = defn_stack.pop()
                            parent_class = None
                            for parent_defn in reversed(defn_stack):
                                if parent_defn["type"] == "class":
                                    parent_class = parent_defn["name"]
                                    break
                            if parent_class and popped["type"] == "method":
                                popped["name"] = f"{parent_class}.{popped['name']}"
                            definitions.append(popped)
                else:
                    stack.append((node, True))
                    
                    def_info = self._get_node_definition_type(node, ext)
                    if def_info:
                        dtype, dname = def_info
                        defn = {
                            "type": dtype,
                            "name": dname,
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                            "code": node.text.decode('utf-8', errors='replace'),
                            "calls": set()
                        }
                        defn_stack.append(defn)
                    elif self._is_call_node(node, ext):
                        call_name = self._get_call_name(node, ext)
                        if call_name:
                            if defn_stack:
                                defn_stack[-1]["calls"].add(call_name)
                            else:
                                module_defn["calls"].add(call_name)
                                
                    for child in reversed(node.children):
                        stack.append((child, False))
                        
            definitions.append(module_defn)
            
            chunks = []
            for i, defn in enumerate(definitions):
                content = defn["code"]
                armored = self._apply_prompt_armor(content)
                tokens = self._estimate_tokens(content)
                
                if defn["type"] == "class":
                    ctype = ChunkType.CLASS
                elif defn["type"] == "method":
                    ctype = ChunkType.METHOD
                elif defn["type"] == "function":
                    ctype = ChunkType.FUNCTION
                elif defn["type"] == "module":
                    ctype = ChunkType.MODULE
                else:
                    ctype = ChunkType.RAW
                    
                chunk = ParsedChunk(
                    content=content,
                    armored_content=armored,
                    chunk_type=ctype,
                    chunk_index=i,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.CODE,
                    start_line=defn["start_line"],
                    end_line=defn["end_line"],
                    symbol_name=defn["name"],
                    detected_tags=self._detect_tags(content, FileCategory.CODE),
                    estimated_tokens=tokens
                )
                chunk.calls = list(defn["calls"])
                chunks.append(chunk)
                
        except Exception as e:
            logger.warning("Erro ao processar AST com tree-sitter para %s (fallback native/RAW): %s", rel_path, e)
            if ext == ".py":
                return self._parse_python(source, rel_path, file_hash)
            elif ext in self._JS_EXTS:
                return self._parse_javascript(source, rel_path, file_hash)
            return self._parse_raw(source, rel_path, file_hash, FileCategory.CODE)

        return chunks

    def parse_batch(self, crawl_results: list[CrawlResult]) -> list[ParsedChunk]:
        """Processa múltiplos arquivos com Semantic Fallback."""
        all_chunks: list[ParsedChunk] = []
        for cr in crawl_results:
            try:
                chunks = self.parse(cr)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error("Fallback: falha ao parsear %s: %s", cr.relative_path, e)
        return all_chunks

    # ===================================================================
    # PYTHON — AST Chunking
    # ===================================================================

    def _parse_python(self, source: str, rel_path: str, file_hash: str) -> list[ParsedChunk]:
        lines = source.splitlines(keepends=True)
        chunks: list[ParsedChunk] = []
        chunk_idx = 0

        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError as e:
            logger.warning("SyntaxError em %s (fallback RAW): %s", rel_path, e)
            return self._parse_raw(source, rel_path, file_hash, FileCategory.CODE)

        # Coleta nós (funções, classes, métodos)
        nodes_to_process: list[tuple[ChunkType, str, int, int, ast.AST]] = []

        # Traverse AST child nodes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start
                nodes_to_process.append((ChunkType.FUNCTION, node.name, start, end, node))
            elif isinstance(node, ast.ClassDef):
                start = node.lineno
                end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start
                nodes_to_process.append((ChunkType.CLASS, node.name, start, end, node))
                # Mapeia métodos internos da classe
                for subnode in ast.iter_child_nodes(node):
                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        sub_start = subnode.lineno
                        sub_end = subnode.end_lineno if hasattr(subnode, "end_lineno") and subnode.end_lineno else sub_start
                        nodes_to_process.append((ChunkType.METHOD, f"{node.name}.{subnode.name}", sub_start, sub_end, subnode))

        # Adiciona o módulo no final para corresponder ao comportamento do tree-sitter
        nodes_to_process.append((ChunkType.MODULE, "<module>", 1, len(lines) if lines else 1, tree))

        # Mapeia chamadas usando escopo de definição
        calls_map = {tree: set()}

        def traverse_ast(n, current_defn):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                calls_map[n] = set()
                for child in ast.iter_child_nodes(n):
                    traverse_ast(child, n)
            else:
                if isinstance(n, ast.Call):
                    name = None
                    if isinstance(n.func, ast.Name):
                        name = n.func.id
                    elif isinstance(n.func, ast.Attribute):
                        name = n.func.attr
                    if name:
                        calls_map[current_defn].add(name)
                for child in ast.iter_child_nodes(n):
                    traverse_ast(child, current_defn)

        traverse_ast(tree, tree)

        for ctype, name, start, end, ast_node in nodes_to_process:
            if ctype == ChunkType.MODULE:
                block_text = source.rstrip()
            else:
                block_text = "".join(lines[start - 1:end]).rstrip()

            armored = self._apply_prompt_armor(block_text)
            tokens = self._estimate_tokens(block_text)

            # Obtém chamadas específicas deste escopo
            calls = list(calls_map.get(ast_node, set()))

            # Se excede max_tokens, subdivide (exceto module para simplificar)
            if tokens > self._max_tokens and ctype != ChunkType.MODULE:
                sub_chunks = self._split_oversized(block_text, rel_path, file_hash, ctype, name, start, chunk_idx)
                # Copia chamadas para sub-chunks
                for sc in sub_chunks:
                    sc.calls = calls
                chunks.extend(sub_chunks)
                chunk_idx += len(sub_chunks)
            else:
                chunk = ParsedChunk(
                    content=block_text,
                    armored_content=armored,
                    chunk_type=ctype,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.CODE,
                    start_line=start,
                    end_line=end,
                    symbol_name=name,
                    detected_tags=self._detect_tags(block_text, FileCategory.CODE),
                    estimated_tokens=tokens,
                )
                chunk.calls = calls
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    # ===================================================================
    # JS/TS — Regex Chunking
    # ===================================================================

    def _parse_javascript(self, source: str, rel_path: str, file_hash: str) -> list[ParsedChunk]:
        lines = source.splitlines(keepends=True)
        total_lines = len(lines)
        chunks: list[ParsedChunk] = []
        chunk_idx = 0

        # Coleta posições de funções e classes
        boundaries: list[tuple[int, str, ChunkType]] = []

        for m in _JS_CLASS_RE.finditer(source):
            line_no = source[:m.start()].count("\n") + 1
            name = m.group(1) or "AnonymousClass"
            boundaries.append((line_no, name, ChunkType.CLASS))

        for m in _JS_FUNCTION_RE.finditer(source):
            line_no = source[:m.start()].count("\n") + 1
            name = m.group(1) or m.group(2) or "anonymous"
            boundaries.append((line_no, name, ChunkType.FUNCTION))

        boundaries.sort(key=lambda b: b[0])

        if not boundaries:
            return self._parse_raw(source, rel_path, file_hash, FileCategory.CODE)

        # Bloco MODULE: imports no topo (antes do primeiro boundary)
        first_boundary_line = boundaries[0][0]
        if first_boundary_line > 1:
            module_text = "".join(lines[:first_boundary_line - 1]).strip()
            if module_text:
                armored = self._apply_prompt_armor(module_text)
                chunks.append(ParsedChunk(
                    content=module_text,
                    armored_content=armored,
                    chunk_type=ChunkType.MODULE,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.CODE,
                    start_line=1,
                    end_line=first_boundary_line - 1,
                    symbol_name="<module>",
                    detected_tags=self._detect_tags(module_text, FileCategory.CODE),
                    estimated_tokens=self._estimate_tokens(module_text),
                ))
                chunk_idx += 1

        # Chunks para cada bloco detectado
        for i, (line_no, name, ctype) in enumerate(boundaries):
            # Determina fim do bloco: próximo boundary ou EOF
            if i + 1 < len(boundaries):
                end_line = boundaries[i + 1][0] - 1
            else:
                end_line = total_lines

            # Encontra o fim real do bloco via contagem de chaves
            block_lines = lines[line_no - 1:end_line]
            actual_end = self._find_block_end_braces(block_lines)
            if actual_end > 0:
                end_line = line_no - 1 + actual_end

            block_text = "".join(lines[line_no - 1:end_line]).rstrip()
            if not block_text.strip():
                continue

            armored = self._apply_prompt_armor(block_text)
            tokens = self._estimate_tokens(block_text)

            if tokens > self._max_tokens:
                sub = self._split_oversized(block_text, rel_path, file_hash, ctype, name, line_no, chunk_idx)
                chunks.extend(sub)
                chunk_idx += len(sub)
            else:
                chunks.append(ParsedChunk(
                    content=block_text,
                    armored_content=armored,
                    chunk_type=ctype,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.CODE,
                    start_line=line_no,
                    end_line=end_line,
                    symbol_name=name,
                    detected_tags=self._detect_tags(block_text, FileCategory.CODE),
                    estimated_tokens=tokens,
                ))
                chunk_idx += 1

        return chunks if chunks else self._parse_raw(source, rel_path, file_hash, FileCategory.CODE)

    @staticmethod
    def _find_block_end_braces(block_lines: list[str]) -> int:
        """Encontra a linha onde as chaves { } se equilibram (1-indexed relativo)."""
        depth = 0
        started = False
        for i, line in enumerate(block_lines, 1):
            for ch in line:
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1
            if started and depth <= 0:
                return i
        return 0

    # ===================================================================
    # MARKDOWN — Header Chunking
    # ===================================================================

    def _parse_markdown(self, source: str, rel_path: str, file_hash: str) -> list[ParsedChunk]:
        lines = source.splitlines(keepends=True)
        chunks: list[ParsedChunk] = []
        chunk_idx = 0

        # Encontra headers
        header_positions: list[tuple[int, str]] = []  # (line_no, header_text)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") and " " in stripped:
                header_positions.append((i, stripped))

        if not header_positions:
            # Sem headers — trata como bloco único
            armored = self._apply_prompt_armor(source)
            return [ParsedChunk(
                content=source.strip(),
                armored_content=armored,
                chunk_type=ChunkType.SECTION,
                chunk_index=0,
                source_file=rel_path,
                file_hash=file_hash,
                category=FileCategory.DOC,
                start_line=1,
                end_line=len(lines),
                symbol_name="<document>",
                detected_tags=self._detect_tags(source, FileCategory.DOC),
                estimated_tokens=self._estimate_tokens(source),
            )]

        # Conteúdo antes do primeiro header
        if header_positions[0][0] > 1:
            pre_text = "".join(lines[:header_positions[0][0] - 1]).strip()
            if pre_text:
                armored = self._apply_prompt_armor(pre_text)
                chunks.append(ParsedChunk(
                    content=pre_text,
                    armored_content=armored,
                    chunk_type=ChunkType.SECTION,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.DOC,
                    start_line=1,
                    end_line=header_positions[0][0] - 1,
                    symbol_name="<preamble>",
                    detected_tags=[],
                    estimated_tokens=self._estimate_tokens(pre_text),
                ))
                chunk_idx += 1

        # Cada seção
        for i, (line_no, header) in enumerate(header_positions):
            if i + 1 < len(header_positions):
                end_line = header_positions[i + 1][0] - 1
            else:
                end_line = len(lines)

            section_text = "".join(lines[line_no - 1:end_line]).rstrip()
            if not section_text.strip():
                continue

            # Extrai nome da seção (remove #)
            section_name = header.lstrip("#").strip()

            armored = self._apply_prompt_armor(section_text)
            tokens = self._estimate_tokens(section_text)

            if tokens > self._max_tokens:
                sub = self._split_oversized(section_text, rel_path, file_hash, ChunkType.SECTION, section_name, line_no, chunk_idx)
                chunks.extend(sub)
                chunk_idx += len(sub)
            else:
                chunks.append(ParsedChunk(
                    content=section_text,
                    armored_content=armored,
                    chunk_type=ChunkType.SECTION,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.DOC,
                    start_line=line_no,
                    end_line=end_line,
                    symbol_name=section_name,
                    detected_tags=self._detect_tags(section_text, FileCategory.DOC),
                    estimated_tokens=tokens,
                ))
                chunk_idx += 1

        return chunks

    # ===================================================================
    # CONFIG — Bloco único ou split
    # ===================================================================

    def _parse_config(self, source: str, rel_path: str, file_hash: str) -> list[ParsedChunk]:
        tokens = self._estimate_tokens(source)
        armored = self._apply_prompt_armor(source)

        if tokens <= self._max_tokens:
            return [ParsedChunk(
                content=source.strip(),
                armored_content=armored,
                chunk_type=ChunkType.CONFIG,
                chunk_index=0,
                source_file=rel_path,
                file_hash=file_hash,
                category=FileCategory.CONFIG,
                start_line=1,
                end_line=source.count("\n") + 1,
                symbol_name=Path(rel_path).name,
                detected_tags=self._detect_tags(source, FileCategory.CONFIG),
                estimated_tokens=tokens,
            )]

        # Config grande — split por tamanho
        return self._split_oversized(source, rel_path, file_hash, ChunkType.CONFIG, Path(rel_path).name, 1, 0)

    # ===================================================================
    # RAW — Fallback
    # ===================================================================

    def _parse_raw(self, source: str, rel_path: str, file_hash: str, category: FileCategory) -> list[ParsedChunk]:
        tokens = self._estimate_tokens(source)
        armored = self._apply_prompt_armor(source)

        if tokens <= self._max_tokens:
            return [ParsedChunk(
                content=source.strip(),
                armored_content=armored,
                chunk_type=ChunkType.RAW,
                chunk_index=0,
                source_file=rel_path,
                file_hash=file_hash,
                category=category,
                start_line=1,
                end_line=source.count("\n") + 1,
                symbol_name=Path(rel_path).name,
                detected_tags=self._detect_tags(source, category),
                estimated_tokens=tokens,
            )]

        return self._split_oversized(source, rel_path, file_hash, ChunkType.RAW, Path(rel_path).name, 1, 0)

    # ===================================================================
    # SPLIT OVERSIZED — subdivide chunks grandes
    # ===================================================================

    def _split_oversized(
        self, text: str, rel_path: str, file_hash: str,
        chunk_type: ChunkType, base_name: str, base_line: int, start_idx: int,
    ) -> list[ParsedChunk]:
        """Subdivide um bloco que excede max_chunk_tokens em sub-chunks."""
        lines = text.splitlines(keepends=True)
        chunks: list[ParsedChunk] = []
        chunk_idx = start_idx
        max_chars = self._max_tokens * 4  # heurística inversa

        current_lines: list[str] = []
        current_start = base_line
        current_chars = 0

        for i, line in enumerate(lines):
            current_lines.append(line)
            current_chars += len(line)

            if current_chars >= max_chars:
                block = "".join(current_lines).rstrip()
                armored = self._apply_prompt_armor(block)
                chunks.append(ParsedChunk(
                    content=block,
                    armored_content=armored,
                    chunk_type=chunk_type,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.CODE,
                    start_line=current_start,
                    end_line=current_start + len(current_lines) - 1,
                    symbol_name=f"{base_name}[{chunk_idx - start_idx}]",
                    detected_tags=self._detect_tags(block, FileCategory.CODE),
                    estimated_tokens=self._estimate_tokens(block),
                ))
                chunk_idx += 1
                current_start = base_line + i + 1
                current_lines = []
                current_chars = 0

        # Resto
        if current_lines:
            block = "".join(current_lines).rstrip()
            if block.strip():
                armored = self._apply_prompt_armor(block)
                chunks.append(ParsedChunk(
                    content=block,
                    armored_content=armored,
                    chunk_type=chunk_type,
                    chunk_index=chunk_idx,
                    source_file=rel_path,
                    file_hash=file_hash,
                    category=FileCategory.CODE,
                    start_line=current_start,
                    end_line=current_start + len(current_lines) - 1,
                    symbol_name=f"{base_name}[{chunk_idx - start_idx}]" if chunks else base_name,
                    detected_tags=self._detect_tags(block, FileCategory.CODE),
                    estimated_tokens=self._estimate_tokens(block),
                ))

        return chunks

    # ===================================================================
    # PROMPT ARMOR
    # ===================================================================

    def _apply_prompt_armor(self, content: str) -> str:
        """Envolve conteúdo em tags XML de Prompt Armor (comentários XML estruturados com escape defensivo)."""
        if not self._armor:
            return content
        escaped_content = content.replace("-->", "-- >")
        return f"{PROMPT_ARMOR_OPEN}\n{escaped_content}\n{PROMPT_ARMOR_CLOSE}"

    # ===================================================================
    # TOKEN ESTIMATION
    # ===================================================================

    def _estimate_tokens(self, text: str) -> int:
        """Estima tokens: ~4 caracteres por token."""
        return max(1, len(text) // 4)

    # ===================================================================
    # TAG DETECTION
    # ===================================================================

    def _detect_tags(self, content: str, category: FileCategory) -> list[str]:
        """Detecta tags automáticas baseado no conteúdo."""
        tags: set[str] = set()

        content_lower = content.lower()

        if category == FileCategory.CODE:
            # Extrai imports Python
            for m in _IMPORT_PY_RE.finditer(content):
                mod = (m.group(1) or m.group(2) or "").split(".")[0].lower()
                if mod:
                    tags.add(mod)
            # Extrai imports JS/TS
            for m in _IMPORT_JS_RE.finditer(content):
                mod = (m.group(1) or m.group(2) or "")
                mod = mod.strip("./").split("/")[0].lower()
                if mod and not mod.startswith("."):
                    tags.add(mod)

        # Detecta frameworks conhecidos
        for keyword, tag in _FRAMEWORK_KEYWORDS.items():
            if keyword in content_lower:
                tags.add(tag)

        # Para docs: detecta palavras-chave técnicas
        if category == FileCategory.DOC:
            doc_keywords = ["api", "auth", "database", "deploy", "migration", "security", "testing"]
            for kw in doc_keywords:
                if kw in content_lower:
                    tags.add(kw)

        return sorted(tags)
