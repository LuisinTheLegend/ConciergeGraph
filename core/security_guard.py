"""
core/security_guard.py — SDD-SURVIVAL-24

Guarda de Fronteira e Classificador de Perigo (Vanguard Bounds Guard).

Implementa duas barreiras de segurança complementares:
  1. is_safe_path: Barreira física intransponível que impede qualquer leitura
     ou escrita de arquivos fora do diretório raiz normalizado do monorepo.
     Previne Path Traversal (../../etc/passwd) mesmo sob alucinação do agente.
  2. classify_command: Classificador de comandos de terminal em três níveis
     de risco (SAFE, WARNING, CRITICAL), alimentando o GatingInterceptor.

Segurança:
  - Normalização via os.path.realpath() resolve symlinks e traversals.
  - Blacklist regex para comandos intrinsecamente destrutivos (rm -rf /, mkfs, dd).
  - Zero-trust: caminhos vazios ou inválidos são considerados seguros (noop).
"""

import logging
import os
import re
from typing import List

logger = logging.getLogger(__name__)


class SecurityGuard:
    """
    Guarda de fronteira de segurança com validação física de caminhos
    e classificação de comandos de terminal.

    Parâmetros:
      project_root — Diretório raiz do monorepo. Normalizado via realpath()
                     para resolver symlinks e caminhos relativos.
    """

    def __init__(self, project_root: str):
        # Normaliza o caminho do monorepo para checagem absoluta de limites
        self.project_root = os.path.realpath(project_root)

        # Padrões conhecidos de comandos intrinsecamente destrutivos
        self.blacklisted_patterns = re.compile(
            r"(\brm\s+-rf\s+/|\b(mkfs|dd\s+if|shutdown|reboot|systemctl|userdel|iptables)\b)",
            re.IGNORECASE,
        )

        # Termos que indicam comandos de infraestrutura/empacotamento (WARNING)
        self.warning_terms: List[str] = [
            "npm install",
            "pip install",
            "pytest",
            "build",
            "docker",
        ]

    def is_safe_path(self, target_path: str) -> bool:
        """
        Garante que nenhum arquivo seja lido ou editado fora das dependências
        físicas do monorepo (Prevenção absoluta de Path Traversal).

        Normaliza o caminho de destino via os.path.realpath() e compara com
        o diretório raiz do projeto. Caminhos vazios são tratados como noop
        seguro (sem arquivo alvo = sem risco).

        Retorna:
          True  — se o caminho está dentro do monorepo ou é vazio/nulo.
          False — se o caminho normalizado está fora do monorepo.
        """
        if not target_path:
            return True
        try:
            absolute_target = os.path.realpath(target_path)
            # Verifica se o caminho físico de destino inicia com o caminho do monorepo
            # Adiciona os.sep para evitar falsos positivos parciais
            # (ex: /home/user/project-evil vs /home/user/project)
            return absolute_target.startswith(
                self.project_root + os.sep
            ) or absolute_target == self.project_root
        except Exception:
            return False

    def classify_command(self, command: str) -> str:
        """
        Classifica comandos de terminal em três níveis de risco:

          CRITICAL — Comandos banidos sumariamente (rm -rf /, mkfs, dd if, etc.).
                     Bloqueados em TODOS os modos de gating, incluindo auto-approve.
          WARNING  — Comandos de infraestrutura (npm install, docker, pytest, build).
                     Requerem aprovação humana no modo 'ask'.
          SAFE     — Todos os demais comandos (ls, cat, echo, git status, etc.).
                     Liberados automaticamente.

        Retorna: "CRITICAL", "WARNING" ou "SAFE".
        """
        if self.blacklisted_patterns.search(command):
            return "CRITICAL"

        # Comandos de empacotamento, infraestrutura ou compilação local
        if any(term in command for term in self.warning_terms):
            return "WARNING"

        return "SAFE"
