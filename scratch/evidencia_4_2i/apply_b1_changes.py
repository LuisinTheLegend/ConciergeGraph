"""Apply Bloco 1 modifications to storage/schema.py, storage/store.py, storage/logic.py, and tests/test_storage_logic.py."""
import pathlib
import sys

# ---------------------------------------------------------------------------
# 1. storage/schema.py
# ---------------------------------------------------------------------------
p_schema = pathlib.Path("storage/schema.py")
s_text = p_schema.read_text(encoding="utf-8")

old_fts_table = """FTS5_TABLE_SQL: str = \"\"\"
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    label, tags, summary, content='nodes', content_rowid='id'
);
\"\"\""""

new_fts_table = """FTS5_TABLE_SQL: str = \"\"\"
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    label, tags, summary, content, content='nodes', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
\"\"\""""

old_fts_triggers = """FTS5_TRIGGERS_SQL: str = \"\"\"
CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
  VALUES('delete', old.id, old.label, old.tags, old.summary);
  INSERT INTO nodes_fts(rowid, label, tags, summary)
  VALUES (new.id, new.label, new.tags, new.summary);
END;
\"\"\""""

new_fts_triggers = """FTS5_TRIGGERS_SQL: str = \"\"\"
CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, label, tags, summary, content)
  VALUES (new.id, new.label, new.tags, new.summary, new.content);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
  VALUES('delete', old.id, old.label, old.tags, old.summary, old.content);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
  VALUES('delete', old.id, old.label, old.tags, old.summary, old.content);
  INSERT INTO nodes_fts(rowid, label, tags, summary, content)
  VALUES (new.id, new.label, new.tags, new.summary, new.content);
END;
\"\"\""""

assert old_fts_table in s_text, "old_fts_table not found"
assert old_fts_triggers in s_text, "old_fts_triggers not found"
s_text = s_text.replace(old_fts_table, new_fts_table, 1)
s_text = s_text.replace(old_fts_triggers, new_fts_triggers, 1)

# Ensure 'import os' is present
if "import os\n" not in s_text and "import os\r\n" not in s_text:
    s_text = s_text.replace("import sqlite3", "import os\nimport sqlite3", 1)

# Update SchemaManager.SCHEMA_VERSION to 3.8.2
s_text = s_text.replace('SCHEMA_VERSION: str = "3.8.0"', 'SCHEMA_VERSION: str = "3.8.2"', 1)

# Add FTS migration logic inside apply_full_schema before version setting
target_marker = "# Ensure the current version is saved in DB."
fts_migration_code = """# FTS5 Migration: upgrade nodes_fts to 4 columns (label, tags, summary, content)
            # with unicode61 remove_diacritics 2.
            cursor = self._conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
            )
            fts_row = cursor.fetchone()
            needs_fts_upgrade = False
            if fts_row and fts_row[0]:
                fts_sql = fts_row[0].lower()
                if "content," not in fts_sql and "content)" not in fts_sql:
                    needs_fts_upgrade = True
                elif "remove_diacritics 2" not in fts_sql:
                    needs_fts_upgrade = True
            elif not fts_row:
                needs_fts_upgrade = True

            if needs_fts_upgrade and fts_row:
                # Non-new database with old nodes_fts schema:
                # 1. Check if database has nodes; if so, create backup before modifying.
                node_count = 0
                try:
                    cur_cnt = self._conn.execute("SELECT COUNT(*) FROM nodes")
                    node_count = cur_cnt.fetchone()[0]
                except Exception:
                    pass

                if node_count > 0:
                    try:
                        db_list = self._conn.execute("PRAGMA database_list").fetchall()
                        db_path = None
                        for db_entry in db_list:
                            if db_entry[1] == "main" and db_entry[2]:
                                db_path = db_entry[2]
                                break
                        if db_path and os.path.exists(db_path) and db_path != ":memory:":
                            bak_path = f"{db_path}.pre_fts_v2.bak"
                            # Use SQLite online backup API
                            backup_conn = sqlite3.connect(bak_path)
                            self._conn.backup(backup_conn)
                            backup_conn.close()
                            logger.info("FTS Migration: backup created at %s", bak_path)
                    except Exception as bak_err:
                        logger.warning("FTS Migration backup warning: %s", bak_err)

                # 2. Drop old triggers and old nodes_fts virtual table (nodes table is NEVER touched)
                self._conn.execute("DROP TRIGGER IF EXISTS nodes_ai;")
                self._conn.execute("DROP TRIGGER IF EXISTS nodes_ad;")
                self._conn.execute("DROP TRIGGER IF EXISTS nodes_au;")
                self._conn.execute("DROP TABLE IF EXISTS nodes_fts;")

                # 3. Recreate nodes_fts with 4 columns + unicode61 remove_diacritics 2 and triggers
                self._conn.executescript(FTS5_TABLE_SQL)
                self._conn.executescript(FTS5_TRIGGERS_SQL)

                # 4. Rebuild and integrity-check
                self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
                self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
                self._conn.commit()
                logger.info("FTS Migration: nodes_fts upgraded to 4 columns with unicode61 remove_diacritics 2.")

            # Ensure the current version is saved in DB."""

assert target_marker in s_text, "target_marker for version saving not found in storage/schema.py"
s_text = s_text.replace(target_marker, fts_migration_code, 1)

# In rebuild_fts_index, add integrity-check
old_rebuild = """            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
            self._conn.commit()
            logger.info("FTS5 index rebuilt successfully.")"""
new_rebuild = """            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")
            self._conn.commit()
            logger.info("FTS5 index rebuilt and integrity-checked successfully.")"""
assert old_rebuild in s_text, "old_rebuild not found in storage/schema.py"
s_text = s_text.replace(old_rebuild, new_rebuild, 1)

p_schema.write_text(s_text, encoding="utf-8")
print("storage/schema.py updated successfully.")

# ---------------------------------------------------------------------------
# 2. storage/store.py (search_symbols restricted to label)
# ---------------------------------------------------------------------------
p_store = pathlib.Path("storage/store.py")
st_text = p_store.read_text(encoding="utf-8")
old_sym_param = 'params: list[Any] = [f\'"{safe_query}"\']'
new_sym_param = 'params: list[Any] = [f\'label : "{safe_query}"\']'
assert old_sym_param in st_text, "old_sym_param not found in storage/store.py"
st_text = st_text.replace(old_sym_param, new_sym_param, 1)
p_store.write_text(st_text, encoding="utf-8")
print("storage/store.py updated successfully.")

# ---------------------------------------------------------------------------
# 3. storage/logic.py (fts_search with BM25 weights and multiword AND/OR fallback)
# ---------------------------------------------------------------------------
p_logic = pathlib.Path("storage/logic.py")
l_text = p_logic.read_text(encoding="utf-8")

old_fts_search = '''    def fts_search(
        self,
        query: str,
        project_uuid: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Text search via FTS5 with BM25 normalized to [0, 1].

        SQLite returns bm25() as negative value (more negative = more relevant).
        We normalize to [0, 1] using:  1.0 - (rank / min_rank)
        where min_rank is the most negative (most relevant) value of the batch.

        Args:
            query: Search text. Special characters are escaped.
            project_uuid: Optional filter by project (Strict Scoping).
            node_type: Targeted filter (FACT, SKILL, INSIGHT, TRAJECTORY, PATCH).
            limit: Maximum results.

        Returns:
            List of dicts with node fields + normalized 'bm25_score' [0, 1].
            Sorted from most relevant to least relevant.
        """
        # Escapes quotes in query to prevent FTS5 injection
        safe_query = query.replace('"', '""')

        # Assembles the SQL query dynamically according to the filters
        sql = """
            SELECT n.*, bm25(nodes_fts) AS rank
            FROM nodes_fts f
            JOIN nodes n ON n.id = f.rowid
            WHERE nodes_fts MATCH ?
        """
        params: list[Any] = [f'"{safe_query}"']

        if project_uuid:
            sql += " AND n.project_uuid = ?"
            params.append(project_uuid)

        if node_type:
            sql += " AND n.node_type = ?"
            params.append(node_type)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        with self._conn.read() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        if not rows:
            return []

        results = [dict(r) for r in rows]

        # Normalizes BM25: the most negative rank becomes 1.0 and the least negative becomes ~0.0
        min_rank = min(r["rank"] for r in results)  # most negative value
        for r in results:
            if min_rank < 0:
                r["bm25_score"] = round(r["rank"] / min_rank, 4)
            else:
                r["bm25_score"] = 1.0
            del r["rank"]  # Removes internal SQLite field

        return results'''

new_fts_search = '''    @staticmethod
    def _build_fts5_queries(query: str) -> tuple[Optional[str], Optional[str]]:
        """Parses and sanitizes raw user query into FTS5-safe expressions.

        Returns:
            (and_query, or_query):
              - and_query: primary expression (exact phrase or terms joined by AND).
              - or_query: secondary fallback expression (terms joined by OR), or None.
        """
        if not query or not isinstance(query, str):
            return None, None

        stripped = query.strip()
        if not stripped:
            return None, None

        # Exact phrase matching: user wrapped query in quotes: "reembolso estorno"
        if (
            len(stripped) >= 2
            and stripped.startswith('"')
            and stripped.endswith('"')
            and '"' not in stripped[1:-1]
        ):
            inner = stripped[1:-1]
            tokens = re.findall(r"\\w+(?:-\\w+)*", inner, flags=re.UNICODE)
            if not tokens:
                return None, None
            exact_expr = '"' + " ".join(tokens) + '"'
            return exact_expr, None

        # General multi-word tokenization: extract words and hyphenated tokens (abacaxi-zeta, ZEBRA-42)
        raw_tokens = re.findall(r"\\w+(?:-\\w+)*", stripped, flags=re.UNICODE)
        if not raw_tokens:
            return None, None

        # Strip standalone boolean operators (AND, OR, NOT, NEAR) to prevent query hijacking
        fts_keywords = {"AND", "OR", "NOT", "NEAR"}
        filtered = [t for t in raw_tokens if t.upper() not in fts_keywords]
        effective_tokens = filtered if filtered else raw_tokens

        escaped = ['"' + t.replace('"', '""') + '"' for t in effective_tokens]
        if len(escaped) == 1:
            return escaped[0], None

        and_query = " AND ".join(escaped)
        or_query = " OR ".join(escaped)
        return and_query, or_query

    def fts_search(
        self,
        query: str,
        project_uuid: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Text search via FTS5 with BM25 normalized to [0, 1].

        BM25 Weights:
            bm25(nodes_fts, 10.0, 5.0, 2.0, 1.0)
            - label (10.0): Highest priority. Filenames/symbol names are direct targets.
            - tags (5.0): High priority domain/syntax markers.
            - summary (2.0): Intermediate priority LLM/macro descriptions.
            - content (1.0): Base priority full text body (prevents long content from drowning labels).

        Multi-word Strategy (F4-024):
            1. Escapes and sanitizes all query tokens against FTS5 syntax injection.
            2. Executes primary query with all terms (AND) or exact phrase.
            3. If primary query yields 0 results, falls back to alternative query (OR).

        Returns:
            List of dicts with node fields + normalized 'bm25_score' [0, 1].
            Sorted from most relevant to least relevant.
        """
        and_query, or_query = self._build_fts5_queries(query)
        if not and_query:
            return []

        # Base query with weighted BM25 across 4 columns (label, tags, summary, content)
        sql_base = """
            SELECT n.*, bm25(nodes_fts, 10.0, 5.0, 2.0, 1.0) AS rank
            FROM nodes_fts f
            JOIN nodes n ON n.id = f.rowid
            WHERE nodes_fts MATCH ?
        """
        params_base: list[Any] = []
        if project_uuid:
            sql_base += " AND n.project_uuid = ?"
            params_base.append(project_uuid)
        if node_type:
            sql_base += " AND n.node_type = ?"
            params_base.append(node_type)
        sql_base += " ORDER BY rank LIMIT ?"
        params_base.append(limit)

        def _execute_match(match_expr: str) -> list[Any]:
            p = [match_expr] + params_base
            with self._conn.read() as conn:
                return conn.execute(sql_base, tuple(p)).fetchall()

        # Step 1: Attempt AND query
        rows = _execute_match(and_query)

        # Step 2: Fallback to OR query if AND yielded no results
        if not rows and or_query:
            rows = _execute_match(or_query)

        if not rows:
            return []

        results = [dict(r) for r in rows]

        # Normalizes BM25: the most negative rank becomes 1.0 and the least negative becomes ~0.0
        min_rank = min(r["rank"] for r in results)
        for r in results:
            if min_rank < 0:
                r["bm25_score"] = round(r["rank"] / min_rank, 4)
            else:
                r["bm25_score"] = 1.0
            del r["rank"]

        return results'''

assert old_fts_search in l_text, "old_fts_search not found in storage/logic.py"
l_text = l_text.replace(old_fts_search, new_fts_search, 1)

# Also update fts_rebuild to include integrity-check
old_fts_rebuild = '''    def fts_rebuild(self) -> None:
        """Rebuilds the complete FTS5 index.

        Use after massive ingestion (concierge mine) to optimize performance.
        """
        def _do(conn: Any) -> None:
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

        self._conn.write(_do)
        logger.info("FTS5 index rebuilt successfully.")'''

new_fts_rebuild = '''    def fts_rebuild(self) -> None:
        """Rebuilds the complete FTS5 index and verifies integrity.

        Use after massive ingestion (concierge mine) to optimize performance.
        """
        def _do(conn: Any) -> None:
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('integrity-check');")

        self._conn.write(_do)
        logger.info("FTS5 index rebuilt and integrity-checked successfully.")'''

assert old_fts_rebuild in l_text, "old_fts_rebuild not found in storage/logic.py"
l_text = l_text.replace(old_fts_rebuild, new_fts_rebuild, 1)

p_logic.write_text(l_text, encoding="utf-8")
print("storage/logic.py updated successfully.")

# ---------------------------------------------------------------------------
# 4. tests/test_storage_logic.py (update mock FTS5 table to match schema)
# ---------------------------------------------------------------------------
p_test_logic = pathlib.Path("tests/test_storage_logic.py")
tl_text = p_test_logic.read_text(encoding="utf-8")

old_tl_fts = """            -- FTS5 virtual table for text search
            CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                label, body, content=nodes, content_rowid=id
            );

            -- FTS5 sync triggers
            CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                INSERT INTO nodes_fts(rowid, label, body)
                VALUES (new.id, new.label, new.body);
            END;

            CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, label, body)
                VALUES ('delete', old.id, old.label, old.body);
            END;

            CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, label, body)
                VALUES ('delete', old.id, old.label, old.body);
                INSERT INTO nodes_fts(rowid, label, body)
                VALUES (new.id, new.label, new.body);
            END;"""

new_tl_fts = """            -- FTS5 virtual table for text search
            CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                label, tags, summary, content, content=nodes, content_rowid=id,
                tokenize='unicode61 remove_diacritics 2'
            );

            -- FTS5 sync triggers
            CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                INSERT INTO nodes_fts(rowid, label, tags, summary, content)
                VALUES (new.id, new.label, COALESCE(new.tags, ''), COALESCE(new.summary, ''), COALESCE(new.content, new.body));
            END;

            CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
                VALUES ('delete', old.id, old.label, COALESCE(old.tags, ''), COALESCE(old.summary, ''), COALESCE(old.content, old.body));
            END;

            CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary, content)
                VALUES ('delete', old.id, old.label, COALESCE(old.tags, ''), COALESCE(old.summary, ''), COALESCE(old.content, old.body));
                INSERT INTO nodes_fts(rowid, label, tags, summary, content)
                VALUES (new.id, new.label, COALESCE(new.tags, ''), COALESCE(new.summary, ''), COALESCE(new.content, new.body));
            END;"""

assert old_tl_fts in tl_text, "old_tl_fts not found in tests/test_storage_logic.py"
tl_text = tl_text.replace(old_tl_fts, new_tl_fts, 1)
p_test_logic.write_text(tl_text, encoding="utf-8")
print("tests/test_storage_logic.py updated successfully.")

