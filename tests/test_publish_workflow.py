"""tests/test_publish_workflow.py

Structural guardrail tests for OIDC PyPI Trusted Publishing in
.github/workflows/publish.yml.
"""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLISH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish.yml"


def _load_workflow() -> tuple[str, dict]:
    raw = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    return raw, data


def test_publish_workflow_trigger_is_release_published_only() -> None:
    """Workflow must trigger solely on release.types == ['published']."""
    _, data = _load_workflow()
    trigger = data["on"] if "on" in data else data.get(True)

    assert isinstance(trigger, dict)
    assert set(trigger.keys()) == {"release"}
    assert trigger["release"] == {"types": ["published"]}


def test_publish_workflow_top_level_permissions_empty() -> None:
    """Workflow must declare empty top-level permissions ({})."""
    _, data = _load_workflow()

    assert "permissions" in data
    assert data["permissions"] == {}


def test_publish_workflow_build_job_least_privilege_and_steps() -> None:
    """Build job must not request id-token and must verify tag, build, twine, and upload."""
    _, data = _load_workflow()
    build = data["jobs"]["build"]

    assert build["permissions"] == {"contents": "read"}
    assert "id-token" not in build["permissions"]

    steps = build["steps"]
    uses_list = [s.get("uses") for s in steps if "uses" in s]
    assert "actions/checkout@v4" in uses_list
    assert "actions/setup-python@v5" in uses_list
    assert "actions/upload-artifact@v4" in uses_list

    upload_step = next(s for s in steps if s.get("uses") == "actions/upload-artifact@v4")
    assert upload_step["with"]["name"] == "pypi-dist"

    tag_step = next(
        s for s in steps
        if "tomllib" in str(s.get("run", ""))
    )
    assert tag_step.get("env") == {"RELEASE_TAG": "${{ github.event.release.tag_name }}"}
    assert "github.event.release.tag_name" not in tag_step["run"]

    all_runs = "\n".join(str(s.get("run", "")) for s in steps)
    assert "python -m build" in all_runs
    assert "twine check" in all_runs


def test_publish_workflow_publish_job_uses_oidc_without_secrets() -> None:
    """Publish job must depend on build, use pypi env, id-token: write, and OIDC action."""
    _, data = _load_workflow()
    publish = data["jobs"]["publish"]

    needs = publish["needs"]
    assert needs == "build" or (isinstance(needs, list) and "build" in needs)
    assert publish["environment"] == {
        "name": "pypi",
        "url": "https://pypi.org/project/concierge-graph/",
    }
    assert publish["permissions"] == {"id-token": "write"}

    steps = publish["steps"]
    download_step = next(s for s in steps if s.get("uses") == "actions/download-artifact@v4")
    assert download_step["with"]["name"] == "pypi-dist"

    pypi_step = next(
        s for s in steps if s.get("uses") == "pypa/gh-action-pypi-publish@release/v1"
    )
    pypi_with = pypi_step.get("with", {})
    assert pypi_with.get("packages-dir") == "dist/"
    assert "password" not in pypi_with
    assert "user" not in pypi_with


def test_publish_workflow_contains_no_secret_references() -> None:
    """Workflow must not reference static tokens or GitHub secrets."""
    raw, _ = _load_workflow()

    for forbidden in ("secrets.", "TWINE_PASSWORD", "PYPI_API_TOKEN"):
        assert forbidden not in raw, f"Unexpected static secret reference: {forbidden}"
