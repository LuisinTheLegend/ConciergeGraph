"""tests/test_fts_code_search.py — SDD-SURVIVAL-F4-018 & F4-024

Suíte de testes para:
- F4-018: FTS5 com 4 colunas (label, tags, summary, content), unicode61 remove_diacritics 2,
          rebuild/integrity-check, busca por conteúdo com summary IS NULL, search_symbols restrito a label,
          pesos BM25 (w_label > w_content), migração versionada e idempotente com backup.
- F4-024: Consulta multi-palavra em fts_search com AND -> fallback OR, suporte a frase exata ("..."),
          tratamento de consultas vazias/símbolos e imunidade total contra injeção de sintaxe FTS5.
"""

import hashlib
import os
import sqlite3
import tempfile
import unittest

from storage.connection import ConnectionManager
from storage.logic import GraphLogic
from storage.schema import SchemaManager
from storage.store import SqliteStore


class TestFTSCodeSearchAndInjection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_fts.db")
        self.store = SqliteStore(db_path=self.db_path)
        self.project_uuid = "proj-fts-test-001"
        self.store.create_project(
            uuid=self.project_uuid,
            folder_name="test_proj",
            primary_wing="geral",
            summary="Projeto de teste FTS",
        )

    def tearDown(self):
        if hasattr(self, "store") and self.store:
            self.store.close()
            self.store = None
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _insert_test_node(
        self,
        label: str,
        content: str,
        summary: str = None,
        tags: str = "test",
        node_type: str = "FACT",
        item_type: str = "file",
        status: str = "ACTIVE",
    ) -> int:
        def _write(conn: sqlite3.Connection):
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO nodes (project_uuid, label, summary, content, node_type, type, tags, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (self.project_uuid, label, summary, content, node_type, item_type, tags, status),
            )
            return cur.lastrowid

        return self.store._conn_mgr.write(_write)

    # -------------------------------------------------------------------------
    # F4-018: Conteúdo indexado mesmo com summary IS NULL
    # -------------------------------------------------------------------------
    def test_sentinel_words_found_in_content_when_summary_is_null(self):
        """As 3 palavras-sentinela presentes APENAS em nodes.content (com summary IS NULL e label neutro) devem ser encontradas."""
        sentinels = ["abacaxi-zeta", "violoncelo-ômega", "farol-sigma"]
        for idx, s in enumerate(sentinels, start=1):
            self._insert_test_node(
                label=f"arquivo_neutro_{idx}.py",
                content=f"Este arquivo descreve a implementação de {s} em detalhes no corpo do código.",
                summary=None,
                tags="sistema",
            )

        for s in sentinels:
            res = self.store.fts_search(query=s, project_uuid=self.project_uuid)
            self.assertTrue(
                len(res) > 0,
                f"Palavra-sentinela {s!r} não foi encontrada pela busca FTS quando presente apenas no content!",
            )
            self.assertEqual(res[0]["summary"], None)
            self.assertIn(s, res[0]["content"])

    def test_diacritics_insensitivity(self):
        """Busca por 'aliquota' deve achar 'alíquota' e 'violoncelo-omega' deve achar 'violoncelo-ômega'."""
        self._insert_test_node(
            label="fiscal.py",
            content="Cálculo especial de alíquota para regime monofásico.",
            summary=None,
        )
        self._insert_test_node(
            label="musica.py",
            content="Concerto sinfônico executado com violoncelo-ômega.",
            summary=None,
        )

        res_aliquota = self.store.fts_search(
            query="aliquota", project_uuid=self.project_uuid
        )
        self.assertTrue(
            any("alíquota" in r["content"] for r in res_aliquota),
            "Busca por 'aliquota' (sem acento) não encontrou 'alíquota'!",
        )

        res_omega = self.store.fts_search(
            query="violoncelo-omega", project_uuid=self.project_uuid
        )
        self.assertTrue(
            any("violoncelo-ômega" in r["content"] for r in res_omega),
            "Busca por 'violoncelo-omega' não encontrou 'violoncelo-ômega'!",
        )

    def test_identifiers_matching(self):
        """Identificadores técnicos com sublinhado e hífen devem ser encontrados."""
        self._insert_test_node(
            label="financeiro.py",
            content="def calcular_imposto_renda(): return 42\n# Tag de controle ZEBRA-42",
            summary=None,
        )

        res_ident = self.store.fts_search(
            query="calcular_imposto_renda", project_uuid=self.project_uuid
        )
        self.assertTrue(
            len(res_ident) > 0 and "calcular_imposto_renda" in res_ident[0]["content"],
            "Identificador 'calcular_imposto_renda' não foi encontrado!",
        )

        res_tag = self.store.fts_search(
            query="ZEBRA-42", project_uuid=self.project_uuid
        )
        self.assertTrue(
            len(res_tag) > 0 and "ZEBRA-42" in res_tag[0]["content"],
            "Identificador 'ZEBRA-42' não foi encontrado!",
        )

    # -------------------------------------------------------------------------
    # Mudança 2: search_symbols restrito à coluna label
    # -------------------------------------------------------------------------
    def test_search_symbols_restricted_to_label_regression(self):
        """search_symbols deve encontrar símbolos cujo label bate com a query,
        mas DEVE IGNORAR nós cujo termo aparece apenas em content."""
        # Nó 1: label contém o termo (símbolo real)
        self._insert_test_node(
            label="calcular_imposto_renda",
            content="corpo de função",
            node_type="FUNCTION",
            item_type="function",
        )
        # Nó 2: label NÃO contém o termo, mas content contém
        self._insert_test_node(
            label="outro_modulo_consumidor.py",
            content="from financeiro import calcular_imposto_renda\nchama calcular_imposto_renda aqui",
            node_type="FUNCTION",
            item_type="function",
        )

        symbols = self.store.search_symbols(
            query="calcular_imposto_renda", project_uuid=self.project_uuid
        )
        labels = [s["label"] for s in symbols]
        self.assertIn(
            "calcular_imposto_renda",
            labels,
            "search_symbols deveria encontrar símbolo cujo label é 'calcular_imposto_renda'",
        )
        self.assertNotIn(
            "outro_modulo_consumidor.py",
            labels,
            "search_symbols NÃO deve casar arquivos cujo termo aparece apenas em content!",
        )

    # -------------------------------------------------------------------------
    # Mudança 3: Pesos BM25 (label mais pesado que content)
    # -------------------------------------------------------------------------
    def test_bm25_weights_label_ranks_before_content_only(self):
        """Um nó cujo label contém o termo deve ser ranqueado à frente de outro cujo termo está apenas no content."""
        term = "autenticacao"
        # Nó A: termo no label
        id_a = self._insert_test_node(
            label=f"modulo_{term}_oauth.py",
            content="implementação geral de segurança sem o termo repetido",
            summary=None,
        )
        # Nó B: termo apenas no content
        id_b = self._insert_test_node(
            label="utils_diversos.py",
            content=f"funções auxiliares para {term} de usuários no sistema",
            summary=None,
        )

        res = self.store.fts_search(query=term, project_uuid=self.project_uuid)
        self.assertTrue(len(res) >= 2, f"Esperava encontrar ambos os nós para {term}")
        self.assertEqual(
            res[0]["id"],
            id_a,
            f"O nó com '{term}' no label deveria vir em 1º lugar (BM25 ponderado). Resultados: {[r['label'] for r in res]}",
        )

    # -------------------------------------------------------------------------
    # F4-024: Multi-palavra, Fallback OR, Frase Exata e Imunidade a Injeção
    # -------------------------------------------------------------------------
    def test_multiword_and_fallback_to_or(self):
        """Busca multi-palavra tenta AND primeiro; se não houver intersecção, faz fallback para OR."""
        # Doc 1 tem "reembolso" e "estorno" não adjacentes
        id_both = self._insert_test_node(
            label="doc_ambos.md",
            content="O cliente solicitou reembolso de compra. O processo de estorno bancário foi concluído.",
            summary=None,
        )
        # Doc 2 tem apenas "reembolso"
        id_reemb = self._insert_test_node(
            label="doc_reembolso.md",
            content="Regras gerais de reembolso para cancelamento de passagens.",
            summary=None,
        )

        # 1. Busca com ambos os termos presentes em Doc 1: deve retornar Doc 1 via AND
        res_and = self.store.fts_search(
            query="reembolso estorno", project_uuid=self.project_uuid
        )
        self.assertTrue(len(res_and) > 0)
        self.assertEqual(res_and[0]["id"], id_both)

        # 2. Busca com um termo existente e outro inexistente: AND falha, fallback OR encontra os docs com 'reembolso'
        res_or = self.store.fts_search(
            query="reembolso palavra_inexistente_xyz_42",
            project_uuid=self.project_uuid,
        )
        ids_or = [r["id"] for r in res_or]
        self.assertIn(
            id_reemb, ids_or, "Fallback OR deveria retornar docs contendo 'reembolso'"
        )
        self.assertIn(
            id_both, ids_or, "Fallback OR deveria retornar docs contendo 'reembolso'"
        )

    def test_exact_phrase_matching_with_quotes(self):
        """Consulta entre aspas (\"...\") deve exigir frase exata."""
        # Doc 1: palavras adjacentes na ordem exata
        id_exact = self._insert_test_node(
            label="frase_exata.md",
            content="Protocolo de reembolso estorno imediato.",
            summary=None,
        )
        # Doc 2: palavras não adjacentes
        id_separated = self._insert_test_node(
            label="frase_separada.md",
            content="reembolso feito hoje; outro dia faremos estorno.",
            summary=None,
        )

        res = self.store.fts_search(
            query='"reembolso estorno"', project_uuid=self.project_uuid
        )
        ids = [r["id"] for r in res]
        self.assertIn(id_exact, ids, "Frase exata deve casar palavras adjacentes")
        self.assertNotIn(
            id_separated, ids, "Frase exata NÃO deve casar palavras não adjacentes"
        )

    def test_empty_and_symbol_only_queries_safe_noop(self):
        """Consultas vazias, compostas apenas por espaços ou caracteres de pontuação retornam [] sem erro."""
        queries = ["", "   ", '""', '   ""   ', "*** () :NEAR: --- \"\""]
        for q in queries:
            res = self.store.fts_search(query=q, project_uuid=self.project_uuid)
            self.assertEqual(
                res, [], f"Consulta {q!r} deveria retornar lista vazia sem erro."
            )

    def test_fts5_injection_safety(self):
        """Nenhum payload de injeção de sintaxe FTS5 pode levantar sqlite3.OperationalError ou quebrar a busca."""
        self._insert_test_node(
            label="seguro.py",
            content="Arquivo com conteúdo regular para testar injeção de busca.",
        )
        injection_payloads = [
            'reembolso" OR 1=1 --',
            'NEAR(reembolso, estorno, 5)',
            'label:secret* OR content:password*',
            'reembolso ) OR ( estorno * ^ : -',
            'AND OR NOT NEAR',
            '"unclosed quote sem fechar',
            '"""',
            ':coluna:invalida',
            'SELECT * FROM nodes',
            'DROP TABLE nodes_fts;',
        ]
        for payload in injection_payloads:
            try:
                res = self.store.fts_search(
                    query=payload, project_uuid=self.project_uuid
                )
                self.assertIsInstance(
                    res,
                    list,
                    f"Resultado de {payload!r} deve ser lista sem levantar exceção.",
                )
            except sqlite3.OperationalError as e:
                self.fail(
                    f"Payload de injeção {payload!r} causou sqlite3.OperationalError: {e}"
                )

    def test_fts_query_builder_preserves_reserved_keywords_as_literals(self):
        """F4-027: _build_fts5_queries deve preservar AND, OR, NOT, NEAR como literais entre aspas."""
        # 1. 'not found' deve manter ambos os termos na consulta AND e OR
        and_q, or_q = GraphLogic._build_fts5_queries("not found")
        self.assertEqual(and_q, '"not" AND "found"', "Termo 'not' não pode ser removido da consulta")
        self.assertEqual(or_q, '"not" OR "found"', "Termo 'not' não pode ser removido do fallback OR")

        # 2. 'AND' sozinho deve buscar a palavra literal 'AND'
        and_q, or_q = GraphLogic._build_fts5_queries("AND")
        self.assertEqual(and_q, '"AND"', "Termo 'AND' sozinho deve ser preservado")
        self.assertIsNone(or_q)

        # 3. 'NEAR(a b)' deve preservar a palavra 'NEAR' como literal
        and_q, or_q = GraphLogic._build_fts5_queries("NEAR(a b)")
        self.assertEqual(and_q, '"NEAR" AND "a" AND "b"', "Operador NEAR deve ser preservado como token literal")
        self.assertEqual(or_q, '"NEAR" OR "a" OR "b"')

        # 4. 'a AND b OR c' deve preservar todas as palavras literais
        and_q, or_q = GraphLogic._build_fts5_queries("a AND b OR c")
        self.assertEqual(
            and_q,
            '"a" AND "AND" AND "b" AND "OR" AND "c"',
            "Palavras AND e OR em consultas complexas devem ser tratadas como literais",
        )
        self.assertEqual(
            or_q,
            '"a" OR "AND" OR "b" OR "OR" OR "c"',
        )

    def test_fts_search_with_keywords_matches_accurate_documents(self):
        """F4-027: Busca real com palavras-chave FTS5 distingue nós corretamente."""
        # Doc com 'not' e 'found'
        id_not_found = self._insert_test_node(
            label="error_handler.py",
            content="HTTP 404: resource not found in repository.",
        )
        # Doc apenas com 'found' (sem 'not')
        id_found_only = self._insert_test_node(
            label="cache_lookup.py",
            content="item successfully found in memory cache.",
        )
        # Doc sem 'NEAR', contendo 'a' e 'b'
        id_near = self._insert_test_node(
            label="geo_service.py",
            content="calculates distance between points a and b in space.",
        )
        # Doc com 'NEAR' literal
        id_near_code = self._insert_test_node(
            label="query_doc.py",
            content="documentation describes NEAR(a b) usage in search.",
        )

        # Busca por 'not found': deve casar id_not_found via AND
        # Em código com filtro de keywords, 'not' era removido e a busca virava 'found',
        # casando id_found_only indevidamente.
        res = self.store.fts_search(query="not found", project_uuid=self.project_uuid)
        res_ids = [r["id"] for r in res]
        self.assertIn(id_not_found, res_ids)
        self.assertNotIn(
            id_found_only,
            res_ids,
            "Documento que contém apenas 'found' (sem 'not') NÃO deve ser retornado na busca 'not found'",
        )

        # Busca por 'NEAR(a b)': deve casar id_near_code (que tem 'NEAR', 'a', 'b')
        # e NÃO id_near (que não tem 'NEAR')
        res_near = self.store.fts_search(query="NEAR(a b)", project_uuid=self.project_uuid)
        res_near_ids = [r["id"] for r in res_near]
        self.assertIn(id_near_code, res_near_ids)
        self.assertNotIn(
            id_near,
            res_near_ids,
            "Documento sem o termo 'NEAR' não deve casar consulta 'NEAR(a b)'",
        )



class TestFTSMigration(unittest.TestCase):
    """Testa a migração do esquema FTS antigo (3 colunas) para o novo (4 colunas + unicode61 remove_diacritics 2)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "legacy_migration.db")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _create_legacy_v380_db(self):
        """Cria um banco simulando a versão v3.8.0 antiga:
        nodes_fts com 3 colunas (label, tags, summary) sem content, e triggers antigos.
        """
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE projects (
                uuid TEXT PRIMARY KEY,
                folder_name TEXT NOT NULL,
                primary_wing TEXT NOT NULL DEFAULT 'geral',
                privacy_level TEXT NOT NULL DEFAULT 'PUBLIC',
                summary TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_uuid TEXT NOT NULL REFERENCES projects(uuid) ON DELETE CASCADE,
                label TEXT NOT NULL,
                summary TEXT,
                content TEXT,
                node_type TEXT NOT NULL DEFAULT 'FACT',
                type TEXT NOT NULL DEFAULT 'file',
                tags TEXT,
                file_hash TEXT,
                last_accessed TEXT,
                last_commit_at TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                valid_from_commit TEXT NULL,
                valid_to_commit TEXT NULL
            );
            CREATE VIRTUAL TABLE nodes_fts USING fts5(
                label, tags, summary, content='nodes', content_rowid='id'
            );
            CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
              INSERT INTO nodes_fts(rowid, label, tags, summary)
              VALUES (new.id, new.label, new.tags, new.summary);
            END;
            CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN
              INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
              VALUES('delete', old.id, old.label, old.tags, old.summary);
            END;
            CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN
              INSERT INTO nodes_fts(nodes_fts, rowid, label, tags, summary)
              VALUES('delete', old.id, old.label, old.tags, old.summary);
              INSERT INTO nodes_fts(rowid, label, tags, summary)
              VALUES (new.id, new.label, new.tags, new.summary);
            END;
            PRAGMA user_version = 308000;
        """)
        # Insere dados legados
        conn.execute(
            "INSERT INTO projects (uuid, folder_name) VALUES ('proj-leg', 'leg')"
        )
        conn.execute(
            """
            INSERT INTO nodes (project_uuid, label, summary, content, tags)
            VALUES ('proj-leg', 'legado.py', NULL, 'Conteúdo com violoncelo-ômega no legado', 'python')
        """
        )
        conn.commit()
        conn.close()

    def test_migration_upgrades_schema_preserves_nodes_and_creates_backup(self):
        """A migração deve:
        1. Criar backup antes de mexer (quando houver nós);
        2. Preservar 100% dos dados em nodes (hash SHA-256 idêntico antes e depois);
        3. Recriar nodes_fts com 4 colunas e tokenizer unicode61 remove_diacritics 2;
        4. Reindexar conteúdo antigo para que se torne imediatamente pesquisável;
        5. Ser idempotente (rodar 2x dá o mesmo resultado).
        """
        self._create_legacy_v380_db()

        # Calcula hash dos dados de nodes antes da migração
        conn_pre = sqlite3.connect(self.db_path)
        rows_pre = conn_pre.execute(
            "SELECT id, project_uuid, label, summary, content, tags FROM nodes ORDER BY id"
        ).fetchall()
        hash_pre = hashlib.sha256(repr(rows_pre).encode("utf-8")).hexdigest()
        conn_pre.close()

        # Aplica migração através do SqliteStore (que executa _boot_schema)
        store = SqliteStore(db_path=self.db_path)

        # 1. Verifica existência de backup (.bak)
        bak_files = [
            f for f in os.listdir(self.temp_dir.name) if f.endswith(".bak")
        ]
        self.assertTrue(
            len(bak_files) >= 1,
            f"Arquivo de backup não foi encontrado no diretório: {os.listdir(self.temp_dir.name)}",
        )

        # 2. Verifica hash de nodes pós-migração
        conn_post = sqlite3.connect(self.db_path)
        rows_post = conn_post.execute(
            "SELECT id, project_uuid, label, summary, content, tags FROM nodes ORDER BY id"
        ).fetchall()
        hash_post = hashlib.sha256(repr(rows_post).encode("utf-8")).hexdigest()
        self.assertEqual(
            hash_pre,
            hash_post,
            "Dados da tabela 'nodes' foram alterados durante a migração!",
        )

        # 3. Verifica se nodes_fts agora tem as 4 colunas (label, tags, summary, content)
        cur = conn_post.execute("SELECT sql FROM sqlite_master WHERE name='nodes_fts'")
        fts_sql = cur.fetchone()[0]
        self.assertIn("content", fts_sql)
        self.assertIn("remove_diacritics 2", fts_sql)
        conn_post.close()

        # 4. Verifica se o conteúdo antigo agora é encontrado pela busca FTS
        res = store.fts_search(
            query="violoncelo-omega", project_uuid="proj-leg"
        )
        self.assertTrue(
            len(res) > 0,
            "Conteúdo antigo com 'violoncelo-ômega' deveria ser encontrado após migração!",
        )
        store.close()

        # 5. Idempotência: reabrir SqliteStore novamente
        store2 = SqliteStore(db_path=self.db_path)
        res_repeat = store2.fts_search(
            query="violoncelo-omega", project_uuid="proj-leg"
        )
        self.assertEqual(len(res), len(res_repeat))
        store2.close()


if __name__ == "__main__":
    unittest.main()
