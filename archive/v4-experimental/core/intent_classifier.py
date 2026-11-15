"""
core/intent_classifier.py — SDD-SURVIVAL-22

Hybrid Intent Classifier (Syntactic + Semantic) for Knowledge Routing.

Implements a 3-tier triage pipeline to determine whether a developer query
targets the local private codebase (LOCAL_CODEBASE) or generic market/framework
knowledge (EXTERNAL_GENERAL):

  1. Fast Heuristic (Regex < 1ms): Project keywords, paths, and file extensions.
  2. Relational Entity Heuristic (SQLite): Checks if query terms match
     indexed file paths in the 'files' table.
  3. Cognitive Semantic Fallback (Local SLM): In ambiguous cases,
     invokes lightweight local model (qwen2.5-coder:1.5b) for intent classification.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class IntentClassifier:
    """JIT query intent classifier with a 3-tier triage pipeline."""

    def __init__(self, db_manager, slm_client=None, ollama_client=None):
        self.db = db_manager
        self.slm_client = slm_client or ollama_client
        self.ollama = self.slm_client  # Backward-compatibility alias

        # Tier 1: Compiled regex for known project-specific terms and path prefixes
        self.local_keywords = re.compile(
            r'\b(grafo|concierge|core|agent|sdd|db|tabela|sqlite|vector|mcp|janitor|database|comunidade|teste|testes|commit)\b|'
            r'(\.py|\.tsx?|\.jsx?)\b|'
            r'(/workspace|core/|interface/|grafo-dashboard-web)',
            re.IGNORECASE,
        )

    def classify_query(self, query: str) -> str:
        """
        Classifies query into either 'LOCAL_CODEBASE' or 'EXTERNAL_GENERAL'.

        Decision pipeline:
          1. Fast Heuristic (Syntactic < 1ms) via Regex
          2. Relational Entity Heuristic (SQLite indexed files)
          3. Cognitive Semantic Fallback via Local SLM (if available)

        Returns:
            'LOCAL_CODEBASE' if query refers to the private project.
            'EXTERNAL_GENERAL' if query targets market frameworks/libraries.
        """
        # 1. Fast Syntactic Heuristic (< 1ms)
        if self.local_keywords.search(query):
            logger.debug("IntentClassifier: '%s' -> LOCAL_CODEBASE (regex match)", query[:60])
            return "LOCAL_CODEBASE"

        # 2. Relational Entity Heuristic in SQLite
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
                        "IntentClassifier: '%s' -> LOCAL_CODEBASE (db entity match, %d hits)",
                        query[:60], count
                    )
                    return "LOCAL_CODEBASE"
            except Exception as e:
                logger.warning("IntentClassifier: Entity heuristic failure: %s", e)

        # 3. Cognitive Semantic Fallback (Only if SLM is active)
        if self.slm_client:
            try:
                prompt = (
                    "Classify the user query into exactly one of two strict categories:\n"
                    "1. 'LOCAL_CODEBASE': Questions specific to project source code, internal architecture, "
                    "files, infrastructure, or local commits.\n"
                    "2. 'EXTERNAL_GENERAL': General conceptual questions about languages or industry frameworks "
                    "(Next.js, React, Tailwind, Python) without direct relation to local private files.\n\n"
                    f"Query: \"{query}\"\n\n"
                    "Answer strictly with ONLY one of the two category names."
                )
                response = self.slm_client.generate(model="qwen2.5-coder:1.5b", prompt=prompt)
                clean_res = response.strip().upper()
                if "LOCAL_CODEBASE" in clean_res:
                    logger.debug("IntentClassifier: '%s' -> LOCAL_CODEBASE (SLM fallback)", query[:60])
                    return "LOCAL_CODEBASE"
            except Exception as e:
                logger.warning("IntentClassifier: Local SLM fallback failure: %s", e)

        logger.debug("IntentClassifier: '%s' -> EXTERNAL_GENERAL (default)", query[:60])
        return "EXTERNAL_GENERAL"
