"""
tests/test_revisor_critico.py — RevisorCritico (agents/revisor_critico.py)

Migrated from _test_agents_phase3.py (script-style, assert-based).
Tests the heuristic audit, retry loop, reranking, and contamination
barrier of the RevisorCritico agent — all without LLM (llm_adapter=None).
"""
import pytest
from agents.revisor_critico import RevisorCritico, AuditResult, RerankResult
from core.config import DEFAULT_CONFIG


@pytest.fixture
def revisor():
    """RevisorCritico in heuristic mode (no LLM)."""
    return RevisorCritico(llm_adapter=None, config=DEFAULT_CONFIG)


# ---------------------------------------------------------------------------
# audit() — valid and invalid commits
# ---------------------------------------------------------------------------

class TestRevisorCriticoAudit:
    def test_valid_commit_approved(self, revisor):
        draft = {
            "phase": "build",
            "technical_changes": (
                "Implemented /api/users endpoint with JWT authentication "
                "and rate-limiting middleware."
            ),
            "updated_pointers": ["src/routes/users.py", "src/middleware/auth.py"],
            "source_wing": "gestao/saas",
        }
        result = revisor.audit(draft)
        assert result.approved is True, f"Expected approval, got: {result.reason}"

    def test_empty_technical_changes_rejected(self, revisor):
        draft = {
            "phase": "build",
            "technical_changes": "",
            "updated_pointers": ["file.py"],
        }
        result = revisor.audit(draft)
        assert result.approved is False

    def test_no_updated_pointers_rejected(self, revisor):
        draft = {
            "phase": "review",
            "technical_changes": (
                "Fixed CSV parser bug causing truncation on quoted lines."
            ),
            "updated_pointers": [],
        }
        result = revisor.audit(draft)
        assert result.approved is False

    def test_too_short_technical_changes_rejected(self, revisor):
        draft = {
            "phase": "done",
            "technical_changes": "fix bug",
            "updated_pointers": ["x.py"],
        }
        result = revisor.audit(draft)
        assert result.approved is False

    def test_audit_result_has_reason(self, revisor):
        draft = {
            "phase": "build",
            "technical_changes": "",
            "updated_pointers": [],
        }
        result = revisor.audit(draft)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0


# ---------------------------------------------------------------------------
# audit_with_retry() — fallback to partial_audit after N rejections
# ---------------------------------------------------------------------------

class TestRevisorCriticoRetry:
    def test_retry_loop_falls_back_to_partial_audit(self, revisor):
        """When generate_fn always returns an invalid draft, partial_audit is True."""
        bad_draft = {
            "phase": "build",
            "technical_changes": "bad",
            "updated_pointers": [],
        }

        def always_bad(feedback):
            return {
                "phase": "build",
                "technical_changes": "bad",
                "updated_pointers": [],
            }

        result = revisor.audit_with_retry(
            draft=bad_draft,
            generate_fn=always_bad,
        )
        assert result.approved is True, "Expected approval via partial_audit fallback"
        assert result.partial_audit is True
        assert result.loop_count >= 1


# ---------------------------------------------------------------------------
# rerank() — heuristic reranking
# ---------------------------------------------------------------------------

class TestRevisorCriticoRerank:
    def _candidates(self):
        return [
            {"node_id": 1, "score_final": 0.95, "score_breakdown": {"vetorial": 0.9}},
            {"node_id": 2, "score_final": 0.85, "score_breakdown": {"vetorial": 0.8}},
            {"node_id": 3, "score_final": 0.40, "score_breakdown": {"vetorial": 0.3}},
            {"node_id": 4, "score_final": 0.15, "score_breakdown": {"vetorial": 0.1}},
            {"node_id": 5, "score_final": 0.05, "score_breakdown": {"vetorial": 0.0}},
        ]

    def test_rerank_filters_low_scores(self, revisor):
        reranked = revisor.rerank(
            self._candidates(), task_context="JWT authentication with refresh tokens"
        )
        assert len(reranked) >= 1
        assert len(reranked) < len(self._candidates())

    def test_rerank_empty_input(self, revisor):
        assert revisor.rerank([], task_context="anything") == []

    def test_rerank_preserves_node_ids(self, revisor):
        reranked = revisor.rerank(
            self._candidates(), task_context="authentication"
        )
        for item in reranked:
            assert "node_id" in item


# ---------------------------------------------------------------------------
# check_contamination() — privacy barrier
# ---------------------------------------------------------------------------

class TestContaminationBarrier:
    def test_restricted_to_public_blocked(self, revisor):
        source = {"folder_name": "secret-project", "privacy_level": "RESTRICTED"}
        target = {"folder_name": "public-blog", "privacy_level": "PUBLIC"}
        is_safe, reason = revisor.check_contamination(source, target)
        assert is_safe is False
        assert isinstance(reason, str)

    def test_public_to_internal_allowed(self, revisor):
        source = {"folder_name": "opensource-lib", "privacy_level": "PUBLIC"}
        target = {"folder_name": "internal-project", "privacy_level": "INTERNAL"}
        is_safe, reason = revisor.check_contamination(source, target)
        assert is_safe is True
