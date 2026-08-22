"""
core/background_janitor.py — SDD-SURVIVAL-06

Varredor de Resumos em Segundo Plano (SLM Offloading).

Delega a geração de resumos das comunidades DIRTY para modelos locais
gratuitos (SLM via Ollama) durante períodos de ociosidade, blindando
o usuário contra custos de tokens na nuvem.

Fluxo:
  1. Localiza comunidades com is_dirty = 1
  2. Para cada: agrupa conteúdo dos arquivos associados
  3. Dispara callback da SLM local gratuita
  4. Persiste resumo, limpa flags, retorna log de auditoria
"""

from typing import Any, Callable, Dict


class BackgroundJanitor:
    """
    Varredor de ociosidade que resume comunidades sujas utilizando
    exclusivamente modelos locais gratuitos (SLM), garantindo faturas
    de API zeradas.
    """

    def __init__(self, db_manager: Any):
        self.db_manager = db_manager

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
