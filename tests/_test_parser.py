"""Teste E2E para ingestion/parser.py — Grafo Concierge v3.8.0"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.crawler import CrawlResult, FileCategory
from ingestion.parser import FileParser, ChunkType, PROMPT_ARMOR_OPEN, PROMPT_ARMOR_CLOSE

# Diretorio de teste
TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_test_parser_tmp")
os.makedirs(TEST_DIR, exist_ok=True)

parser = FileParser(max_chunk_tokens=512, enable_prompt_armor=True)

def make_crawl(filename, content, category, ext):
    path = os.path.join(TEST_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return CrawlResult(
        absolute_path=path, relative_path=filename,
        file_hash="fakehash123", category=category,
        extension=ext, size_bytes=len(content),
    )

# ===================================================================
print("=" * 60)
print("TESTE 1: Python AST Chunking")
print("=" * 60)
py_source = '''import os
import json
from pathlib import Path

CONSTANT = 42

def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"

class Calculator:
    """A simple calculator."""
    def add(self, a, b):
        return a + b
    def sub(self, a, b):
        return a - b

async def fetch_data(url):
    pass
'''
cr = make_crawl("sample.py", py_source, FileCategory.CODE, ".py")
chunks = parser.parse(cr)
print(f"  Chunks gerados: {len(chunks)}")
for c in chunks:
    print(f"    [{c.chunk_type.value:8s}] L{c.start_line}-{c.end_line} symbol={c.symbol_name} tokens={c.estimated_tokens}")
assert len(chunks) >= 3, f"Esperado >= 3 chunks (module + func + class), obteve {len(chunks)}"
types = {c.chunk_type for c in chunks}
assert ChunkType.MODULE in types, "Deveria ter chunk MODULE"
assert ChunkType.FUNCTION in types, "Deveria ter chunk FUNCTION"
assert ChunkType.CLASS in types, "Deveria ter chunk CLASS"
print("  [PASS] Python AST Chunking OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 2: Prompt Armor")
print("=" * 60)
for c in chunks:
    assert PROMPT_ARMOR_OPEN in c.armored_content, f"Prompt Armor OPEN ausente no chunk {c.chunk_index}"
    assert PROMPT_ARMOR_CLOSE in c.armored_content, f"Prompt Armor CLOSE ausente no chunk {c.chunk_index}"
    assert PROMPT_ARMOR_OPEN not in c.content, "content NAO deve ter armor (so armored_content)"
print("  [PASS] Prompt Armor aplicado corretamente em todos os chunks")

# ===================================================================
print()
print("=" * 60)
print("TESTE 3: Token Estimation")
print("=" * 60)
for c in chunks:
    expected = max(1, len(c.content) // 4)
    assert c.estimated_tokens == expected, f"Token estimate errado: {c.estimated_tokens} != {expected}"
print("  [PASS] Token estimation (4 chars/token) OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 4: Tag Detection (Python imports)")
print("=" * 60)
module_chunk = [c for c in chunks if c.chunk_type == ChunkType.MODULE][0]
print(f"  Tags detectadas no MODULE: {module_chunk.detected_tags}")
assert "os" in module_chunk.detected_tags, "Deveria detectar 'os'"
assert "json" in module_chunk.detected_tags, "Deveria detectar 'json'"
print("  [PASS] Tag detection para imports Python OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 5: JavaScript/TypeScript Chunking")
print("=" * 60)
js_source = '''import { useState } from 'react';
import axios from 'axios';

export function fetchUser(id) {
    return axios.get(`/api/users/${id}`);
}

export class UserService {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
    }
    getUser(id) {
        return fetch(`${this.apiUrl}/users/${id}`);
    }
}

const processData = async (data) => {
    return data.map(d => d.value);
};
'''
cr_js = make_crawl("service.ts", js_source, FileCategory.CODE, ".ts")
js_chunks = parser.parse(cr_js)
print(f"  Chunks gerados: {len(js_chunks)}")
for c in js_chunks:
    print(f"    [{c.chunk_type.value:8s}] L{c.start_line}-{c.end_line} symbol={c.symbol_name} tokens={c.estimated_tokens}")
assert len(js_chunks) >= 2, f"Esperado >= 2 chunks, obteve {len(js_chunks)}"
js_tags_all = set()
for c in js_chunks:
    js_tags_all.update(c.detected_tags)
print(f"  Tags consolidadas: {sorted(js_tags_all)}")
assert "react" in js_tags_all, "Deveria detectar 'react'"
print("  [PASS] JS/TS Chunking OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 6: Markdown Header Chunking")
print("=" * 60)
md_source = '''# Introduction
Welcome to the project.

## Getting Started
Install with `pip install project`.

### Prerequisites
- Python 3.10+
- Docker

## API Reference
The API endpoints are documented below.

### Authentication
Use JWT tokens for auth.
'''
cr_md = make_crawl("README.md", md_source, FileCategory.DOC, ".md")
md_chunks = parser.parse(cr_md)
print(f"  Chunks gerados: {len(md_chunks)}")
for c in md_chunks:
    print(f"    [{c.chunk_type.value:8s}] L{c.start_line}-{c.end_line} symbol={c.symbol_name}")
assert len(md_chunks) >= 4, f"Esperado >= 4 secoes, obteve {len(md_chunks)}"
names = [c.symbol_name for c in md_chunks]
assert "Introduction" in names, "Deveria ter secao Introduction"
assert "Getting Started" in names, "Deveria ter secao Getting Started"
print("  [PASS] Markdown Header Chunking OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 7: Config Chunking")
print("=" * 60)
config_source = '{"name": "project", "version": "1.0.0", "scripts": {"dev": "next dev"}}'
cr_cfg = make_crawl("package.json", config_source, FileCategory.CONFIG, ".json")
cfg_chunks = parser.parse(cr_cfg)
print(f"  Chunks gerados: {len(cfg_chunks)}")
assert len(cfg_chunks) == 1, "Config pequeno deveria ser 1 chunk"
assert cfg_chunks[0].chunk_type == ChunkType.CONFIG
print("  [PASS] Config Chunking OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 8: parse_batch com Semantic Fallback")
print("=" * 60)
results = [cr, cr_js, cr_md, cr_cfg]
all_chunks = parser.parse_batch(results)
print(f"  Total de chunks em batch: {len(all_chunks)}")
assert len(all_chunks) > 0, "Batch deveria gerar chunks"
print("  [PASS] parse_batch OK")

# ===================================================================
print()
print("=" * 60)
print("TESTE 9: Python com SyntaxError (fallback RAW)")
print("=" * 60)
bad_py = "def broken(\n    this is not valid python"
cr_bad = make_crawl("broken.py", bad_py, FileCategory.CODE, ".py")
bad_chunks = parser.parse(cr_bad)
print(f"  Chunks gerados (fallback): {len(bad_chunks)}")
assert len(bad_chunks) >= 1, "Deveria gerar pelo menos 1 chunk RAW"
assert bad_chunks[0].chunk_type == ChunkType.RAW, "Deveria ser RAW (fallback)"
print("  [PASS] SyntaxError fallback para RAW OK")

# Cleanup
shutil.rmtree(TEST_DIR)

print()
print("=" * 60)
print("TODOS OS 9 TESTES PASSARAM — parser.py v3.8.0 OPERACIONAL")
print("=" * 60)
