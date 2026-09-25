#!/usr/bin/env -S uv run python
# Simple 'hello world' agent. Sends a single prompt to the model and
# streams the response back.
#
# Run it from anywhere inside the repo with ./scripts/helloworld.py. The
# shebang uses `uv run`, which finds the project (and its installed `agents`
# package) by searching up from the current directory.

from agents import config
from agents.prompts import initial_messages
from agents.ui import agent_prompt, console, get_agent_theme, user_prompt

QUERY = "Why is the sky blue?"


def main() -> None:
    client = config.get_client()
    theme = get_agent_theme(config.THEME)

    console.print(user_prompt(theme) + QUERY)
    stream = client.chat(
        model=config.MODEL,
        messages=initial_messages(config.PERSONA, tools_enabled=False)
        + [{"role": "user", "content": QUERY}],
        stream=True,
    )

    console.print(agent_prompt(theme), end=" ")
    for chunk in stream:
        console.print(chunk["message"]["content"], end="", markup=False, highlight=False)
    console.print()


if __name__ == "__main__":
    main()
