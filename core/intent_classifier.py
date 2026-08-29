"""
core/intent_classifier.py — SDD-SURVIVAL-22

Classificador de Intenção Híbrido (Sintático + Semântico) para Roteamento de Conhecimento.

Implementa uma pipeline de triagem em 3 camadas para discernir se a consulta
do desenvolvedor se refere ao codebase privado local (LOCAL_CODEBASE) ou a
conhecimento genérico de mercado/frameworks (EXTERNAL_GENERAL):

  1. Heurística Rápida (Regex < 1ms): Palavras-chave do projeto e extensões de arquivos.
  2. Heurística de Entidades Relacionais (SQLite): Verifica se termos da query
     correspondem a caminhos de arquivos indexados na tabela 'files'.
  3. Fallback Cognitivo Semântico (Ollama SLM): Apenas em caso de ambiguidade,
     recorre a um modelo local leve (qwen2.5-coder:1.5b) para classificação.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classificador JIT de intenção com pipeline de triagem em 3 camadas."""

    def __init__(self, db_manager, ollama_client=None):
        self.db = db_manager
        self.ollama = ollama_client

        # Camada 1: Regex compilado para termos locais conhecidos do projeto
        self.local_keywords = re.compile(
            r'\b(grafo|concierge|hermes|nexus|sdd|db|tabela|sqlite|qdrant|mcp|janitor|database|comunidade|teste|testes|commit)\b|'
            r'(\.py|\.tsx?|\.jsx?)\b|'
            r'(/workspace|core/|interface/|grafo-dashboard-web)',
            re.IGNORECASE
        )

    def classify_query(self, query: str) -> str:
        """
        Classifica a consulta entre 'LOCAL_CODEBASE' ou 'EXTERNAL_GENERAL'.

        Pipeline de decisão:
          1. Heurística Rápida (Sintática < 1ms) via Regex
          2. Heurística de Entidades Existentes no Banco Relacional (SQLite)
          3. Fallback Cognitivo Semântico via Ollama SLM (apenas se ativo)

        Returns:
            'LOCAL_CODEBASE' se a consulta se refere ao projeto privado.
            'EXTERNAL_GENERAL' se a consulta é sobre frameworks/bibliotecas de mercado.
        """
        # 1. Heurística Rápida (Sintática < 1ms)
        if self.local_keywords.search(query):
            logger.debug("IntentClassifier: '%s' → LOCAL_CODEBASE (regex match)", query[:60])
            return "LOCAL_CODEBASE"

        # 2. Heurística de Entidades Existentes no Banco Relacional
        words = [w for w in re.findall(r'\b\w{4,}\b', query)]
        if words:
            like_conditions = " OR ".join(["path LIKE ?" for _ in words])
            query_sql = f"SELECT COUNT(*) FROM files WHERE {like_conditions};"
            params = tuple(f"%{w}%" for w in words)

            try:
                result = self.db.read_query(query_sql, params)
                count = result[0][0] if result else 0
                if count > 0:
                    logger.debug(
                        "IntentClassifier: '%s' → LOCAL_CODEBASE (db entity match, %d hits)",
                        query[:60], count
                    )
                    return "LOCAL_CODEBASE"
            except Exception as e:
                logger.warning("IntentClassifier: Falha na heurística de entidades: %s", e)

        # 3. Fallback Cognitivo Semântico (Apenas se Ollama estiver ativo)
        if self.ollama:
            try:
                prompt = (
                    "Classifique a pergunta do usuário entre duas categorias rígidas:\n"
                    "1. 'LOCAL_CODEBASE': Perguntas específicas sobre o código, arquitetura interna, "
                    "arquivos, infraestrutura ou commits locais do projeto.\n"
                    "2. 'EXTERNAL_GENERAL': Perguntas conceituais sobre linguagens, frameworks de mercado "
                    "(Next.js, React, Tailwind, Python) sem relação direta com arquivos privados do projeto.\n\n"
                    f"Pergunta: \"{query}\"\n\n"
                    "Responda estritamente APENAS com uma das duas palavras."
                )
                response = self.ollama.generate(model="qwen2.5-coder:1.5b", prompt=prompt)
                clean_res = response.strip().upper()
                if "LOCAL_CODEBASE" in clean_res:
                    logger.debug("IntentClassifier: '%s' → LOCAL_CODEBASE (SLM fallback)", query[:60])
                    return "LOCAL_CODEBASE"
            except Exception as e:
                logger.warning("IntentClassifier: Falha no fallback Ollama SLM: %s", e)

        logger.debug("IntentClassifier: '%s' → EXTERNAL_GENERAL (default)", query[:60])
        return "EXTERNAL_GENERAL"
