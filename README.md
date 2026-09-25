# AI Agents

A simple AI agent implemented with Python, built up step by step (see `PLAN.md`).

## Usage

```
uv run agent
```

This starts a chat in your terminal. The agent keeps the full conversation history, so the model
remembers earlier turns, and it can use tools.

Set `AGENTS_MODEL` / `AGENTS_HOST` to point at a different model or Ollama host (defaults:
`qwen3` at `http://localhost:11434`).

Set `AGENTS_THEME=light|dark` (default `dark`), or pass `--theme=light|dark` on the command line,
to switch prompt and status bar colors for light- or dark-background terminals.

Every conversation starts with a shared system prompt, built from the templates in
`src/agents/prompts/`: where the agent is running, today's date, formatting rules, and guidance on
using tools (or a note that there are none).

Set `AGENTS_PERSONA=<name>`, or pass `--persona=<name>`, to give the agent a personality from
`src/agents/personas/` (e.g. `pirate`, `socratic`, `terse`), appended to the shared system
prompt. The `none` persona (the default) adds no personality. To add a persona, drop a new `.md`
file in that directory.

The agent offers the model tools (a calculator, the current time, and listing/reading files),
defined in `src/agents/tools.py`. File tools only work inside the directory you start the agent
from. Pass `--no-tools` to turn tools off.

The agent can use tools over several rounds before answering: it calls a tool, looks at the
result, and decides what to do next. Pass `--max-rounds=N` to change the limit (default 10), and
`--show-thinking` to watch a thinking model reason between steps.

## Development

Format, lint and type check the code with [ruff](https://docs.astral.sh/ruff/) and
[ty](https://docs.astral.sh/ty/), both configured in `pyproject.toml`:

```
make format   # uv run ruff check --select I --fix, then uv run ruff format
make lint     # uv run ruff check
make types    # uv run ty check
```

## Scripts

- `scripts/helloworld.py`: The hello world of agents. Sends one query to the model and prints the
  response. Run it from inside the repo with `./scripts/helloworld.py`.
