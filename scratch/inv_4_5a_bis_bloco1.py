"""Probe Bloco 1 da 4.5a-bis: find_packages, build_wheel real e grep de auditoria."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scratch" / "evidencia_4_5a_bis"


def run_packaging_probe() -> dict:
    pyproject_path = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    pkg_find = data.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {})
    where = pkg_find.get("where", ["."])
    include = pkg_find.get("include", [])
    exclude = pkg_find.get("exclude", [])
    py_modules = data.get("tool", {}).get("setuptools", {}).get("py-modules", [])

    import setuptools

    found_packages = setuptools.find_packages(
        where=str(ROOT / where[0]),
        include=include,
        exclude=exclude,
    )

    wheel_result = {
        "attempted": True,
        "method": None,
        "success": False,
        "wheel_filename": None,
        "entries": [],
        "top_level_dirs": [],
        "error": None,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Try setuptools.build_meta.build_wheel directly (no network, no pip needed)
        try:
            from setuptools import build_meta

            old_cwd = os.getcwd()
            os.chdir(ROOT)
            try:
                whl_name = build_meta.build_wheel(str(tmp_path))
            finally:
                os.chdir(old_cwd)

            whl_path = tmp_path / whl_name
            wheel_result["method"] = "setuptools.build_meta.build_wheel"
            wheel_result["success"] = True
            wheel_result["wheel_filename"] = whl_name
            with zipfile.ZipFile(whl_path, "r") as zf:
                names = sorted(zf.namelist())
                wheel_result["entries"] = names
                tops = sorted({n.split("/", 1)[0] for n in names})
                wheel_result["top_level_dirs"] = tops
        except Exception as exc:
            wheel_result["method"] = "setuptools.build_meta.build_wheel"
            wheel_result["error"] = f"{type(exc).__name__}: {exc}"

            # Fallback probe: check pip / build CLI availability
            for mod in ("build", "pip"):
                proc = subprocess.run(
                    [sys.executable, "-m", mod, "--version"],
                    capture_output=True,
                    text=True,
                )
                wheel_result[f"module_{mod}_check"] = {
                    "returncode": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(),
                }

    return {
        "python_executable": sys.executable,
        "setuptools_version": getattr(setuptools, "__version__", "unknown"),
        "pyproject_packages_find": pkg_find,
        "pyproject_py_modules": py_modules,
        "find_packages_result": found_packages,
        "wheel_probe": wheel_result,
    }


def run_grep_audit() -> dict:
    patterns = [
        ("agents_glob", re.compile(r"agents\*")),
        ("nao_e_empacotado", re.compile(r"n[aã]o\s+[eé]\s+empacotado", re.IGNORECASE)),
        ("omite", re.compile(r"\bomite\b", re.IGNORECASE)),
    ]
    targets = []
    for folder in (ROOT / "audits", ROOT / "scratch" / "evidencia_4_5a"):
        if folder.exists():
            for p in sorted(folder.rglob("*")):
                if p.is_file() and p.suffix in {".md", ".txt", ".json", ".csv"}:
                    targets.append(p)
    for p in sorted((ROOT / "scratch").glob("*.py")):
        if "inv_4_5a" in p.name or "build_4_5a" in p.name:
            targets.append(p)

    hits: list[dict] = []
    for p in targets:
        rel = p.relative_to(ROOT).as_posix()
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, start=1):
            matched_labels = [label for label, pat in patterns if pat.search(line)]
            if matched_labels:
                hits.append(
                    {
                        "file": rel,
                        "line": idx,
                        "labels": matched_labels,
                        "text": line.strip(),
                    }
                )
    return {"scanned_files": len(targets), "hits": hits}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pkg = run_packaging_probe()
    grep = run_grep_audit()

    (OUT_DIR / "bloco1_packaging.json").write_text(
        json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DIR / "bloco1_grep_audit.json").write_text(
        json.dumps(grep, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        f"Python: {pkg['python_executable']}",
        f"Setuptools: {pkg['setuptools_version']}",
        f"pyproject.toml [tool.setuptools.packages.find]: {pkg['pyproject_packages_find']}",
        f"pyproject.toml py-modules: {pkg['pyproject_py_modules']}",
        f"setuptools.find_packages(...) => {pkg['find_packages_result']}",
        "",
        "Wheel probe:",
        f"  method: {pkg['wheel_probe']['method']}",
        f"  success: {pkg['wheel_probe']['success']}",
        f"  wheel_filename: {pkg['wheel_probe']['wheel_filename']}",
        f"  top_level_dirs: {pkg['wheel_probe']['top_level_dirs']}",
        f"  entry_count: {len(pkg['wheel_probe']['entries'])}",
        f"  error: {pkg['wheel_probe']['error']}",
        "  entries:",
    ]
    for e in pkg["wheel_probe"]["entries"]:
        lines.append(f"    {e}")
    (OUT_DIR / "bloco1_packaging.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    grep_lines = [f"Scanned files: {grep['scanned_files']}", f"Total hits: {len(grep['hits'])}", ""]
    for h in grep["hits"]:
        grep_lines.append(f"{h['file']}:{h['line']} [{','.join(h['labels'])}] {h['text']}")
    (OUT_DIR / "bloco1_grep_audit.txt").write_text("\n".join(grep_lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:14]))
    print("---")
    print("\n".join(grep_lines))


if __name__ == "__main__":
    main()
