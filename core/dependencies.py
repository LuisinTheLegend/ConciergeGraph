"""
core/dependencies.py — SDD-SURVIVAL-03

Contêiner de Injeção de Dependências Estrita (AgentDependencies).

Centraliza todos os recursos sensíveis e variáveis de ambiente do agente
em um contêiner imutável fortemente tipado (frozen dataclass), eliminando
acoplamento de conexões globais soltas e viabilizando mocks perfeitos
para testes offline.

Recursos encapsulados:
  - db_manager:     Instância de ConciergeDatabaseManager (SDD-SURVIVAL-02)
  - workspace_path: Caminho físico absoluto do projeto do usuário
  - rate_governor:  Controlador opcional de taxa de requisições LLM
  - security_guard: Validador opcional de permissões e sandboxing
"""

from dataclasses import dataclass
from typing import Any, Optional
import os


@dataclass(frozen=True)
class AgentDependencies:
    """
    Contêiner imutável que centraliza os recursos de infraestrutura local,
    garantindo isolamento total de conexões e facilitando injeção em testes.
    """

    db_manager: Any  # Instância de ConciergeDatabaseManager
    workspace_path: str
    rate_governor: Optional[Any] = None
    security_guard: Optional[Any] = None

    def __post_init__(self):
        # Validação estrita de segurança no bootstrap de recursos
        if not os.path.exists(self.workspace_path):
            raise ValueError(
                f"Caminho do workspace inválido ou inexistente: {self.workspace_path}"
            )
