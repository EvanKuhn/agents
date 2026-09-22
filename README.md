# AI Agents

A simple set of AI agents implemented with Python.

## Usage

```
uv run agents <name>
```

Set `AGENTS_MODEL` / `AGENTS_HOST` to point at a different model or Ollama host (defaults: `llama3.1` at `http://localhost:11434`).

Set `AGENTS_THEME=light|dark` (default `dark`), or pass `--theme=light|dark` on the command line, to switch prompt and status bar colors for light- or dark-background terminals.

Every conversation starts with a shared system prompt, built from the templates in `src/agents/prompts/`: where the agent is running, today's date, formatting rules, and guidance on using tools (or a note that there are none).

Set `AGENTS_PERSONA=<name>`, or pass `--persona=<name>`, to give the agent a personality from `src/agents/personas/` (e.g. `pirate`, `socratic`, `terse`), appended to the shared system prompt. The `none` persona (the default) adds no personality. To add a persona, drop a new `.md` file in that directory.

The `chat` agent offers the model tools (a calculator, the current time, and listing/reading files), defined in `src/agents/tools.py`. File tools only work inside the directory you start the agent from. Pass `--no-tools` to turn tools off.

__The Cast__
- **simple**: The hello world of agents. Sends a query, prints the response.
- **chat**: Adds working memory. Runs a REPL loop and resends the full conversation history each turn, so the model remembers earlier turns. Also supports personas and tool calling.
