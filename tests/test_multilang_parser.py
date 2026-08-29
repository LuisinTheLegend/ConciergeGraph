"""
tests/test_multilang_parser.py — SDD-SURVIVAL-19

Suíte de testes TDD para o Parser Multilinguagem (JS/TS/JSX/TSX).

Valida:
  1. Roteamento correto da ParserFactory por extensão de arquivo.
  2. Extração de imports (ES6 + CommonJS), classes e arrow functions
     de arquivos TSX complexos com resolução de aliases do Next.js.
  3. Consistência e resiliência da Assinatura Estrutural Hash (SSH)
     frente a mudanças de lógica interna e formatação.
  4. Extração precisa de entidades de arquivos Python via PythonASTParser.
  5. Filtragem correta de pacotes npm externos (react, next, etc.).
"""

import unittest
import os

from core.parsers.ts_js_parser import TSJSASTParser
from core.parsers.python_parser import PythonASTParser
from core.parser_factory import ParserFactory


class TestMultiLangParser(unittest.TestCase):

    def setUp(self):
        self.parser = TSJSASTParser(project_root=".")
        # Reseta o cache singleton da fábrica entre testes
        ParserFactory.reset()

    # ── Teste 1: Roteamento da Fábrica ───────────────────────────────

    def test_factory_resolves_correct_parser(self):
        """Testa se a fábrica retorna o parser adequado pela extensão do arquivo."""
        py_parser = ParserFactory.get_parser_for_file("core/watcher.py")
        ts_parser = ParserFactory.get_parser_for_file("grafo-dashboard-web/app/page.tsx")
        js_parser = ParserFactory.get_parser_for_file("scripts/build.js")
        jsx_parser = ParserFactory.get_parser_for_file("components/App.jsx")
        invalid_parser = ParserFactory.get_parser_for_file("README.md")
        json_parser = ParserFactory.get_parser_for_file("package.json")

        self.assertIsNotNone(py_parser)
        self.assertIsInstance(py_parser, PythonASTParser)

        self.assertIsNotNone(ts_parser)
        self.assertIsInstance(ts_parser, TSJSASTParser)

        self.assertIsNotNone(js_parser)
        self.assertIsInstance(js_parser, TSJSASTParser)

        self.assertIsNotNone(jsx_parser)
        self.assertIsInstance(jsx_parser, TSJSASTParser)

        self.assertIsNone(invalid_parser)
        self.assertIsNone(json_parser)

    # ── Teste 2: Extração de Entidades TS/JSX ────────────────────────

    def test_typescript_lexical_parsing_and_imports(self):
        """Valida a extração de imports, classes e arrow functions de um arquivo TSX complexo."""
        tsx_code = """
        import React, { useState } from 'react';
        import { AgentTimelinePanel } from '@/components/AgentTimelinePanel';
        import { calculate_thompson_score } from '../utils/math';
        const Sidebar = require('./Sidebar');

        export class DashboardContainer extends React.Component {
            render() {
                return <div />;
            }
        }

        const handleUpdate = (id: string) => {
            console.log(id);
        };

        function calculateMetrics(data: any) {
            return data;
        }
        """

        # Simula arquivo salvo na pasta mock do dashboard
        file_path = "grafo-dashboard-web/app/Dashboard.tsx"
        parsed_data = self.parser.parse(file_path, tsx_code)

        # Validação de classes extraídas
        self.assertIn("DashboardContainer", parsed_data["classes"])

        # Validação de funções extraídas (arrow + nomeada)
        self.assertIn("handleUpdate", parsed_data["functions"])
        self.assertIn("calculateMetrics", parsed_data["functions"])

        # Validação de imports e resolução de aliases do Next.js
        # Imports de npm (externos como 'react') devem ser OMITIDOS.
        npm_imports = [i for i in parsed_data["imports"] if "react" in i.lower()]
        self.assertEqual(len(npm_imports), 0, "Imports npm externos devem ser filtrados")

        # Imports de alias '@/components/...' devem apontar para a pasta física
        self.assertIn(
            "grafo-dashboard-web/components/AgentTimelinePanel",
            parsed_data["imports"],
        )

        # Imports relativos '../utils/math' devem ser resolvidos de forma correta
        self.assertIn("grafo-dashboard-web/utils/math", parsed_data["imports"])

        # Import via require('./Sidebar') deve ser resolvido relativamente
        self.assertIn("grafo-dashboard-web/app/Sidebar", parsed_data["imports"])

    # ── Teste 3: Consistência do SSH ─────────────────────────────────

    def test_structural_hash_consistency_and_resilience(self):
        """Garante que modificações lógicas internas não alterem o SSH de arquivos de JS/TS."""
        code_v1 = """
        import { fetchStatus } from '@/api/concierge';
        export function run() {
            console.log("Olá!");
            return true;
        }
        """

        # V2 tem alterações de lógica interna e formatação, mas mantém a assinatura idêntica
        code_v2 = """
        import { fetchStatus } from '@/api/concierge';
        export function run() {
            // Comentário adicionado e código interno reescrito
            const result = fetchStatus();
            if (result) {
                console.log("Sucesso!");
            }
            return result;
        }
        """

        parsed_v1 = self.parser.parse("src/run.ts", code_v1)
        parsed_v2 = self.parser.parse("src/run.ts", code_v2)

        # As assinaturas devem ser idênticas, impedindo o imposto de tokens
        # do Background Janitor
        self.assertEqual(
            parsed_v1["structural_signature"],
            parsed_v2["structural_signature"],
        )

    # ── Teste 4: Parser Python via Fábrica ───────────────────────────

    def test_python_parser_extraction_via_factory(self):
        """Valida que o PythonASTParser extrai classes, funções e imports corretamente."""
        py_code = """
import os
from typing import Dict, Any

class GraphRAGEngine:
    def __init__(self, db_manager):
        self.db = db_manager

    def retrieve_multihop_context(self, entry_node: str, max_depth: int = 3):
        pass

async def background_task():
    await do_work()
"""

        parser = ParserFactory.get_parser_for_file("core/graph_rag.py")
        self.assertIsNotNone(parser)

        result = parser.parse("core/graph_rag.py", py_code)

        self.assertIn("GraphRAGEngine", result["classes"])
        self.assertIn("__init__", result["functions"])
        self.assertIn("retrieve_multihop_context", result["functions"])
        self.assertIn("background_task", result["functions"])
        self.assertIn("os", result["imports"])
        self.assertIn("typing", result["imports"])
        self.assertNotEqual(result["structural_signature"], "")

    # ── Teste 5: Filtragem de Pacotes npm Externos ───────────────────

    def test_should_filter_external_npm_packages(self):
        """Pacotes npm como 'react', 'next/router', 'recharts' devem ser descartados."""
        code = """
        import React from 'react';
        import { useRouter } from 'next/router';
        import { BarChart } from 'recharts';
        import axios from 'axios';
        import { Panel } from '@/components/Panel';
        import { helper } from './utils/helper';
        """

        parsed = self.parser.parse("grafo-dashboard-web/pages/index.tsx", code)

        # Apenas imports internos devem aparecer
        self.assertEqual(len(parsed["imports"]), 2)
        self.assertIn("grafo-dashboard-web/components/Panel", parsed["imports"])
        self.assertIn("grafo-dashboard-web/pages/utils/helper", parsed["imports"])

    # ── Teste 6: Suporte a Extensões Múltiplas ───────────────────────

    def test_factory_supports_all_js_ts_extensions(self):
        """Garante que todas as extensões JS/TS são roteadas para o TSJSASTParser."""
        extensions = [".ts", ".tsx", ".js", ".jsx"]
        for ext in extensions:
            parser = ParserFactory.get_parser_for_file(f"app/component{ext}")
            self.assertIsNotNone(parser, f"Parser não encontrado para extensão {ext}")
            self.assertIsInstance(parser, TSJSASTParser)

    # ── Teste 7: Detecção de Hooks React como Builtins ───────────────

    def test_should_not_extract_react_builtins_as_functions(self):
        """Hooks e builtins do React não devem ser contabilizados como funções do projeto."""
        code = """
        const MyComponent = () => {
            const [state, setState] = useState(false);
            useEffect(() => {}, []);
            return <div />;
        };
        """

        parsed = self.parser.parse("app/MyComponent.tsx", code)

        self.assertIn("MyComponent", parsed["functions"])
        self.assertNotIn("useState", parsed["functions"])
        self.assertNotIn("useEffect", parsed["functions"])

    # ── Teste 8: SSH Vazio para Arquivos sem Estrutura ────────────────

    def test_empty_file_produces_consistent_empty_ssh(self):
        """Arquivos JS/TS vazios ou só com comentários devem produzir SSH determinístico."""
        empty_code = ""
        comment_only = "// Este arquivo está vazio\n/* Nada aqui */"

        parsed_empty = self.parser.parse("app/empty.ts", empty_code)
        parsed_comment = self.parser.parse("app/comment.ts", comment_only)

        # Ambos devem produzir assinaturas determinísticas (vazias mas consistentes)
        self.assertEqual(parsed_empty["structural_signature"], parsed_comment["structural_signature"])
        self.assertEqual(parsed_empty["classes"], [])
        self.assertEqual(parsed_empty["functions"], [])
        self.assertEqual(parsed_empty["imports"], [])
