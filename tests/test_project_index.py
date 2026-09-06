"""
tests/test_project_index.py — ProjectIndex.categorize_project (core/)

Migrated from _test_core_phase2.py (script-style, assert-based).
Tests wing categorization logic using keyword matching without
instantiating the full GrafoConcierge stack.
"""
import pytest
from core import ProjectIndex
from core.config import DEFAULT_CONFIG


@pytest.fixture
def project_index():
    """Lightweight ProjectIndex with no store (categorize_project is standalone)."""
    idx = ProjectIndex.__new__(ProjectIndex)
    idx._config = DEFAULT_CONFIG
    idx._store = None
    return idx


class TestProjectIndexCategorize:
    def test_marketing_wing_detected(self, project_index):
        wing = project_index.categorize_project(
            labels=["api_vendas.py", "landing_page.html", "copy_email.txt"],
            tags=["marketing", "copy", "CTA"],
        )
        assert wing == "marketing/vendas"

    def test_finance_wing_detected(self, project_index):
        wing = project_index.categorize_project(
            labels=["robo_daytrade.py", "crypto_wallet.ts"],
            tags=["trade", "crypto", "investimento"],
        )
        assert wing == "finanças/quant"

    def test_fallback_to_geral(self, project_index):
        wing = project_index.categorize_project(
            labels=["random_file.xyz"],
            tags=[],
        )
        assert wing == "geral"

    def test_empty_labels_and_tags_falls_back(self, project_index):
        wing = project_index.categorize_project(labels=[], tags=[])
        assert isinstance(wing, str)
        assert len(wing) > 0

    def test_returns_string(self, project_index):
        result = project_index.categorize_project(
            labels=["app.py"], tags=["python"]
        )
        assert isinstance(result, str)
