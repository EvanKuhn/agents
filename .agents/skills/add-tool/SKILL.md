---
name: add-tool
description: Add a new tool that the chat agent can offer to the model, such as a file search or web fetch tool. Use when asked to add, create or implement a tool in src/agents/tools.py.
---

# Adding a tool to the agent

Tools are plain Python functions in `src/agents/tools.py`. The `ollama` library builds the tool
description the model sees from each function's name, type hints and docstring, so the docstring
is part of the prompt.

## Steps

1. Write the function in `tools.py`, next to the existing tools.
   - Give every parameter a type hint.
   - Return a string. The model only ever sees the tool result as text.
   - Raise an exception with a clear message for bad input. `run_tool()` turns it into an
     `Error: ...` result for the model, so don't catch errors inside the tool.
2. Write a Google-style docstring aimed at the model:
   - The summary says what the tool does and when to use it.
   - `Args:` describes each parameter, with an example value where it helps.
   - `Returns:` and `Raises:` are for human readers; the model never sees them.
3. Add the function to the `TOOLS` list at the bottom of the file.
4. If the model needs guidance on when to use the tool, add a line to
   `src/agents/prompts/tools_on.md`.

## Safety

Everything the model passes in is untrusted.

- Keep tools read-only unless the task clearly needs otherwise, and say so if it does.
- Never use `eval()`, `exec()` or `shell=True` on model input.
- Resolve any file path with `_resolve_allowed_path()` so it stays inside `ALLOWED_DIR`.
- Cap the size of what the tool returns, like `MAX_READ_BYTES`, so one call can't fill the
  context window.

## Check your work

Check the schema the model will receive, and look for missing descriptions:

```bash
uv run python -c "import json; from agents.tools import TOOLS; from ollama._utils import convert_function_to_tool; print(json.dumps(convert_function_to_tool(TOOLS[-1]).model_dump(exclude_none=True)['function'], indent=2))"
```

Then call it directly with `run_tool()`, including bad input and paths that try to escape
`ALLOWED_DIR`, and finally ask `uv run agent` a question that needs the tool.
