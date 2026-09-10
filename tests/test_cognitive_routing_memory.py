"""
tests/test_cognitive_routing_memory.py — SDD-SURVIVAL-22

TDD Test Suite for Federated Knowledge Routing and Global Memory Adapter.

Validates in isolation:
  1. Fast syntactic triage (regex) and relational database entity lookup.
  2. Accurate query routing (LOCAL_GRAPHRAG vs EXTERNAL_FEDERATED_MCP).
  3. Strict fidelity of hybrid memory sliding window compilation (LTM + STM).
"""

import unittest
import tempfile
import os

from core.database import ConciergeDatabaseManager
from core.intent_classifier import IntentClassifier
from core.federated_knowledge_router import FederatedKnowledgeRouter, EXTERNAL_FEDERATED_MCP
from core.global_memory_adapter import GlobalMemoryAdapter


class MockGraphRAGEngine:
    """In-memory mock of local GraphRAG Engine for isolated testing."""
    def retrieve_multihop_context(self, query: str) -> str:
        return "[Local GraphRAG Content] Module core/database.py has high in-degree."


class MockExternalMCP:
    """In-memory mock of federated public documentation MCP server."""
    def query_docs(self, query: str) -> str:
        return "[External NextJS Doc] Next.js 15 uses App Router by default."


class TestCognitiveRoutingMemory(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_manager = ConciergeDatabaseManager(self.db_path)

        # Create 'files' table for relational entity lookup heuristic
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
        self.router = FederatedKnowledgeRouter(self.db_manager, self.graph_rag, self.external_mcp)
        self.memory_adapter = GlobalMemoryAdapter(self.db_manager)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_should_classify_local_query_syntactically_and_by_db_entities(self):
        """Validates that queries with paths, project keywords, or indexed entities resolve to LOCAL_CODEBASE."""
        # Keyword heuristic (Regex)
        res_keyword = self.classifier.classify_query("How does the SQLite WAL write queue work?")
        self.assertEqual(res_keyword, "LOCAL_CODEBASE")

        # Relational entity heuristic (file registered in SQLite)
        res_db = self.classifier.classify_query("What logic is implemented in database.py?")
        self.assertEqual(res_db, "LOCAL_CODEBASE")

        # Purely conceptual query falls back to external documentation
        res_external = self.classifier.classify_query("What are the architectural benefits of CSS Grid over Flexbox?")
        self.assertEqual(res_external, "EXTERNAL_GENERAL")

    def test_should_route_and_resolve_correct_knowledge_source(self):
        """Validates that the router reliably dispatches requests based on intent classification."""
        # Local Codebase Route
        info_local = self.router.resolve_knowledge("How is the database initialized?", "LOCAL_CODEBASE")
        self.assertEqual(info_local["source"], "LOCAL_GRAPHRAG")
        self.assertTrue(info_local["is_private"])
        self.assertIn("database.py", info_local["context"])

        # External Public Route
        info_ext = self.router.resolve_knowledge("How do dynamic routes work in NextJS?", "EXTERNAL_GENERAL")
        self.assertEqual(info_ext["source"], EXTERNAL_FEDERATED_MCP)
        self.assertFalse(info_ext["is_private"])
        self.assertIn("App Router", info_ext["context"])

    def test_should_compile_hybrid_context_with_sliding_window(self):
        """Validates that the context window retains strictly the last 3 raw chat turns + LTM substrate."""
        mock_chat = [
            {"role": "user", "content": "Very old message 1"},
            {"role": "assistant", "content": "Very old response 2"},
            {"role": "user", "content": "Old test message 3"},
            {"role": "user", "content": "Recent message 4"},
            {"role": "assistant", "content": "Recent response 5"},
            {"role": "user", "content": "Current question 6"}
        ]

        retrieved_data = {
            "source": "LOCAL_GRAPHRAG",
            "context": "[LTM Context] Indexed classes and call edges from file watcher."
        }

        compiled_prompt = self.memory_adapter.compile_hybrid_context(mock_chat, retrieved_data)

        # Long-Term Memory (LTM) substrate must be injected
        self.assertIn("=== LONG-TERM MEMORY SUBSTRATE", compiled_prompt)
        self.assertIn("[LTM Context] Indexed classes and call edges", compiled_prompt)

        # Older messages (1, 2, 3) must be pruned to conserve context tokens
        self.assertNotIn("Very old message 1", compiled_prompt)
        self.assertNotIn("Old test message 3", compiled_prompt)

        # The 3 most recent interactions (4, 5, 6) must be preserved in STM
        self.assertIn("Recent message 4", compiled_prompt)
        self.assertIn("Recent response 5", compiled_prompt)
        self.assertIn("Current question 6", compiled_prompt)


if __name__ == "__main__":
    unittest.main()
