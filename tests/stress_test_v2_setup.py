"""Setup compartilhado para o Stress Test v2."""
from __future__ import annotations
import os, sys, shutil, uuid, time, logging
from dotenv import load_dotenv
load_dotenv()

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(BASE, "_stress_test_v2_workspace")
DB_PATH = os.path.join(TEST_DIR, "v2_test.db")
CHROMA_PATH = os.path.join(TEST_DIR, "chroma")

PROJ_A_DIR = os.path.join(TEST_DIR, "fintech-api")
PROJ_B_DIR = os.path.join(TEST_DIR, "obsidian-vault")
PROJ_C_DIR = os.path.join(TEST_DIR, "personal-wiki")

LLM_API_KEY = os.environ.get("GRAFO_LLM_API_KEY", "")
_results: list[tuple[str, bool, str]] = []

def report(label, passed, detail=""):
    icon = "[OK]" if passed else "[FAIL]"
    _results.append((label, passed, detail))
    print(f"  {icon} {label}" + (f" -- {detail}" if detail else ""))

def header(title):
    print(); print("=" * 64); print(f"  {title}"); print("=" * 64)

def get_results():
    return _results

def clear_results():
    _results.clear()

def print_report():
    header("RELATORIO FINAL")
    total = len(_results); passed = sum(1 for _,ok,_ in _results if ok); failed = total - passed
    print()
    for label, ok, detail in _results:
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {label}" + (f"  ->  {detail}" if detail else ""))
    print(); print("-" * 64)
    pct = (passed/total*100) if total else 0
    st = "PASS" if not failed else "WARN"
    print(f"  [{st}]  {passed}/{total} testes passaram ({pct:.0f}%)")
    if not failed: print("  ABSOLUTE SOLIDITY CONFIRMADA")
    else: print(f"  {failed} teste(s) falharam")
    print("-" * 64)
    return 0 if not failed else 1

# --- Criacao de arquivos fake ---
_TRADING_PY = '''\
"""Motor de Trading com estrategias de alta frequencia."""
from dataclasses import dataclass
from typing import Optional
import math

@dataclass
class TradeOrder:
    symbol: str
    quantity: int
    price: float
    side: str = "BUY"

class TradingEngine:
    """Motor de execucao de ordens com suporte a HFT."""
    def __init__(self, max_position: int = 1000):
        self._max_position = max_position
        self._orders: list[TradeOrder] = []

    def place_order(self, order: TradeOrder) -> bool:
        if order.quantity > self._max_position:
            return False
        self._orders.append(order)
        return True

    def calculate_vwap(self, prices: list[float], volumes: list[int]) -> float:
        total_pv = sum(p*v for p,v in zip(prices, volumes))
        total_v = sum(volumes)
        return total_pv / total_v if total_v else 0.0

    def sharpe_ratio(self, returns: list[float], rf: float = 0.02) -> float:
        mean_r = sum(returns)/len(returns) if returns else 0
        std = math.sqrt(sum((r-mean_r)**2 for r in returns)/len(returns)) if len(returns)>1 else 1
        return (mean_r - rf) / std if std else 0.0
'''

_RISK_PY = '''\
"""Modulo de calculo de risco financeiro e VaR."""
import math

class RiskCalculator:
    """Calcula Value at Risk (VaR) e metricas de risco."""
    def __init__(self, confidence: float = 0.95):
        self._confidence = confidence

    def parametric_var(self, portfolio_value: float, volatility: float, days: int = 1) -> float:
        z_score = 1.645 if self._confidence == 0.95 else 2.326
        return portfolio_value * volatility * z_score * math.sqrt(days)

    def max_drawdown(self, equity_curve: list[float]) -> float:
        peak = equity_curve[0] if equity_curve else 0
        max_dd = 0
        for val in equity_curve:
            if val > peak: peak = val
            dd = (peak - val) / peak if peak else 0
            if dd > max_dd: max_dd = dd
        return max_dd
'''

_UTILS_PY = '''\
"""Utilitarios de formatacao financeira."""
def format_currency(value: float, symbol: str = "R$") -> str:
    return f"{symbol} {value:,.2f}"

def validate_rate(rate: float) -> bool:
    return 0.0 <= rate <= 1.0
'''

_README_A = '''\
# Fintech API
Motor de trading algoritmico com HFT, VaR e gestao de risco.
## Stack: Python, FastAPI, PostgreSQL
'''

_ANALYTICS_PY = '''\
"""Rastreamento de metricas de marketing e conversao."""
class AnalyticsTracker:
    """Rastreia eventos de conversao e funil de vendas."""
    def __init__(self):
        self._events = []

    def track_event(self, event_name: str, properties: dict = None):
        self._events.append({"name": event_name, "props": properties or {}})

    def conversion_rate(self, visitors: int, conversions: int) -> float:
        return conversions / visitors if visitors else 0.0

    def customer_lifetime_value(self, avg_purchase: float, frequency: float, lifespan: float) -> float:
        return avg_purchase * frequency * lifespan
'''

_README_B = '''\
# Obsidian Vault - Marketing Dashboard
Dashboard de analytics e campanhas de marketing digital.
## KPIs: CAC, LTV, Churn Rate, ROAS
'''

_VAULT_PY = '''\
"""Gerenciamento seguro de segredos e credenciais."""
class SecretVault:
    def __init__(self):
        self._secrets = {}
    def store_secret(self, key: str, value: str):
        self._secrets[key] = value
    def get_secret(self, key: str) -> str:
        return self._secrets.get(key, "")
'''

_README_C = '# Personal Wiki\nBase de conhecimento pessoal.\n'

def setup_workspace():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)
    for d in [PROJ_A_DIR, PROJ_B_DIR, PROJ_C_DIR]:
        os.makedirs(os.path.join(d, "src"), exist_ok=True)
    files = [
        (os.path.join(PROJ_A_DIR, "src", "trading.py"), _TRADING_PY),
        (os.path.join(PROJ_A_DIR, "src", "risk.py"), _RISK_PY),
        (os.path.join(PROJ_A_DIR, "src", "utils.py"), _UTILS_PY),
        (os.path.join(PROJ_A_DIR, "README.md"), _README_A),
        (os.path.join(PROJ_A_DIR, ".gitignore"), "__pycache__/\n*.pyc\n"),
        (os.path.join(PROJ_B_DIR, "src", "analytics.py"), _ANALYTICS_PY),
        (os.path.join(PROJ_B_DIR, "README.md"), _README_B),
        (os.path.join(PROJ_C_DIR, "src", "vault.py"), _VAULT_PY),
        (os.path.join(PROJ_C_DIR, "README.md"), _README_C),
    ]
    for path, content in files:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

def bootstrap():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)-7s | %(name)-28s | %(message)s", stream=sys.stderr)
    for name in ["grafo-concierge", "chromadb", "sentence_transformers"]:
        logging.getLogger(name).setLevel(logging.ERROR)

    from storage import SqliteStore, EmbeddingManager, ChromaVectorStore
    from ingestion.summarizer import LLMAdapter, ZoomSummarizer
    from ingestion.orchestrator import IngestionManager
    from core.middleware import GrafoConcierge
    from agents.revisor_critico import RevisorCritico
    from interface.action_hooks import ActionHooks

    store = SqliteStore(DB_PATH)
    embedder = EmbeddingManager()
    vector = ChromaVectorStore(persist_dir=CHROMA_PATH, collection_name="stress_v2", embedding_manager=embedder)

    if not LLM_API_KEY:
        raise RuntimeError("GRAFO_LLM_API_KEY nao encontrada no .env. Teste requer LLM real.")

    llm = LLMAdapter(
        model_name=os.environ.get("GRAFO_LLM_MODEL", "gemini-2.5-flash"),
        api_key=LLM_API_KEY,
        base_url=os.environ.get("GRAFO_LLM_BASE_URL", None) or None,
    )
    summarizer = ZoomSummarizer(llm_adapter=llm, sqlite_store=store)
    manager = IngestionManager(sqlite_store=store, vector_store=vector, embedding_manager=embedder, summarizer=summarizer)
    gc = GrafoConcierge(sqlite_store=store, vector_store=vector, embedding_manager=embedder, ingestion_manager=manager)
    revisor = RevisorCritico()
    hooks = ActionHooks(concierge=gc, revisor=revisor)

    return store, vector, embedder, manager, gc, revisor, hooks
