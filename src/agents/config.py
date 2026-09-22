# Shared configuration: which model to talk to, and where to find it.
# Both can be overridden via environment variables so you can point at a
# different model or a remote Ollama host without touching code.

import os

import ollama

from .personas import DEFAULT_PERSONA

# Some models:
# - deepseek-r1   : Thinking model but fails with tools.
# - llama3.1      : Fast and lightweight. Has trouble with tools.
# - qwen3         : Good for tool calling. Runs slower.

MODEL = os.environ.get("AGENTS_MODEL", "llama3.1")  # "deepseek-r1")
HOST = os.environ.get("AGENTS_HOST", "http://localhost:11434")
THEME = os.environ.get("AGENTS_THEME", "dark")
PERSONA = os.environ.get("AGENTS_PERSONA", DEFAULT_PERSONA)

# Whether to offer tools to the model; turned off with --no-tools
TOOLS_ENABLED = True


def get_client() -> ollama.Client:
    """
    Return an ollama.Client instance
    """
    return ollama.Client(host=HOST)


def supports_thinking(client: ollama.Client) -> bool:
    """
    Returns a bool indicating if the model supports thinking. Eg:
    - llama3.1     : False
    - deepseek-r1  : True
    """
    return "thinking" in (client.show(MODEL).capabilities or [])


def supports_tools(client: ollama.Client) -> bool:
    """
    Returns a bool indicating if the model supports tool calling. Eg:
    - llama3.1     : True
    - deepseek-r1  : True
    """
    return "tools" in (client.show(MODEL).capabilities or [])
