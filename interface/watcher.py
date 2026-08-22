"""
interface/watcher.py — SDD-SURVIVAL-01

Monitor de Arquivos Reativo com Filtro Precoce de Ignorados (Early Exit).

Captura eventos de gravação no sistema de arquivos local e aplica
regras de descarte precoce baseadas nos padrões do .conciergeignore,
utilizando pathspec (Git Wildmatch) para correspondência ultra-rápida.

Isso elimina:
  - Riscos de segurança (vazamento de credenciais via .env)
  - Picos desnecessários de CPU/disco (node_modules, dist/, *.log)
"""

import os
import pathspec
from watchdog.events import FileSystemEventHandler


class ConciergeFileSystemHandler(FileSystemEventHandler):
    """
    Captura eventos de gravação no sistema de arquivos local e aplica
    regras de descarte precoce (Early Exit) baseadas no arquivo de ignore.
    """

    def __init__(
        self,
        project_path: str,
        ignore_spec: pathspec.PathSpec,
        on_valid_change_callback,
    ):
        super().__init__()
        self.project_path = os.path.abspath(project_path)
        self.ignore_spec = ignore_spec
        self.on_valid_change_callback = on_valid_change_callback

    def on_modified(self, event):
        if event.is_directory:
            return

        # Converte o caminho absoluto do arquivo modificado para caminho relativo
        abs_path = os.path.abspath(event.src_path)
        rel_path = os.path.relpath(abs_path, self.project_path)

        # 🛡️ Portão de Segurança / Descarte Precoce (Early Exit)
        if self.ignore_spec.match_file(rel_path):
            # Aborta imediatamente sem gastar processamento de AST ou I/O
            return

        # Passou pelo portão: executa o callback de processamento delta
        self.on_valid_change_callback(abs_path)
