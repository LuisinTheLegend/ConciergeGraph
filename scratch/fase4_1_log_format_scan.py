import ast
import os
import re
from pathlib import Path

# Specifier regex for % formatting (excluding %%)
# % followed by optional flags, width, precision, and conversion char
SPECIFIER_RE = re.compile(r"%(?:%|(?:\([a-zA-Z0-9_]+\))?[-+ #0]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrsa%])")

LOG_METHODS = {"debug", "info", "warning", "warn", "error", "critical", "exception"}

PRODUCTION_DIRS = [
    "core",
    "ingestion",
    "interface",
    "services",
    "storage",
    "agent",
    "agents",
]
ROOT_FILES = ["main.py"]

def count_format_specifiers(fmt_str: str) -> int:
    matches = SPECIFIER_RE.findall(fmt_str)
    return sum(1 for m in matches if m != "%%")

def scan_file(filepath: Path, root: Path) -> list[dict]:
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except Exception as e:
        return [{"file": str(filepath.relative_to(root)).replace("\\", "/"), "line": 0, "error": f"Parse error: {e}"}]

    rel_file = str(filepath.relative_to(root)).replace("\\", "/")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = None
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id

        if func_name not in LOG_METHODS:
            continue

        if not node.args:
            continue

        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            fmt_str = first_arg.value
            expected_args = count_format_specifiers(fmt_str)
            actual_args = len(node.args) - 1

            if actual_args > expected_args:
                findings.append({
                    "file": rel_file,
                    "line": node.lineno,
                    "method": func_name,
                    "format_string": fmt_str,
                    "specifiers_count": expected_args,
                    "args_provided": actual_args,
                    "excess": actual_args - expected_args,
                })

    return findings

def main():
    root = Path(__file__).parent.parent.resolve()
    print(f"Scanning production code in: {root}")
    all_findings = []

    files_to_scan = []
    for d in PRODUCTION_DIRS:
        dp = root / d
        if dp.exists():
            files_to_scan.extend(dp.rglob("*.py"))

    for rf in ROOT_FILES:
        fp = root / rf
        if fp.exists():
            files_to_scan.append(fp)

    files_to_scan = sorted(set(files_to_scan))
    print(f"Total production files to scan: {len(files_to_scan)}")

    for f in files_to_scan:
        findings = scan_file(f, root)
        all_findings.extend(findings)

    print(f"\nScan complete. Total findings: {len(all_findings)}")
    for f in all_findings:
        print(f"  {f['file']}:{f['line']} -> {f['method']}(\"{f['format_string']}\", ...) [expected {f['specifiers_count']}, got {f['args_provided']}, excess: {f['excess']}]")

if __name__ == "__main__":
    main()
