"""
core/config.py — Grafo Concierge v3.8.0 (Absolute Solidity)

Centralização de todas as constantes, pesos e parâmetros do sistema.

Este módulo é a ÚNICA fonte de verdade para valores mágicos.
Nenhum outro módulo deve definir constantes duplicadas.
Os valores aqui refletem exatamente o que foi especificado na
Architecture v3.8 e validado nos testes de estresse.

Seções:
    1. Busca Híbrida v4 — Pesos tri-sinal
    2. Recência — Decaimento exponencial
    3. Centralidade — Normalização de in-degree
    4. FTS5 — Parâmetros BM25
    5. Alas (Wings) — Palavras-chave para categorização automática
    6. Ingestão — Limites e diretórios ignorados
    7. Sumarização — Tokens por nível de Zoom Gear
    8. Servidor MCP — Configurações de runtime
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ConciergeConfig:
    """Configurações centralizadas do Grafo Concierge.

    frozen=True garante imutabilidade. Para sobrescrever valores,
    crie uma nova instância passando os campos alterados.

    Exemplo:
        config = ConciergeConfig(vector_backend="qdrant")
    """

    # =================================================================
    # 1. BUSCA HÍBRIDA v4 — Pesos tri-sinal
    # =================================================================
    # score = (weight_vector × vetorial)
    #       + (weight_fts5 × bm25_normalizado)
    #       + (weight_recency_centrality × max(recência, centralidade))
    weight_vector: float = 0.50
    weight_fts5: float = 0.25
    weight_recency_centrality: float = 0.25

    # =================================================================
    # 2. RECÊNCIA — Decaimento exponencial
    # =================================================================
    # Meia-vida de 7 dias: score cai para 0.50 após 7 dias sem commit.
    # Fórmula: max(e^(-λ × t), recency_min_score)
    # λ = ln(2) / half_life_days ≈ 0.09902
    recency_half_life_days: float = 7.0
    recency_lambda: float = field(default=0.0, init=False)
    recency_min_score: float = 0.01

    # =================================================================
    # 3. CENTRALIDADE — Normalização de in-degree
    # =================================================================
    # min(in_degree / centrality_max_in_degree, 1.0)
    # Um nó com 10+ dependentes é "Super-Nó" (score = 1.0).
    centrality_max_in_degree: int = 10

    # =================================================================
    # 4. FTS5 — Parâmetros BM25
    # =================================================================
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    bm25_fields: tuple[str, ...] = ("label", "tags", "summary")

    # =================================================================
    # 5. ALAS (WINGS) — Palavras-chave para categorização automática
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

    # Ala padrão quando nenhuma palavra-chave é detectada.
    default_wing: str = "geral"

    # Limite recomendado de alas — acima disso, avisa o usuário.
    max_wings: int = 12

    # =================================================================
    # 6. INGESTÃO — Limites e filtros
    # =================================================================
    ignore_dirs: tuple[str, ...] = (
        ".git", "node_modules", ".next", "dist", "build",
        "__pycache__", ".mypy_cache", ".pytest_cache", "venv",
        ".venv", "env", ".env", ".tox", "eggs", "*.egg-info",
    )

    # Extensões de arquivo suportadas para ingestão.
    supported_extensions: tuple[str, ...] = (
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
        ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
        ".md", ".txt", ".rst", ".yaml", ".yml", ".toml",
        ".json", ".xml", ".html", ".css", ".scss", ".sql",
    )

    # Tamanho máximo de arquivo para ingestão (em bytes). Default: 1MB.
    max_file_size_bytes: int = 1_048_576

    # =================================================================
    # 7. SUMARIZAÇÃO — Tokens por nível (Zoom Gear)
    # =================================================================
    max_l0_tokens: int = 150   # Chunk individual
    max_l1_tokens: int = 300   # Cluster / Pasta
    max_l2_tokens: int = 300   # Bússola do Projeto
    l2_relevance_threshold: float = 0.15  # Amnésia Seletiva

    # =================================================================
    # 8. SERVIDOR MCP — Configurações de runtime
    # =================================================================
    vector_backend: str = "chroma"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    default_scope: str = "primary_wing"

    # Limites de resultados para buscas.
    search_top_k: int = 10
    fts_limit: int = 20

    # Resume: limite de tokens na Bússola.
    max_resume_tokens: int = 300
    max_commit_tokens: int = 100

    # Revisor Crítico: loops máximos de auditoria.
    max_revisor_loops: int = 3

    # Janitor: intervalo padrão em segundos.
    janitor_interval_seconds: int = 300
    janitor_stale_threshold_days: int = 30

    def __post_init__(self) -> None:
        """Calcula campos derivados após a inicialização."""
        # frozen=True exige object.__setattr__ para campos calculados.
        object.__setattr__(
            self, "recency_lambda",
            math.log(2) / self.recency_half_life_days
        )


# ---------------------------------------------------------------------------
# Instância global padrão — importar diretamente quando não for necessário
# customizar valores.
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = ConciergeConfig()
