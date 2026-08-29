"""
tests/test_cognitive_routing_memory.py — SDD-SURVIVAL-22

Suíte de testes TDD para Roteamento de Conhecimento Externo (Nozomio RAG)
e Adaptador de Memória Global Hierárquica.

Valida isoladamente:
  1. Classificação sintática rápida (regex) e por entidades do banco relacional.
  2. Direcionamento correto do roteador Nozomio (LOCAL_GRAPHRAG vs EXTERNAL_NOZOMIO_MCP).
  3. Fidelidade da montagem da janela deslizante mista de memória (LTM + STM).
"""

import unittest
import tempfile
import os

from core.database import ConciergeDatabaseManager
from core.intent_classifier import IntentClassifier
from core.nozomio_router import NozomioRouter
from core.global_memory_adapter import GlobalMemoryAdapter


class MockGraphRAGEngine:
    """Mock do GraphRAG Engine local para testes isolados."""
    def retrieve_multihop_context(self, query: str) -> str:
        return "[Local GraphRAG Content] Módulo core/database.py possui in-degree alto."


class MockExternalMCP:
    """Mock de servidor MCP federado de documentação pública."""
    def query_docs(self, query: str) -> str:
        return "[External NextJS Doc] Next.js 15 usa o App Router por padrão."


class TestCognitiveRoutingMemory(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)

        # Cria tabela 'files' para o teste heurístico de entidades
        self.db_manager.write_query(
            "CREATE TABLE IF NOT EXISTS files ("
            "path TEXT PRIMARY KEY, community_id TEXT, is_dirty INTEGER, last_modified REAL"
            ");"
        )
        self.db_manager.write_query(
            "INSERT INTO files (path, community_id, is_dirty) VALUES ('src/core/database.py', 'core', 0);"
        )

        self.classifier = IntentClassifier(self.db_manager)
        self.graph_rag = MockGraphRAGEngine()
        self.external_mcp = MockExternalMCP()
        self.router = NozomioRouter(self.db_manager, self.graph_rag, self.external_mcp)
        self.memory_adapter = GlobalMemoryAdapter(self.db_manager)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_should_classify_local_query_syntactically_and_by_db_entities(self):
        """Valida que consultas contendo caminhos, termos chaves ou classes conhecidas são LOCAL_CODEBASE"""
        # Heurística de palavra-chave (Regex)
        res_keyword = self.classifier.classify_query("Como funciona a fila de escrita do SQLite WAL?")
        self.assertEqual(res_keyword, "LOCAL_CODEBASE")

        # Heurística de arquivos cadastrados no SQLite (entidade relacional)
        res_db = self.classifier.classify_query("Qual a lógica implementada no database.py do projeto?")
        self.assertEqual(res_db, "LOCAL_CODEBASE")

        # Consulta puramente genérica deve cair no Fallback Externo
        res_external = self.classifier.classify_query("Quais os benefícios do uso de CSS Grid sobre Flexbox?")
        self.assertEqual(res_external, "EXTERNAL_GENERAL")

    def test_should_route_and_resolve_correct_knowledge_source(self):
        """Valida que o roteador direciona de forma fidedigna as requisições com base na intenção"""
        # Fluxo Local
        info_local = self.router.resolve_knowledge("Como o banco é iniciado?", "LOCAL_CODEBASE")
        self.assertEqual(info_local["source"], "LOCAL_GRAPHRAG")
        self.assertTrue(info_local["is_private"])
        self.assertIn("database.py", info_local["context"])

        # Fluxo Externo
        info_ext = self.router.resolve_knowledge("Como criar uma rota dinâmica no NextJS?", "EXTERNAL_GENERAL")
        self.assertEqual(info_ext["source"], "EXTERNAL_NOZOMIO_MCP")
        self.assertFalse(info_ext["is_private"])
        self.assertIn("App Router", info_ext["context"])

    def test_should_compile_hybrid_context_with_sliding_window(self):
        """Valida que a janela de contexto herda apenas as últimas 3 interações de chat brutos + bloco LTM"""
        mock_chat = [
            {"role": "user", "content": "Mensagem muito antiga 1"},
            {"role": "assistant", "content": "Resposta muito antiga 2"},
            {"role": "user", "content": "Mensagem antiga de teste 3"},
            {"role": "user", "content": "Mensagem recente 4"},
            {"role": "assistant", "content": "Resposta recente 5"},
            {"role": "user", "content": "Pergunta atual 6"}
        ]

        retrieved_data = {
            "source": "LOCAL_GRAPHRAG",
            "context": "[LTM Context] Classes e arestas indexadas do watcher."
        }

        compiled_prompt = self.memory_adapter.compile_hybrid_context(mock_chat, retrieved_data)

        # O bloco de memória de longo prazo (LTM) deve constar
        self.assertIn("=== SUBSTRATO DE MEMÓRIA DE LONGO PRAZO", compiled_prompt)
        self.assertIn("[LTM Context] Classes e arestas", compiled_prompt)

        # As mensagens antigas (1, 2, 3) devem ser eliminadas (podadas) para poupar contexto
        self.assertNotIn("Mensagem muito antiga 1", compiled_prompt)
        self.assertNotIn("Mensagem antiga de teste 3", compiled_prompt)

        # As últimas 3 interações (4, 5, 6) devem estar preservadas na janela de conversação de curto prazo
        self.assertIn("Mensagem recente 4", compiled_prompt)
        self.assertIn("Resposta recente 5", compiled_prompt)
        self.assertIn("Pergunta atual 6", compiled_prompt)


if __name__ == "__main__":
    unittest.main()
