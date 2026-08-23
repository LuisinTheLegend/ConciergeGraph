"""
core/background_janitor.py — SDD-SURVIVAL-06 / SDD-SURVIVAL-12

Varredor de Resumos em Segundo Plano (SLM Offloading) e
Auto-Poda Inteligente de Checkpoints (Smart LRU per Session).

Responsabilidades:
  1. Delega a geração de resumos das comunidades DIRTY para modelos locais
     gratuitos (SLM via Ollama) durante períodos de ociosidade, blindando
     o usuário contra custos de tokens na nuvem. (SDD-06)
  2. Limpa checkpoints intermediários obsoletos de sessões de agentes,
     preservando o ponto zero ("init") e os N mais recentes, evitando
     o inchaço indefinido do banco state.db. (SDD-12)

Fluxo de Resumo (SDD-06):
  1. Localiza comunidades com is_dirty = 1
  2. Para cada: agrupa conteúdo dos arquivos associados
  3. Dispara callback da SLM local gratuita
  4. Persiste resumo, limpa flags, retorna log de auditoria

Fluxo de Poda (SDD-12):
  1. Identifica todos os checkpoints de uma sessão ordenados cronologicamente
  2. Protege o primeiro checkpoint (ponto zero imutável)
  3. Mantém os últimos N checkpoints recentes (keep_limit)
  4. Deleta os intermediários obsoletos via SerializedWriteQueue
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class BackgroundJanitor:
    """
    Varredor de ociosidade que resume comunidades sujas utilizando
    exclusivamente modelos locais gratuitos (SLM), garantindo faturas
    de API zeradas. Também realiza auto-poda inteligente de checkpoints
    para evitar inchaço do banco. (SDD-06 / SDD-12)
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

    # ── Resumo de Comunidades (SDD-06) ────────────────────────────

    def run_idle_summarization(
        self, local_slm_callback: Callable[[str], str]
    ) -> Dict[str, str]:
        """
        Processa todas as comunidades DIRTY em segundo plano.

        Para cada comunidade suja:
          - Agrupa o conteúdo dos arquivos associados
          - Dispara o callback gratuito da SLM local
          - Persiste o novo resumo no banco
          - Reseta flags is_dirty para 0

        Retorna um log de auditoria: {community_id: summary_gerado}
        """
        audit_log: Dict[str, str] = {}

        # Localiza todas as comunidades sujas
        dirty_communities = self.db_manager.read_query(
            "SELECT id FROM communities WHERE is_dirty = 1;"
        )

        for (community_id,) in dirty_communities:
            summary = self._summarize_community(community_id, local_slm_callback)
            audit_log[community_id] = summary

        return audit_log

    def _summarize_community(
        self, community_id: str, local_slm_callback: Callable[[str], str]
    ) -> str:
        """
        Agrupa conteúdo dos arquivos da comunidade, gera resumo via SLM
        local e persiste o resultado limpando as flags de sujeira.
        """
        # Agrupa conteúdo de todos os arquivos da comunidade
        files = self.db_manager.read_query(
            "SELECT content FROM files WHERE community_id = ?;",
            (community_id,),
        )
        payload = "\n".join(row[0] for row in files)

        # Dispara a SLM local gratuita
        new_summary = local_slm_callback(payload)

        # Persiste resumo e reconcilia flags
        self.db_manager.write_query(
            "UPDATE communities SET summary_text = ?, is_dirty = 0 WHERE id = ?;",
            (new_summary, community_id),
        )
        self.db_manager.write_query(
            "UPDATE files SET is_dirty = 0 WHERE community_id = ?;",
            (community_id,),
        )

        return new_summary

    # ── Auto-Poda de Checkpoints (SDD-12) ─────────────────────────

    def prune_session_checkpoints(
        self,
        session_id: Optional[str] = None,
        keep_limit: int = 10,
    ) -> int:
        """
        Executa a auto-poda inteligente de checkpoints por sessão.

        Algoritmo Smart LRU per Session:
          1. Identifica todos os checkpoints da sessão ordenados por created_at
          2. Protege o primeiro checkpoint (ponto zero / "init") — imutável
          3. Dos restantes, preserva os últimos `keep_limit` mais recentes
          4. Deleta fisicamente os intermediários obsoletos

        Se session_id for None, processa todas as sessões existentes.

        Retorna o total de checkpoints eliminados.
        """
        total_pruned = 0

        if session_id is not None:
            sessions = [(session_id,)]
        else:
            sessions = self.db_manager.read_query(
                "SELECT DISTINCT session_id FROM agent_checkpoints;"
            )

        for (sid,) in sessions:
            pruned = self._prune_single_session(sid, keep_limit)
            total_pruned += pruned

        return total_pruned

    def _prune_single_session(self, session_id: str, keep_limit: int) -> int:
        """
        Executa a poda de uma sessão individual.

        Identifica os checkpoint_ids que devem ser preservados (ponto zero +
        os N mais recentes) e deleta todos os outros intermediários.
        """
        # Seleciona todos os checkpoints da sessão em ordem cronológica
        all_checkpoints = self.db_manager.read_query(
            "SELECT checkpoint_id FROM agent_checkpoints "
            "WHERE session_id = ? "
            "ORDER BY created_at ASC;",
            (session_id,),
        )

        if not all_checkpoints:
            return 0

        all_ids = [row[0] for row in all_checkpoints]

        # Protege o primeiro checkpoint (ponto zero imutável)
        init_checkpoint = all_ids[0]
        remaining = all_ids[1:]

        # Dos restantes, preserva os últimos keep_limit
        if len(remaining) <= keep_limit:
            # Nada a podar — todos cabem no limite
            return 0

        # IDs a preservar: init + últimos keep_limit
        recent_ids = remaining[-keep_limit:]
        preserve_set = {init_checkpoint} | set(recent_ids)

        # IDs a eliminar: todos que não estão no conjunto de preservação
        ids_to_delete = [cid for cid in all_ids if cid not in preserve_set]

        if not ids_to_delete:
            return 0

        # Deleta em lote via SerializedWriteQueue
        placeholders = ", ".join("?" for _ in ids_to_delete)
        self.db_manager.write_query(
            f"DELETE FROM agent_checkpoints "
            f"WHERE session_id = ? AND checkpoint_id IN ({placeholders});",
            (session_id, *ids_to_delete),
        )

        logger.info(
            "SDD-12: Poda de sessão '%s' concluída — %d checkpoints eliminados, "
            "%d preservados (1 init + %d recentes).",
            session_id,
            len(ids_to_delete),
            len(preserve_set),
            len(recent_ids),
        )

        return len(ids_to_delete)

