"""
core/config.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Centralization of all constants, weights, and system parameters.

This module is the SINGLE source of truth for magic values.
No other module should define duplicate constants.
The values here reflect exactly what was specified in
Architecture v3.8 and validated in stress tests.

Sections:
    1. Hybrid Search v4 — Tri-signal weights
    2. Recency — Exponential decay
    3. Centrality — In-degree normalization
    4. FTS5 — BM25 parameters
    5. Wings — Keywords for automatic categorization
    6. Ingestion — Limits and ignored directories
    7. Summarization — Tokens per Zoom Gear level
    8. MCP Server — Runtime configurations
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ConciergeConfig:
    """Centralized configurations of Grafo Concierge.

    frozen=True guarantees immutability. To override values,
    create a new instance passing the modified fields.

    Example:
        config = ConciergeConfig(vector_backend="qdrant")
    """

    # =================================================================
    # 1. HYBRID SEARCH v4 — Tri-signal weights
    # =================================================================
    # score = (weight_vector × vector)
    #       + (weight_fts5 × normalized_bm25)
    #       + (weight_recency_centrality × max(recency, centrality))
    weight_vector: float = 0.50
    weight_fts5: float = 0.25
    weight_recency_centrality: float = 0.25

    # =================================================================
    # 2. RECENCY — Exponential decay
    # =================================================================
    # Half-life of 7 days: score drops to 0.50 after 7 days without commit.
    # Formula: max(e^(-λ × t), recency_min_score)
    # λ = ln(2) / half_life_days ≈ 0.09902
    recency_half_life_days: float = 7.0
    recency_lambda: float = field(default=0.0, init=False)
    recency_min_score: float = 0.01

    # =================================================================
    # 3. CENTRALITY — In-degree normalization
    # =================================================================
    # min(in_degree / centrality_max_in_degree, 1.0)
    # A node with 10+ dependents is a "Super-Node" (score = 1.0).
    centrality_max_in_degree: int = 10

    # =================================================================
    # 4. FTS5 — BM25 Parameters
    # =================================================================
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    bm25_fields: tuple[str, ...] = ("label", "tags", "summary")

    # =================================================================
    # 5. WINGS — Keywords for automatic categorization
    # =================================================================
    wing_keywords: dict[str, list[str]] = field(default_factory=lambda: {
        "marketing/vendas": [
            "marketing", "venda", "copy", "cta", "conversão", "landing",
            "funil", "lead", "promo", "anúncio", "tráfego",
        ],
        "finanças/quant": [
            "finança", "quant", "trade", "ação", "crypto", "investimento",
            "bolsa", "daytrade", "renda", "mercado", "carteira",
        ],
        "gestão/saas": [
            "saas", "dashboard", "gestão", "erp", "admin", "painel",
            "plataforma", "multi-tenant", "subscription",
        ],
        "automação/rh": [
            "automação", "excel", "planilha", "rh", "workflow",
            "zapier", "n8n", "integração", "bot",
        ],
        "estatística": [
            "estatística", "análise", "dados", "média", "probabilidade",
            "regressão", "machine learning", "dataset",
        ],
    })

    # Default wing when no keyword is detected.
    default_wing: str = "geral"

    # Recommended limit of wings — warns user if exceeded.
    max_wings: int = 12

    # =================================================================
    # 6. INGESTION — Limits and filters
    # =================================================================
    ignore_dirs: tuple[str, ...] = (
        ".git", "node_modules", ".next", "dist", "build",
        "__pycache__", ".mypy_cache", ".pytest_cache", "venv",
        ".venv", "env", ".env", ".tox", "eggs", "*.egg-info",
    )

    # Supported file extensions for ingestion.
    supported_extensions: tuple[str, ...] = (
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
        ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
        ".md", ".txt", ".rst", ".yaml", ".yml", ".toml",
        ".json", ".xml", ".html", ".css", ".scss", ".sql",
    )

    # Maximum file size for ingestion (in bytes). Default: 1MB.
    max_file_size_bytes: int = 1_048_576

    # =================================================================
    # 7. SUMMARIZATION — Tokens per level (Zoom Gear)
    # =================================================================
    max_l0_tokens: int = 150   # Individual chunk
    max_l1_tokens: int = 300   # Cluster / Folder
    max_l2_tokens: int = 300   # Project Compass
    l2_relevance_threshold: float = 0.15  # Selective Amnesia

    # =================================================================
    # 8. MCP SERVER — Runtime configurations
    # =================================================================
    vector_backend: str = "chroma"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    default_scope: str = "primary_wing"

    # Lightweight mode (saves RAM by disabling vector search and using FTS5)
    lightweight_mode: bool = False

    # Result limits for searches.
    search_top_k: int = 10
    fts_limit: int = 20

    # Resume: token limits in the Compass.
    max_resume_tokens: int = 300
    max_commit_tokens: int = 100

    # Critical Revisor: maximum loops of auditing.
    max_revisor_loops: int = 3

    # Security & VPS authentication
    api_key: Optional[str] = None
    cors_origins: tuple[str, ...] = ("*",)

    def __post_init__(self) -> None:
        """Calculates derived fields after initialization."""
        # frozen=True requires object.__setattr__ for calculated fields.
        object.__setattr__(
            self, "recency_lambda",
            math.log(2) / self.recency_half_life_days
        )

        import os
        if not self.lightweight_mode:
            env_val = os.environ.get("GRAFO_LIGHTWEIGHT_MODE", "false").lower() == "true"
            if env_val:
                object.__setattr__(self, "lightweight_mode", True)

        if self.api_key is None:
            env_key = os.environ.get("GRAFO_API_KEY")
            if env_key:
                object.__setattr__(self, "api_key", env_key)

        env_cors = os.environ.get("GRAFO_CORS_ORIGINS")
        if env_cors:
            origins = tuple(o.strip() for o in env_cors.split(",") if o.strip())
            if origins:
                object.__setattr__(self, "cors_origins", origins)



# ---------------------------------------------------------------------------
# Default global instance — import directly when customizing values is
# not necessary.
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = ConciergeConfig()
