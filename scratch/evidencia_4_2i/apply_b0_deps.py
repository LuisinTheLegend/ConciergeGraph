"""Apply pyproject.toml and requirements.txt updates and capture BL-015 xfail/xpass proofs."""
import pathlib
import subprocess
import sys

# 1. Update pyproject.toml
p = pathlib.Path("pyproject.toml")
text = p.read_text(encoding="utf-8")
old_block = """[project.optional-dependencies]
qdrant = ["qdrant-client>=1.7"]
dev = [
    "pytest>=7.0",
    "flake8>=6.0",
    "mypy>=1.0",
    "qdrant-client>=1.7",
    "google-genai>=0.1.0",
]
all = [
    "qdrant-client>=1.7",
    "google-genai>=0.1.0",
]"""
new_block = """[project.optional-dependencies]
qdrant = ["qdrant-client>=1.7"]
openai = ["openai>=1.0"]
dev = [
    "pytest>=7.0",
    "flake8>=6.0",
    "mypy>=1.0",
    "qdrant-client>=1.7",
    "google-genai>=0.1.0",
    "openai>=1.0",
]
all = [
    "qdrant-client>=1.7",
    "google-genai>=0.1.0",
    "openai>=1.0",
]"""
if old_block in text:
    p.write_bytes(text.replace(old_block, new_block, 1).replace("\n", "\r\n").encode("utf-8"))
    print("pyproject.toml updated")
elif new_block in text:
    print("pyproject.toml already updated")
else:
    raise RuntimeError("Could not find target block in pyproject.toml")

# 2. Update requirements.txt
r = pathlib.Path("requirements.txt")
r_text = r.read_text(encoding="utf-8")
old_req = "# LLM Providers (Google GenAI & OpenAI)\ngoogle-genai>=0.1.0\n\n# Optional Vector Backends"
new_req = "# LLM Providers (Google GenAI & OpenAI)\ngoogle-genai>=0.1.0\nopenai>=1.0.0\n\n# Optional Vector Backends"
if old_req in r_text:
    r.write_bytes(r_text.replace(old_req, new_req, 1).replace("\n", "\r\n").encode("utf-8"))
    print("requirements.txt updated")
elif new_req in r_text:
    print("requirements.txt already updated")
else:
    raise RuntimeError("Could not find target block in requirements.txt")

