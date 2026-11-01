"""scratch/evidencia_4_2i/probe_xfail_forms.py

Verifica qual forma de marcação de falha esperada estrita funciona em
unittest.TestCase sob pytest:
  1. @pytest.mark.xfail(strict=True, reason="...")
  2. @unittest.expectedFailure
Testando ambos quando a asserção falha (comportamento atual do BL-015) e
quando a asserção passa (simulando a correção do BL-015 -> deve falhar a suíte com XPASS estrito).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

SAMPLE_TEST = """
import unittest
import pytest

class SampleCase(unittest.TestCase):
    @pytest.mark.xfail(strict=True, reason="BL-015: default_state is EXECUTION instead of PLANNING (see audits/backlog-final.md#L309)")
    def test_pytest_xfail_strict(self):
        self.assertEqual("{actual}", "PLANNING")

    @unittest.expectedFailure
    def test_unittest_expected_failure(self):
        self.assertEqual("{actual}", "PLANNING")
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test_sample.py"
        for mode, actual in [("WHEN_FAILING_BL015_OPEN", "EXECUTION"), ("WHEN_PASSING_BL015_FIXED", "PLANNING")]:
            p.write_text(SAMPLE_TEST.format(actual=actual), encoding="utf-8")
            for test_name in ["test_pytest_xfail_strict", "test_unittest_expected_failure"]:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", str(p), "-k", test_name, "-v", "-rxX"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                print(f"=== {mode} | {test_name} | rc={proc.returncode} ===")
                for ln in (proc.stdout + proc.stderr).splitlines():
                    if any(k in ln for k in ("test_", "XPASS", "xfail", " passed", " failed", "REASON")):
                        print("  ", ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

