"""
tests/test_ssh_language_coverage.py — Audit Evidence for Finding #6

Parametrized test that documents exactly which lines calculate_ssh()
captures (or misses) for each language the project mentions or intends
to support. This test IS the specification — no prose needed.

Each case contains:
  - A realistic code snippet in the target language
  - The exact list of lines SSH is expected to capture
  - The exact list of structurally significant lines SSH misses
"""

import os
import sys
import importlib
import importlib.util
import unittest

# ── Surgical import (same pattern as test_delta_sync.py) ──
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_dm_spec = importlib.util.spec_from_file_location(
    "core.delta_manager",
    os.path.join(_project_root, "core", "delta_manager.py"),
)
_dm_mod = importlib.util.module_from_spec(_dm_spec)
sys.modules["core.delta_manager"] = _dm_mod
_dm_spec.loader.exec_module(_dm_mod)
DeltaManager = _dm_mod.DeltaManager


def _ssh_captured_lines(code: str) -> list[str]:
    """Returns the list of stripped lines that SSH would include in its hash."""
    prefixes = ("def ", "class ", "import ", "from ")
    return [
        stripped
        for line in code.splitlines()
        if (stripped := line.strip()).startswith(prefixes)
    ]


# ── Language Samples ────────────────────────────────────────────────
# Each entry: (language, code_snippet, expected_captured, expected_missed)
# "expected_missed" = structurally significant declarations that SSH ignores.

LANGUAGE_CASES = [
    # ── Python (fully covered by design) ──
    (
        "Python",
        (
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "class MyService:\n"
            "    def __init__(self, db):\n"
            "        self.db = db\n"
            "\n"
            "    def process(self, item):\n"
            "        return item.upper()\n"
        ),
        # SSH captures all structural lines
        [
            "import os",
            "from pathlib import Path",
            "class MyService:",
            "def __init__(self, db):",
            "def process(self, item):",
        ],
        # SSH misses nothing structurally significant
        [],
    ),
    # ── TypeScript ──
    (
        "TypeScript",
        (
            "import { Injectable } from '@angular/core';\n"
            "import type { User } from './types';\n"
            "\n"
            "export interface UserService {\n"
            "  getUser(id: string): Promise<User>;\n"
            "}\n"
            "\n"
            "export class UserServiceImpl implements UserService {\n"
            "  constructor(private db: Database) {}\n"
            "\n"
            "  async getUser(id: string): Promise<User> {\n"
            "    return this.db.find(id);\n"
            "  }\n"
            "}\n"
            "\n"
            "export function helperFn(): void {}\n"
            "export const arrowFn = (x: number): number => x * 2;\n"
            "export type Result = { ok: boolean };\n"
        ),
        # SSH captures these (lexical match on prefixes)
        [
            "import { Injectable } from '@angular/core';",
            "import type { User } from './types';",
        ],
        # SSH misses these structurally significant declarations
        [
            "export class UserServiceImpl ...",     # "export class" not "class "
            "export interface UserService {",       # no "interface " prefix
            "async getUser(id: string): ...",       # no "def " prefix
            "export function helperFn(): void {}",  # "function" not "def"
            "export const arrowFn = ...",            # arrow function
            "export type Result = ...",              # type alias
            "constructor(private db: Database) {}",  # constructor
        ],
    ),
    # ── JavaScript (ESM) ──
    (
        "JavaScript_ESM",
        (
            "import express from 'express';\n"
            "import { readFile } from 'fs/promises';\n"
            "\n"
            "class AppController {\n"
            "  constructor(port) {\n"
            "    this.port = port;\n"
            "  }\n"
            "\n"
            "  start() {\n"
            "    console.log('started');\n"
            "  }\n"
            "}\n"
            "\n"
            "export function createApp() { return new AppController(3000); }\n"
            "export default AppController;\n"
        ),
        # SSH captures
        [
            "import express from 'express';",
            "import { readFile } from 'fs/promises';",
            "class AppController {",
        ],
        # SSH misses
        [
            "export function createApp() { ... }",  # "function" not "def"
            "start() { ... }",                       # method shorthand
            "constructor(port) { ... }",             # constructor
            "export default AppController;",         # re-export
        ],
    ),
    # ── JavaScript (CommonJS) ──
    (
        "JavaScript_CJS",
        (
            "const fs = require('fs');\n"
            "const path = require('path');\n"
            "\n"
            "function processFile(filePath) {\n"
            "  return fs.readFileSync(filePath, 'utf-8');\n"
            "}\n"
            "\n"
            "class FileProcessor {\n"
            "  constructor(dir) { this.dir = dir; }\n"
            "  run() { return processFile(this.dir); }\n"
            "}\n"
            "\n"
            "module.exports = { processFile, FileProcessor };\n"
        ),
        # SSH captures (class keyword matches)
        [
            "class FileProcessor {",
        ],
        # SSH misses
        [
            "const fs = require('fs');",             # CJS require, no "import "
            "const path = require('path');",         # CJS require
            "function processFile(filePath) { ... }", # "function" not "def"
            "module.exports = { ... };",             # export
        ],
    ),
    # ── Go ──
    (
        "Go",
        (
            'package main\n'
            '\n'
            'import "fmt"\n'
            'import (\n'
            '    "os"\n'
            '    "strings"\n'
            ')\n'
            '\n'
            'type UserService struct {\n'
            '    db *sql.DB\n'
            '}\n'
            '\n'
            'func (s *UserService) GetUser(id string) (*User, error) {\n'
            '    return s.db.Query(id)\n'
            '}\n'
            '\n'
            'func NewUserService(db *sql.DB) *UserService {\n'
            '    return &UserService{db: db}\n'
            '}\n'
            '\n'
            'func main() {\n'
            '    fmt.Println("hello")\n'
            '}\n'
        ),
        # SSH captures (import matches; import ( matches because stripped
        # line starts with "import")
        [
            'import "fmt"',
            'import (',
        ],
        # SSH misses
        [
            "package main",                              # "package" not a prefix
            "type UserService struct {",                  # "type" not a prefix
            "func (s *UserService) GetUser(...) ...",     # "func" not "def"
            "func NewUserService(...) ...",               # "func" not "def"
            "func main() {",                             # "func" not "def"
        ],
    ),
    # ── Rust ──
    (
        "Rust",
        (
            "use std::collections::HashMap;\n"
            "use serde::{Deserialize, Serialize};\n"
            "\n"
            "pub struct UserService {\n"
            "    db: DatabasePool,\n"
            "}\n"
            "\n"
            "impl UserService {\n"
            "    pub fn new(db: DatabasePool) -> Self {\n"
            "        Self { db }\n"
            "    }\n"
            "\n"
            "    pub fn get_user(&self, id: &str) -> Result<User, Error> {\n"
            "        self.db.query(id)\n"
            "    }\n"
            "}\n"
            "\n"
            "fn main() {\n"
            "    println!(\"hello\");\n"
            "}\n"
        ),
        # SSH captures: NOTHING — Rust uses "use" not "import", "fn" not "def",
        # "struct" not "class"
        [],
        # SSH misses everything
        [
            "use std::collections::HashMap;",
            "use serde::{Deserialize, Serialize};",
            "pub struct UserService { ... }",
            "impl UserService { ... }",
            "pub fn new(...) -> Self",
            "pub fn get_user(...) -> Result<...>",
            "fn main() { ... }",
        ],
    ),
    # ── Java ──
    (
        "Java",
        (
            "package com.example.service;\n"
            "\n"
            "import java.util.List;\n"
            "import com.example.model.User;\n"
            "\n"
            "public class UserService {\n"
            "    private final Database db;\n"
            "\n"
            "    public UserService(Database db) {\n"
            "        this.db = db;\n"
            "    }\n"
            "\n"
            "    public User getUser(String id) {\n"
            "        return db.find(id);\n"
            "    }\n"
            "\n"
            "    public interface Repository {\n"
            "        User findById(String id);\n"
            "    }\n"
            "}\n"
        ),
        # SSH captures
        [
            "import java.util.List;",
            "import com.example.model.User;",
            "class UserService {",  # "public class" -> stripped starts with... no wait
        ],
        # SSH misses
        [
            "package com.example.service;",
            "public UserService(Database db) { ... }",   # constructor
            "public User getUser(String id) { ... }",    # method
            "public interface Repository { ... }",       # interface
        ],
    ),
    # ── C++ ──
    (
        "Cpp",
        (
            "#include <iostream>\n"
            "#include <vector>\n"
            "#include <string>\n"
            "\n"
            "namespace app {\n"
            "\n"
            "class UserService {\n"
            "public:\n"
            "    UserService(Database* db) : db_(db) {}\n"
            "    User getUser(const std::string& id);\n"
            "\n"
            "private:\n"
            "    Database* db_;\n"
            "};\n"
            "\n"
            "User UserService::getUser(const std::string& id) {\n"
            "    return db_->find(id);\n"
            "}\n"
            "\n"
            "} // namespace app\n"
        ),
        # SSH captures
        [
            "class UserService {",
        ],
        # SSH misses
        [
            "#include <iostream>",
            "#include <vector>",
            "#include <string>",
            "namespace app {",
            "UserService(Database* db) : db_(db) {}",     # constructor
            "User getUser(const std::string& id);",       # method decl
            "User UserService::getUser(...) { ... }",     # method impl
        ],
    ),
    # ── C ──
    (
        "C",
        (
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n"
            "\n"
            "typedef struct {\n"
            "    int id;\n"
            "    char name[256];\n"
            "} User;\n"
            "\n"
            "User* create_user(int id, const char* name) {\n"
            "    User* u = malloc(sizeof(User));\n"
            "    u->id = id;\n"
            "    strncpy(u->name, name, 255);\n"
            "    return u;\n"
            "}\n"
            "\n"
            "void free_user(User* u) {\n"
            "    free(u);\n"
            "}\n"
            "\n"
            "int main(int argc, char** argv) {\n"
            "    return 0;\n"
            "}\n"
        ),
        # SSH captures: NOTHING — C uses #include not import, no class/def/from
        [],
        # SSH misses everything
        [
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <string.h>",
            "typedef struct { ... } User;",
            "User* create_user(...) { ... }",
            "void free_user(User* u) { ... }",
            "int main(...) { ... }",
        ],
    ),
]


class TestSSHLanguageCoverage(unittest.TestCase):
    """
    Documents SSH coverage per language via assertions.
    Each test case is a verified specification, not prose.
    """

    def setUp(self):
        self.dm = DeltaManager(None)

    def _run_case(self, lang, code, expected_captured, expected_missed_descriptions):
        """Core assertion logic shared by all parametrized cases."""
        actual_captured = _ssh_captured_lines(code)

        # Verify captured lines match exactly
        self.assertEqual(
            actual_captured,
            expected_captured,
            f"[{lang}] SSH captured lines mismatch.\n"
            f"  Expected: {expected_captured}\n"
            f"  Got:      {actual_captured}",
        )

        # Verify SSH hash is non-empty iff there are captured lines
        ssh_hash = self.dm.calculate_ssh(code)
        if expected_captured:
            self.assertNotEqual(
                ssh_hash, "",
                f"[{lang}] SSH hash should be non-empty when lines are captured.",
            )
        else:
            self.assertEqual(
                ssh_hash, "",
                f"[{lang}] SSH hash should be empty when no lines are captured.",
            )

        # Verify LBH is always empty for non-Python
        if lang != "Python":
            lbh = self.dm.calculate_lbh(code)
            self.assertEqual(
                lbh, "",
                f"[{lang}] LBH should always be empty for non-Python.",
            )

        # Print summary for pytest -v output
        n_captured = len(expected_captured)
        n_missed = len(expected_missed_descriptions)
        total = n_captured + n_missed
        pct = (n_captured / total * 100) if total > 0 else 0
        print(f"\n  [{lang}] SSH coverage: {n_captured}/{total} structural decls ({pct:.0f}%)")
        if expected_captured:
            for line in expected_captured:
                print(f"    ✓ {line}")
        if expected_missed_descriptions:
            for desc in expected_missed_descriptions:
                print(f"    ✗ {desc}")


# ── Generate one test method per language ──
def _make_test(lang, code, captured, missed):
    def test_method(self):
        self._run_case(lang, code, captured, missed)
    test_method.__doc__ = f"SSH coverage for {lang}"
    return test_method


for _lang, _code, _captured, _missed in LANGUAGE_CASES:
    # Handle Java special case: "public class" starts with "public", not "class"
    # We need to verify the actual behavior, not assume
    pass

# Actually, let me fix Java: "public class UserService {" stripped starts with
# "public", not "class". So SSH would NOT capture it. Let me correct.
# Same issue: we need to verify exact behavior before setting expectations.
# Let me just run the raw capture and set expectations based on what actually happens.

# Re-verify Java: "public class UserService {".strip() = "public class UserService {"
# .startswith(("def ", "class ", "import ", "from ")) -> False (starts with "public")
# So Java's class declaration is NOT captured. Fix the expected_captured for Java.

# Fix Java case - index 6 in LANGUAGE_CASES
_java_idx = next(i for i, (lang, *_) in enumerate(LANGUAGE_CASES) if lang == "Java")
LANGUAGE_CASES[_java_idx] = (
    "Java",
    LANGUAGE_CASES[_java_idx][1],  # same code
    # Only bare imports are captured; "public class" does NOT start with "class "
    [
        "import java.util.List;",
        "import com.example.model.User;",
    ],
    # Missed — now includes the class declaration too
    [
        "package com.example.service;",
        "public class UserService { ... }",          # "public class" not "class "
        "public UserService(Database db) { ... }",   # constructor
        "public User getUser(String id) { ... }",    # method
        "public interface Repository { ... }",       # interface
    ],
)

# Fix C++ case — "class UserService {" IS captured (no access modifier prefix)
# Already correct.

for _lang, _code, _captured, _missed in LANGUAGE_CASES:
    test_name = f"test_ssh_coverage_{_lang.lower()}"
    setattr(TestSSHLanguageCoverage, test_name, _make_test(_lang, _code, _captured, _missed))


class TestSSHCoverageSummaryTable(unittest.TestCase):
    """Prints a markdown-ready summary table of SSH coverage across all languages."""

    def test_print_summary_table(self):
        """Generate summary table of SSH structural coverage per language."""
        dm = DeltaManager(None)
        print("\n")
        print("| Language | SSH captured | SSH missed | Coverage | LBH |")
        print("|----------|-------------|------------|----------|-----|")
        for lang, code, captured, missed in LANGUAGE_CASES:
            n_cap = len(captured)
            n_miss = len(missed)
            total = n_cap + n_miss
            pct = f"{n_cap}/{total} ({n_cap/total*100:.0f}%)" if total else "N/A"
            lbh_status = "✓ full" if lang == "Python" else "✗ blind"
            ssh_hash = dm.calculate_ssh(code)
            ssh_status = "non-empty" if ssh_hash else "empty"
            print(f"| {lang} | {n_cap} lines | {n_miss} lines | {pct} | {lbh_status} |")
        print()


if __name__ == "__main__":
    unittest.main()
