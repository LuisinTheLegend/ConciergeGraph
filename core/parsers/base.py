"""
core/parsers/base.py — SDD-SURVIVAL-19

Interface abstrata comum para todos os parsers de linguagem do Grafo Concierge.

Define o contrato que cada parser especializado (Python, TS/JS, etc.)
deve implementar para integrar-se com o DeltaManager e o Background Janitor.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseASTParser(ABC):
    """
    Interface base para parsers de linguagem.

    Cada implementação concreta deve ser capaz de:
      1. Extrair classes, funções e imports de um arquivo-fonte.
      2. Gerar uma assinatura estrutural determinística (SSH) que ignore
         mudanças cosméticas e de lógica interna.
      3. Resolver caminhos de imports relativos e com alias para o
         caminho físico real dentro do monorepo.
    """

    @abstractmethod
    def parse(self, file_path: str, code_content: str) -> Dict[str, Any]:
        """
        Analisa o conteúdo de um arquivo-fonte e retorna um dicionário com:
          - "classes": List[str]              → nomes das classes encontradas
          - "functions": List[str]            → nomes das funções encontradas
          - "imports": List[str]              → caminhos resolvidos dos imports
          - "structural_signature": str       → string determinística de arquitetura

        Args:
            file_path: caminho relativo do arquivo dentro do projeto.
            code_content: conteúdo textual completo do arquivo.

        Returns:
            Dict com as chaves acima.
        """
        ...
