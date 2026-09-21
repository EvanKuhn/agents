# Shared configuration: which model to talk to, and where to find it.
# Both can be overridden via environment variables so you can point at a
# different model or a remote Ollama host without touching code.

import os

import ollama

MODEL = os.environ.get("AGENTS_MODEL", "llama3.1")
HOST = os.environ.get("AGENTS_HOST", "http://localhost:11434")


def get_client() -> ollama.Client:
    return ollama.Client(host=HOST)
