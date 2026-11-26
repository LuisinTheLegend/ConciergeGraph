"""tests/test_docker_manifests.py

Contratos estaticos de Dockerfile, docker-compose.yml, .dockerignore e CI docker-smoke
(Rodada 4.8-C3).
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_non_root_sse_and_python_healthcheck():
    """Dockerfile deve usar builder --no-deps, USER concierge (10001), SSE e HEALTHCHECK Python."""
    content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "AS builder" in content
    assert "pip install --no-cache-dir --no-deps ." in content
    assert "10001" in content
    assert re.search(r"^\s*USER\s+concierge\s*$", content, re.MULTILINE), (
        "Dockerfile deve definir USER concierge"
    )

    for expected_env in (
        "GRAFO_TRANSPORT=sse",
        "GRAFO_DB_PATH=/app/data/concierge.db",
        "GRAFO_CHROMA_PATH=/app/data/chroma",
        "HOME=/home/concierge",
    ):
        assert expected_env in content, f"ENV ausente no Dockerfile: {expected_env}"

    assert "HEALTHCHECK" in content
    assert "/health" in content
    assert "curl" not in content.lower()
    assert "|| exit 0" not in content
    assert 'CMD ["concierge-mcp"]' in content


def test_docker_compose_removes_version_pins_sse_env_named_volume_and_python_healthcheck():
    """docker-compose.yml remove version:, fixa SSE/paths, expoẽ token/state e healthcheck Python."""
    content = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert not re.search(r"^\s*version\s*:", content, re.MULTILINE), (
        "docker-compose.yml nao deve conter 'version:' depreciado"
    )
    assert "GRAFO_TRANSPORT=sse" in content
    assert "GRAFO_DB_PATH=/app/data/concierge.db" in content
    assert "GRAFO_CHROMA_PATH=/app/data/chroma" in content
    assert "${GRAFO_TRANSPORT" not in content
    assert "${GRAFO_DB_PATH" not in content
    assert "${GRAFO_CHROMA_PATH" not in content

    assert "GRAFO_DEFAULT_STATE=" in content
    assert "GRAFO_AGENT_TOKEN=" in content
    assert "concierge_data:/app/data" in content
    assert re.search(r"^volumes:\s*$", content, re.MULTILINE)

    assert "/health" in content
    assert "python" in content
    assert "curl" not in content.lower()
    assert "|| exit 0" not in content


def test_dockerignore_excludes_requirements_dev_and_dev_artifacts():
    """.dockerignore exclui *.txt preservando apenas !requirements.txt."""
    lines = [
        line.strip()
        for line in (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    ]
    assert "*.txt" in lines
    assert "!requirements.txt" in lines
    assert lines.index("*.txt") < lines.index("!requirements.txt")


def test_ci_workflow_has_test_and_docker_smoke_jobs():
    """.github/workflows/ci.yml preserva job test e define job real docker-smoke."""
    content = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert re.search(r"^\s{2}test:\s*$", content, re.MULTILINE)
    assert re.search(r"^\s{2}docker-smoke:\s*$", content, re.MULTILINE)
    assert "docker build" in content
    assert "id -u" in content
    assert "10001" in content
    assert "pytest" in content and "flake8" in content and "mypy" in content
    assert "concierge --help" in content
    assert "concierge-mcp --help" in content
    assert "concierge-mcp --version" in content
    assert "/health" in content
    assert "/sse" in content
    assert "if: always()" in content
