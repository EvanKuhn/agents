# Shared configuration: which model to talk to, and where to find it.
# Both can be overridden via environment variables so you can point at a
# different model or a remote Ollama host without touching code.

import os

import ollama

from .personas import DEFAULT_PERSONA

MODEL = os.environ.get("AGENTS_MODEL", "llama3.1")  # "deepseek-r1")
HOST = os.environ.get("AGENTS_HOST", "http://localhost:11434")
THEME = os.environ.get("AGENTS_THEME", "dark")
PERSONA = os.environ.get("AGENTS_PERSONA", DEFAULT_PERSONA)


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
