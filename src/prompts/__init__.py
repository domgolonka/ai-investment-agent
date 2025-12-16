"""
Multi-Agent Trading System - Modular Prompts Package.

This package provides a centralized registry for all agent prompts with version tracking.
The prompts are organized into modules by function:

- analyst_prompts: Market, News, Sentiment, Fundamentals analyst prompts
- debate_prompts: Bull, Bear, Research Manager prompts
- risk_prompts: Safe, Neutral, Risky analyst prompts
- decision_prompts: Trader, Portfolio Manager, Consultant prompts

Backward Compatibility:
    All existing imports from src.prompts continue to work:
    - from src.prompts import PromptRegistry, AgentPrompt, get_registry, get_prompt, etc.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from pathlib import Path
import json
import os
import structlog

# Import prompt definitions from submodules
from .analyst_prompts import get_analyst_prompts
from .debate_prompts import get_debate_prompts
from .risk_prompts import get_risk_prompts
from .decision_prompts import get_decision_prompts

logger = structlog.get_logger(__name__)


@dataclass
class AgentPrompt:
    """
    Structured prompt with metadata for version tracking.

    Attributes:
        agent_key: Unique identifier for the agent.
        agent_name: Human-readable name for the agent.
        version: Version string for tracking prompt changes.
        system_message: The actual prompt content.
        category: Category grouping (e.g., 'technical', 'fundamental', 'risk').
        requires_tools: Whether the agent needs tool access.
        metadata: Additional metadata (last_updated, changes, etc.).
    """
    agent_key: str
    agent_name: str
    version: str
    system_message: str
    category: str = "general"
    requires_tools: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PromptRegistry:
    """
    Central registry for all agent prompts with version tracking.

    The registry loads prompts from the modular prompt files and supports:
    - Loading default prompts from submodules
    - Loading custom prompts from JSON files
    - Environment variable overrides
    - Exporting prompts to JSON

    Usage:
        registry = PromptRegistry()
        prompt = registry.get("market_analyst")
        all_prompts = registry.get_all()
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize the prompt registry.

        Args:
            prompts_dir: Optional directory for custom JSON prompt files.
                         Defaults to PROMPTS_DIR env var or ./prompts.
        """
        self.prompts_dir = Path(prompts_dir or os.environ.get("PROMPTS_DIR", "./prompts"))
        self.prompts: Dict[str, AgentPrompt] = {}
        self._load_default_prompts()
        self._load_custom_prompts()

    def _load_default_prompts(self):
        """Load prompts from modular prompt files."""
        # Collect all prompts from submodules
        all_prompt_dicts = {}
        all_prompt_dicts.update(get_analyst_prompts())
        all_prompt_dicts.update(get_debate_prompts())
        all_prompt_dicts.update(get_risk_prompts())
        all_prompt_dicts.update(get_decision_prompts())

        # Convert dictionaries to AgentPrompt objects
        for agent_key, prompt_dict in all_prompt_dicts.items():
            self.prompts[agent_key] = AgentPrompt(
                agent_key=prompt_dict["agent_key"],
                agent_name=prompt_dict["agent_name"],
                version=prompt_dict["version"],
                system_message=prompt_dict["system_message"],
                category=prompt_dict.get("category", "general"),
                requires_tools=prompt_dict.get("requires_tools", False),
                metadata=prompt_dict.get("metadata", {})
            )

        logger.info("Prompts loaded successfully", count=len(self.prompts))

    def _load_custom_prompts(self):
        """Load custom prompts from JSON files, overriding defaults."""
        if not self.prompts_dir.exists():
            logger.debug("No custom prompts directory found", path=str(self.prompts_dir))
            return

        for json_file in self.prompts_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                agent_key = data.get("agent_key")
                if not agent_key:
                    logger.warning("JSON file missing agent_key", file=json_file.name)
                    continue

                prompt = AgentPrompt(**data)
                self.prompts[agent_key] = prompt
                logger.info("Custom prompt loaded", agent_key=agent_key, version=prompt.version)

            except Exception as e:
                logger.error("Failed to load custom prompt", file=json_file.name, error=str(e))

    def get(self, agent_key: str) -> Optional[AgentPrompt]:
        """
        Get prompt by agent key, checking env var override first.

        Args:
            agent_key: The unique identifier for the agent.

        Returns:
            AgentPrompt if found, None otherwise.

        Environment Override:
            Set PROMPT_{AGENT_KEY} to override the system message.
            Example: PROMPT_MARKET_ANALYST="Custom prompt..."
        """
        env_var = f"PROMPT_{agent_key.upper()}"
        if env_var in os.environ:
            base_prompt = self.prompts.get(agent_key)
            if base_prompt:
                return AgentPrompt(
                    agent_key=agent_key,
                    agent_name=base_prompt.agent_name,
                    version=f"{base_prompt.version}-env",
                    system_message=os.environ[env_var],
                    category=base_prompt.category,
                    requires_tools=base_prompt.requires_tools,
                    metadata={"source": "environment"}
                )

        return self.prompts.get(agent_key)

    def get_all(self) -> Dict[str, AgentPrompt]:
        """
        Get all registered prompts.

        Returns:
            Dict mapping agent_key to AgentPrompt.
        """
        return self.prompts.copy()

    def list_keys(self) -> list:
        """
        List all registered prompt keys.

        Returns:
            List of agent_key strings.
        """
        return list(self.prompts.keys())

    def get_by_category(self, category: str) -> Dict[str, AgentPrompt]:
        """
        Get all prompts in a specific category.

        Args:
            category: The category to filter by.

        Returns:
            Dict of prompts matching the category.
        """
        return {
            key: prompt
            for key, prompt in self.prompts.items()
            if prompt.category == category
        }

    def export_to_json(self, output_dir: Optional[str] = None):
        """
        Export all prompts to JSON files.

        Args:
            output_dir: Directory for output files. Defaults to prompts_dir.
        """
        export_dir = Path(output_dir or self.prompts_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        for agent_key, prompt in self.prompts.items():
            output_file = export_dir / f"{agent_key}.json"

            prompt_dict = {
                "agent_key": prompt.agent_key,
                "agent_name": prompt.agent_name,
                "version": prompt.version,
                "system_message": prompt.system_message,
                "category": prompt.category,
                "requires_tools": prompt.requires_tools,
                "metadata": prompt.metadata
            }

            with open(output_file, 'w') as f:
                json.dump(prompt_dict, f, indent=2)

            logger.info("Prompt exported", agent_key=agent_key, file=str(output_file))


# Global registry instance
_registry = None


def get_registry() -> PromptRegistry:
    """
    Get or create the global prompt registry.

    Returns:
        The singleton PromptRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry


def get_prompt(agent_key: str) -> Optional[AgentPrompt]:
    """
    Convenience function to get a prompt by key.

    Args:
        agent_key: The unique identifier for the agent.

    Returns:
        AgentPrompt if found, None otherwise.
    """
    return get_registry().get(agent_key)


def get_all_prompts() -> Dict[str, AgentPrompt]:
    """
    Convenience function to get all prompts.

    Returns:
        Dict mapping agent_key to AgentPrompt.
    """
    return get_registry().get_all()


def export_prompts(output_dir: Optional[str] = None):
    """
    Convenience function to export prompts.

    Args:
        output_dir: Directory for output files.
    """
    get_registry().export_to_json(output_dir)


# Backward compatibility exports
__all__ = [
    # Core classes
    "AgentPrompt",
    "PromptRegistry",
    # Convenience functions
    "get_registry",
    "get_prompt",
    "get_all_prompts",
    "export_prompts",
    # Submodule access
    "get_analyst_prompts",
    "get_debate_prompts",
    "get_risk_prompts",
    "get_decision_prompts",
]
