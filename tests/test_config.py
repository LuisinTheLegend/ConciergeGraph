"""
tests/test_config.py — SDD-SURVIVAL Quality Audit Refactoring

Comprehensive test suite for core/config.py (ConciergeConfig).
Validates:
  1. Default values and field types across all 8 architectural sections.
  2. Immutability guarantees (dataclass frozen=True).
  3. Dynamic mathematical derivation of recency_lambda in __post_init__.
  4. Custom instance overrides.
  5. Environment variable overrides (GRAFO_LIGHTWEIGHT_MODE, GRAFO_API_KEY, GRAFO_CORS_ORIGINS).
"""

import math
import os
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from core.config import DEFAULT_CONFIG, ConciergeConfig


class TestConciergeConfigDefaults(unittest.TestCase):
    """Verifica todos os valores default e tipos dos parâmetros do sistema."""

    def setUp(self):
        # Garante que variáveis de ambiente não afetem os testes de valores default puros
        self.env_patcher = patch.dict(os.environ, {}, clear=True)
        self.env_patcher.start()
        self.config = ConciergeConfig()

    def tearDown(self):
        self.env_patcher.stop()

    def test_default_instance_exists(self):
        """Valida que DEFAULT_CONFIG é uma instância singleton válida de ConciergeConfig."""
        self.assertIsInstance(DEFAULT_CONFIG, ConciergeConfig)

    def test_section_1_hybrid_search_weights(self):
        """Valida os pesos tri-sinal da busca híbrida (soma deve ser 1.0)."""
        self.assertEqual(self.config.weight_vector, 0.50)
        self.assertEqual(self.config.weight_fts5, 0.25)
        self.assertEqual(self.config.weight_recency_centrality, 0.25)
        total_weight = (
            self.config.weight_vector
            + self.config.weight_fts5
            + self.config.weight_recency_centrality
        )
        self.assertAlmostEqual(total_weight, 1.0, places=4)

    def test_section_2_recency_parameters(self):
        """Valida os parâmetros de decaimento temporal exponencial e cálculo de lambda."""
        self.assertEqual(self.config.recency_half_life_days, 7.0)
        self.assertEqual(self.config.recency_min_score, 0.01)
        expected_lambda = math.log(2) / 7.0
        self.assertAlmostEqual(self.config.recency_lambda, expected_lambda, places=6)
        self.assertAlmostEqual(self.config.recency_lambda, 0.099021, places=5)

    def test_section_3_centrality(self):
        """Valida normalização de centralidade e corte de Super-Node."""
        self.assertEqual(self.config.centrality_max_in_degree, 10)
        self.assertIsInstance(self.config.centrality_max_in_degree, int)

    def test_section_4_fts5_bm25(self):
        """Valida parâmetros de ranking FTS5 BM25."""
        self.assertEqual(self.config.bm25_k1, 1.5)
        self.assertEqual(self.config.bm25_b, 0.75)
        self.assertEqual(self.config.bm25_fields, ("label", "tags", "summary"))
        self.assertIsInstance(self.config.bm25_fields, tuple)

    def test_section_5_wings(self):
        """Valida configuração de Wings e dicionário de palavras-chave."""
        self.assertEqual(self.config.default_wing, "geral")
        self.assertEqual(self.config.max_wings, 12)
        self.assertIsInstance(self.config.wing_keywords, dict)
        expected_wings = {
            "marketing/vendas",
            "finanças/quant",
            "gestão/saas",
            "automação/rh",
            "estatística",
        }
        self.assertTrue(expected_wings.issubset(self.config.wing_keywords.keys()))
        for wing_name, keywords in self.config.wing_keywords.items():
            self.assertIsInstance(keywords, list)
            self.assertGreater(len(keywords), 0, f"Wing '{wing_name}' sem palavras-chave")

    def test_section_6_ingestion_limits_and_filters(self):
        """Valida diretórios ignorados, extensões suportadas e limite de tamanho de arquivo."""
        self.assertIsInstance(self.config.ignore_dirs, tuple)
        self.assertIn(".git", self.config.ignore_dirs)
        self.assertIn("node_modules", self.config.ignore_dirs)
        self.assertIn("__pycache__", self.config.ignore_dirs)
        self.assertIn(".venv", self.config.ignore_dirs)

        self.assertIsInstance(self.config.supported_extensions, tuple)
        self.assertIn(".py", self.config.supported_extensions)
        self.assertIn(".ts", self.config.supported_extensions)
        self.assertIn(".md", self.config.supported_extensions)
        self.assertIn(".json", self.config.supported_extensions)

        self.assertEqual(self.config.max_file_size_bytes, 1_048_576)  # 1MB

    def test_section_7_summarization_tokens(self):
        """Valida orçamentos de tokens por nível de Zoom Gear (L0, L1, L2)."""
        self.assertEqual(self.config.max_l0_tokens, 150)
        self.assertEqual(self.config.max_l1_tokens, 300)
        self.assertEqual(self.config.max_l2_tokens, 300)
        self.assertEqual(self.config.l2_relevance_threshold, 0.15)

    def test_section_8_mcp_runtime(self):
        """Valida parâmetros do servidor MCP e limites de busca/revisor."""
        self.assertEqual(self.config.vector_backend, "chroma")
        self.assertEqual(self.config.embedding_model, "all-MiniLM-L6-v2")
        self.assertEqual(self.config.embedding_dimensions, 384)
        self.assertEqual(self.config.default_scope, "primary_wing")
        self.assertFalse(self.config.lightweight_mode)
        self.assertEqual(self.config.search_top_k, 10)
        self.assertEqual(self.config.fts_limit, 20)
        self.assertEqual(self.config.max_resume_tokens, 300)
        self.assertEqual(self.config.max_commit_tokens, 100)
        self.assertEqual(self.config.max_revisor_loops, 3)
        self.assertIsNone(self.config.api_key)
        self.assertEqual(self.config.cors_origins, ("*",))


class TestConciergeConfigImmutabilityAndCustomization(unittest.TestCase):
    """Verifica a imutabilidade (frozen=True) e instanciação customizada."""

    def test_immutability_raises_frozen_instance_error(self):
        """Valida que tentar alterar qualquer atributo após instanciação levanta FrozenInstanceError."""
        config = ConciergeConfig()
        with self.assertRaises(FrozenInstanceError):
            config.weight_vector = 0.80

        with self.assertRaises(FrozenInstanceError):
            config.lightweight_mode = True

        with self.assertRaises(FrozenInstanceError):
            config.api_key = "hack"

    def test_custom_instance_overrides(self):
        """Valida criação de nova instância com campos customizados."""
        custom = ConciergeConfig(
            vector_backend="qdrant",
            search_top_k=25,
            recency_half_life_days=14.0,
            api_key="custom-secret",
        )
        self.assertEqual(custom.vector_backend, "qdrant")
        self.assertEqual(custom.search_top_k, 25)
        self.assertEqual(custom.recency_half_life_days, 14.0)
        self.assertEqual(custom.api_key, "custom-secret")

        # Lambda deve ser recalculado para a nova meia-vida de 14 dias
        expected_lambda = math.log(2) / 14.0
        self.assertAlmostEqual(custom.recency_lambda, expected_lambda, places=6)


class TestConciergeConfigEnvironmentVariables(unittest.TestCase):
    """Verifica overrides de configuração via variáveis de ambiente no __post_init__."""

    def test_env_lightweight_mode_enabled(self):
        """GRAFO_LIGHTWEIGHT_MODE='true' deve ativar lightweight_mode."""
        with patch.dict(os.environ, {"GRAFO_LIGHTWEIGHT_MODE": "true"}):
            config = ConciergeConfig()
            self.assertTrue(config.lightweight_mode)

    def test_env_lightweight_mode_disabled(self):
        """GRAFO_LIGHTWEIGHT_MODE='false' mantém lightweight_mode desativado."""
        with patch.dict(os.environ, {"GRAFO_LIGHTWEIGHT_MODE": "false"}):
            config = ConciergeConfig()
            self.assertFalse(config.lightweight_mode)

    def test_explicit_lightweight_mode_not_overridden_by_env_false(self):
        """Se explicitamente passado lightweight_mode=True, env var 'false' não anula."""
        with patch.dict(os.environ, {"GRAFO_LIGHTWEIGHT_MODE": "false"}):
            config = ConciergeConfig(lightweight_mode=True)
            self.assertTrue(config.lightweight_mode)

    def test_env_api_key_override(self):
        """GRAFO_API_KEY deve preencher api_key quando None."""
        with patch.dict(os.environ, {"GRAFO_API_KEY": "env-secret-token-999"}):
            config = ConciergeConfig()
            self.assertEqual(config.api_key, "env-secret-token-999")

    def test_explicit_api_key_has_precedence_over_env(self):
        """API key passada explicitamente tem precedência sobre a env var."""
        with patch.dict(os.environ, {"GRAFO_API_KEY": "env-secret"}):
            config = ConciergeConfig(api_key="explicit-secret")
            self.assertEqual(config.api_key, "explicit-secret")

    def test_env_cors_origins_parsing(self):
        """GRAFO_CORS_ORIGINS com múltiplos domínios separados por vírgula."""
        with patch.dict(
            os.environ,
            {"GRAFO_CORS_ORIGINS": "https://dashboard.concierge.ai, http://localhost:3000 "},
        ):
            config = ConciergeConfig()
            self.assertEqual(
                config.cors_origins,
                ("https://dashboard.concierge.ai", "http://localhost:3000"),
            )

    def test_env_cors_origins_empty_string_preserves_default(self):
        """GRAFO_CORS_ORIGINS vazio ou apenas espaços preserva o default ('*',)."""
        with patch.dict(os.environ, {"GRAFO_CORS_ORIGINS": "   "}):
            config = ConciergeConfig()
            self.assertEqual(config.cors_origins, ("*",))


if __name__ == "__main__":
    unittest.main()
