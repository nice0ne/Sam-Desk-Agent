"""Brain module for Sam-Desk-Agent: prompts, registry, and agent brain."""

from src.brain.prompts import SAM_SYSTEM_PROMPT
from src.brain.registry import ToolRegistry
from src.brain.agent import AgentBrain
from src.brain.llm_client import (
    LLMClient,
    LLMProviderConfig,
    PROVIDER_PRESETS,
    get_default_provider_config,
)

__all__ = [
    "ToolRegistry",
    "AgentBrain",
    "SAM_SYSTEM_PROMPT",
    "LLMClient",
    "LLMProviderConfig",
    "PROVIDER_PRESETS",
    "get_default_provider_config",
]

