# Shared configuration: which model to use, where to find it, and how the chat
# behaves. cli.py builds one Config at startup and passes it to whatever needs
# it. Each setting comes from, in increasing priority: the defaults below, the
# AGENTS_* environment variables, and command-line flags.

import os
from dataclasses import dataclass
from typing import Any, Self

import ollama

from .personas import DEFAULT_PERSONA, list_personas
from .ui import THEMES

# Some models:
# - deepseek-r1   : Thinking model but fails with tools.
# - llama3.1      : Fast and lightweight. Has trouble with tools.
# - qwen3         : Good for tool calling. Runs slower.

# Settings that can be set by environment variable, and the variable for each
ENV_VARS = {
    "model": "AGENTS_MODEL",
    "host": "AGENTS_HOST",
    "theme": "AGENTS_THEME",
    "persona": "AGENTS_PERSONA",
}


@dataclass(frozen=True)
class Config:
    """
    All the settings for a run. Frozen, so nothing can change a setting once
    the agent has started.
    - model              : Ollama model to use
    - host               : URL of the Ollama server
    - theme              : color theme, "dark" or "light"
    - persona            : persona to append to the system prompt, or "none"
    - tools_enabled      : whether to offer tools to the model (--no-tools)
    - max_rounds         : most rounds of tool calls per question (--max-rounds)
    - show_thinking      : whether to show the model's thinking (--show-thinking)
    - show_system_prompt : whether to print the system prompt (--show-system-prompt)
    """

    model: str = "qwen3"
    host: str = "http://localhost:11434"
    theme: str = "dark"
    persona: str = DEFAULT_PERSONA
    tools_enabled: bool = True
    max_rounds: int = 10
    show_thinking: bool = False
    show_system_prompt: bool = False

    def __post_init__(self) -> None:
        """
        Check the settings are valid, so mistakes are caught at startup.

        Raises:
            ValueError: A setting has an invalid value.
        """
        if self.theme not in THEMES:
            raise ValueError(f"unknown theme {self.theme!r} (choose from {', '.join(THEMES)})")
        if self.persona not in list_personas():
            raise ValueError(
                f"unknown persona {self.persona!r} (choose from {', '.join(list_personas())})"
            )
        if self.max_rounds < 1:
            raise ValueError("max rounds must be at least 1")

    @classmethod
    def from_env(cls, **overrides: Any) -> Self:
        """
        Build a Config from the defaults, then the AGENTS_* environment
        variables, then the given overrides.

        Args:
            overrides: Settings to use instead, e.g. from command-line flags.
                A value of None means "not given", and is ignored.

        Returns:
            The new Config.

        Raises:
            ValueError: A setting has an invalid value.
        """
        values: dict[str, Any] = {
            name: os.environ[var] for name, var in ENV_VARS.items() if var in os.environ
        }
        values.update({name: value for name, value in overrides.items() if value is not None})
        return cls(**values)

    def get_client(self) -> ollama.Client:
        """
        Return an ollama.Client for the configured host. Doesn't contact the
        server until it's used.
        """
        return ollama.Client(host=self.host)


def model_capabilities(client: ollama.Client, model: str) -> list[str]:
    """
    Ask the Ollama server what the model can do. Kept out of Config because it
    talks to the server, and a Config should be cheap to create. Eg:
    - llama3.1    : ["completion", "tools"]
    - qwen3       : ["completion", "tools", "thinking"]

    Args:
        client: Ollama client to ask.
        model: Name of the model.

    Returns:
        The model's capabilities, e.g. "tools" or "thinking".
    """
    return list(client.show(model).capabilities or [])
