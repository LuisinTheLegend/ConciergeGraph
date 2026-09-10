"""
agent/ — SDD-SURVIVAL-26

Agent execution package for the cognitive loop.

Modules:
    - run_agent.py: CognitiveAgentRunner — HSM-coupled agent execution loop
    - agent_prompts.py: Dynamic system prompt builder with HSM state injection
"""

from agent.run_agent import CognitiveAgentRunner, HermesAgentRunner

__all__ = ["CognitiveAgentRunner", "HermesAgentRunner"]
