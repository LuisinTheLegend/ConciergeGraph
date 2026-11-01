"""Test FTS5 parser/escaper against edge cases and injection payloads."""
import re
import sqlite3
from typing import Optional

_FTS5_BOOL_KEYWORDS = frozenset({"AND", "OR", "NOT", "NEAR"})


def build_fts5_queries(query: str) -> tuple[Optional[str], Optional[str]]:
    """Build (and_query, or_query) for SQLite FTS5 from raw user query.

    Rules:
    - If query is empty or contains no word characters (\\w), returns (None, None).
    - If the user wraps the entire query in double quotes ("...") without internal
      unescaped quotes, treats it as an exact phrase query: ('"term1 term2"', None).
    - Otherwise splits the query into terms, strips FTS5 syntax characters
      (", *, (, ), :, ^, etc.), drops standalone FTS5 boolean operator tokens
      (AND, OR, NOT, NEAR) when mixed with search terms so injected operators
      cannot change query semantics, and wraps each term in double quotes.
    - Returns ('"t1" AND "t2"', '"t1" OR "t2"') for multi-term queries, or
      ('"t1"', None) for single-term queries.
    """
    if not query or not isinstance(query, str):
        return None, None

    stripped = query.strip()
    if not stripped:
        return None, None

    # Exact phrase mode when wrapped in double quotes: "reembolso estorno"
    if (
        len(stripped) >= 2
        and stripped.startswith('"')
        and stripped.endswith('"')
        and '"' not in stripped[1:-1]
    ):
        inner = stripped[1:-1]
        # Extract word/hyphen tokens so no FTS5 control character can break syntax
        phrase_tokens = re.findall(r"\w+(?:-\w+)*", inner, flags=re.UNICODE)
        if not phrase_tokens:
            return None, None
        exact_expr = '"' + " ".join(phrase_tokens) + '"'
        return exact_expr, None

    # General mode: extract tokens (words or hyphenated identifiers like abacaxi-zeta, ZEBRA-42)
    raw_tokens = re.findall(r"\w+(?:-\w+)*", stripped, flags=re.UNICODE)
    if not raw_tokens:
        return None, None

    # If there are non-keyword tokens, filter out standalone FTS5 boolean operator words
    # (AND, OR, NOT, NEAR) so an attacker passing 'foo" OR "bar' or 'foo NOT bar'
    # cannot alter query semantics or inject operators.
    non_kw_tokens = [t for t in raw_tokens if t.upper() not in _FTS5_BOOL_KEYWORDS]
    effective_tokens = non_kw_tokens if non_kw_tokens else raw_tokens

    escaped_terms = ['"' + t.replace('"', '""') + '"' for t in effective_tokens]
    if len(escaped_terms) == 1:
        return escaped_terms[0], None

    and_query = " AND ".join(escaped_terms)
    or_query = " OR ".join(escaped_terms)
    return and_query, or_query


conn = sqlite3.connect(":memory:")
conn.execute(
    "CREATE VIRTUAL TABLE t USING fts5(label, tags, summary, content, tokenize='unicode61 remove_diacritics 2')"
)
conn.execute(
    "INSERT INTO t VALUES (?, ?, ?, ?)",
    (
        "doc1.md",
        "financeiro",
        None,
        "Texto com abacaxi-zeta, violoncelo-ômega, farol-sigma, alíquota de calcular_imposto_renda e código ZEBRA-42. Reembolso autorizado após análise de estorno.",
    ),
)

test_inputs = [
    "",
    "   ",
    "*** () :NEAR: --- \"\"",
    '""',
    "abacaxi-zeta",
    "violoncelo-omega",
    "reembolso estorno",
    '"reembolso estorno"',
    '"reembolso autorizado"',
    "reembolso inexistente_xyz",
    'reembolso" OR "1"="1',
    'NEAR(reembolso, estorno, 5)',
    'label:secret* OR content:password*',
    'reembolso ) OR ( estorno * ^ : -',
    'AND OR NOT NEAR',
    '"unclosed quote reembolso',
]

for inp in test_inputs:
    q_and, q_or = build_fts5_queries(inp)
    res_and = conn.execute("SELECT label FROM t WHERE t MATCH ?", (q_and,)).fetchall() if q_and else []
    res_or = conn.execute("SELECT label FROM t WHERE t MATCH ?", (q_or,)).fetchall() if (not res_and and q_or) else []
    print(f"IN={inp!r:36s} -> AND={q_and!r:35s} res={res_and or res_or}")
