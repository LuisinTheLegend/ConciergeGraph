"""
tests/test_delta_sync_drift.py — SDD-SURVIVAL-11

Suíte TDD para validar o Semantic Drift Guard via Hashing de Corpo AST.

Cenários cobertos:
  1. Alterações de comentários e espaços NÃO mudam o hash lógico (LBH).
  2. Alterações de docstrings NÃO mudam o hash lógico (LBH).
  3. Alterações de lógica interna (mesmo sem mudar assinatura) SIM mudam o LBH.
"""

import unittest
import hashlib
import ast
from core.delta_sync import DeltaManager, DocstringStripper


class TestDeltaSyncDrift(unittest.TestCase):
    def setUp(self):
        self.stripper = DocstringStripper()

    def get_logical_ast_dump(self, code_str):
        """Limpa docstrings e gera o dump estrutural estável para hashing"""
        tree = ast.parse(code_str)
        cleaned_tree = self.stripper.visit(tree)
        # O ast.dump com annotate_fields=False gera uma string estrutural pura e estável
        return ast.dump(cleaned_tree, annotate_fields=False)

    def test_ignore_formatting_and_comments(self):
        """Garante que alterações em comentários e espaços em branco NÃO mudam o hash lógico"""
        code_original = """
def calcular_taxa(valor):
    # Calcula taxa base de forma simples
    taxa = valor * 0.05
    return taxa
"""
        code_formatado_com_comentarios_novos = """
def calcular_taxa(valor):
    
    # NOVA DOCUMENTAÇÃO DE COMENTÁRIO INTERNO
    # Espaços extras adicionados propositalmente
    
    taxa = valor * 0.05
    
    return taxa
"""
        dump_orig = self.get_logical_ast_dump(code_original)
        dump_mod = self.get_logical_ast_dump(code_formatado_com_comentarios_novos)

        # O dump estrutural estruturado deve ser idêntico!
        self.assertEqual(dump_orig, dump_mod)

    def test_ignore_docstring_mutations(self):
        """Garante que modificações apenas nas docstrings das funções são ignoradas pelo LBH"""
        code_original = """
def processar_dados(dados):
    \"\"\"Docstring original antiga.\"\"\"
    return len(dados)
"""
        code_com_docstring_alterada = """
def processar_dados(dados):
    \"\"\"Docstring completamente reformulada e muito maior para testes.\"\"\"
    return len(dados)
"""
        dump_orig = self.get_logical_ast_dump(code_original)
        dump_mod = self.get_logical_ast_dump(code_com_docstring_alterada)

        self.assertEqual(dump_orig, dump_mod)

    def test_detect_internal_logic_drift(self):
        """Garante que se a lógica do corpo mudar (sem mudar a assinatura), o hash lógico muda"""
        code_original = """
def validar_usuario(user):
    \"\"\"Verifica se usuário é admin\"\"\"
    return user.role == "admin"
"""
        # Assinatura pública idêntica, mas lógica interna alterada (mudou operador de == para !=)
        code_com_deriva_logica = """
def validar_usuario(user):
    \"\"\"Verifica se usuário é admin\"\"\"
    return user.role != "admin"
"""
        dump_orig = self.get_logical_ast_dump(code_original)
        dump_mod = self.get_logical_ast_dump(code_com_deriva_logica)

        self.assertNotEqual(dump_orig, dump_mod)
