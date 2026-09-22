# AI Agents

A simple set of AI agents implemented with Python.

## Usage

```
uv run agents <name>
```

Set `AGENTS_MODEL` / `AGENTS_HOST` to point at a different model or Ollama host (defaults: `llama3.1` at `http://localhost:11434`).

Set `AGENTS_THEME=light|dark` (default `dark`), or pass `--theme=light|dark` on the command line, to switch prompt and status bar colors for light- or dark-background terminals.

__The Cast__
- **simple**: The hello world of agents. Sends a query, prints the response.
- **chat**: Adds working memory. Runs a REPL loop and resends the full conversation history each turn, so the model remembers earlier turns.
