# Simple 'hello world' agent. Sends a single prompt to the model and
# streams the response back.

from . import config
from .ui import ASSISTANT_STYLE, USER_STYLE, console

QUERY = "Why is the sky blue?"


def main() -> None:
    client = config.get_client()

    console.print(f"[{USER_STYLE}]User:[/{USER_STYLE}] {QUERY}")
    stream = client.chat(
        model=config.MODEL,
        messages=[{"role": "user", "content": QUERY}],
        stream=True,
    )

    console.print(f"[{ASSISTANT_STYLE}]Assistant:[/{ASSISTANT_STYLE}] ", end="")
    for chunk in stream:
        console.print(chunk["message"]["content"], end="", markup=False, highlight=False)
    console.print()
