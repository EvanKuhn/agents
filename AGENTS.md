# Agent Instructions

A learning project: a local AI agent built up step by step on top of Ollama. `PLAN.md` lists the
steps and which are done. `journal/` holds the owner's notes on what was learned, one file per day
(`<yyyymmdd>.md`); the owner writes these, so don't edit existing entries unless asked.

## Commands

- `uv run agent`: start the chat agent. Options: `--theme`, `--persona`, `--no-tools`.
- `./scripts/helloworld.py`: send one prompt to the model and print the reply.
- Config comes from `AGENTS_MODEL`, `AGENTS_HOST`, `AGENTS_THEME` and `AGENTS_PERSONA`; CLI flags
  override them. The default model is `qwen3`, which needs Ollama running locally.
- `make format`, `make lint` and `make types`: format, lint and type check, using ruff and ty
  (configured in `pyproject.toml`).

## Layout

All code is in `src/agents/`:

- `cli.py`: argument parsing; sets values in `config.py`, then starts `chat.py`.
- `chat.py`: the chat loop, streaming output, and running tool calls.
- `tools.py`: the tools offered to the model.
- `prompts.py` and `prompts/`: the shared system prompt, built from Markdown templates.
- `personas.py` and `personas/`: optional personalities appended to the system prompt.
- `ui.py`: the shared `rich` console and light/dark themes.

## Conventions

- Tool docstrings in `tools.py` are sent to the model: the `ollama` library turns the summary and
  `Args:` section into the tool description. Write them for the model, in Google style.
- Treat everything the model sends as untrusted input. Tools stay read-only, never use `eval()`,
  and file access stays inside `ALLOWED_DIR`.
- Use `rich` (via `ui.console`) for all terminal output, with colors from the theme classes.
- Resolve settings that CLI flags can override inside functions, not at import time, since
  `cli.py` sets them after the modules are imported.
- Wrap Markdown files under 100 characters, except code blocks and tables.

## Workflow

- Don't commit or push unless asked.
- After changing Python code, run `make format`, `make lint` and `make types`, and fix what they
  report rather than silencing it.
- Test changes by running the agent against a real model, not just by importing the code.
- Skills live in `.agents/skills/` (`.claude/skills` is a symlink to it): `add-tool` for adding
  a tool, and `journal-entry` for starting a new journal entry.
