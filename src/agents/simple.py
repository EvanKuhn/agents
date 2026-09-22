# Simple 'hello world' agent. Sends a single prompt to the model and
# streams the response back.

from . import config
from .ui import console, get_agent_theme

QUERY = "Why is the sky blue?"


def main() -> None:
    client = config.get_client()
    theme = get_agent_theme(config.THEME)

    console.print(f"[{theme.USER_PROMPT_COLOR}]User:[/{theme.USER_PROMPT_COLOR}] {QUERY}")
    stream = client.chat(
        model=config.MODEL,
        messages=[{"role": "user", "content": QUERY}],
        stream=True,
    )

    console.print(f"[{theme.AGENT_PROMPT_COLOR}]Assistant:[/{theme.AGENT_PROMPT_COLOR}] ", end="")
    for chunk in stream:
        console.print(chunk["message"]["content"], end="", markup=False, highlight=False)
    console.print()
