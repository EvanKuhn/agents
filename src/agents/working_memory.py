# Working memory agent. Like simple, but wraps the call in a REPL loop and
# keeps a running list of messages, resending the full conversation history
# to the model on every turn. This is what gives the agent "memory" of
# what's been said so far - the model itself is stateless, so without
# resending history it would forget every prior turn.
#
# Type 'exit' or 'quit' to end the conversation, or press Ctrl+D/Ctrl+C.
#
# Try deliberately having a long conversation (or pasting in a big block of
# text) to see what happens when the conversation outgrows the model's
# context window.

from rich.live import Live
from rich.markdown import Markdown

from . import config
from .ui import ASSISTANT_STYLE, USER_STYLE, console


def main() -> None:
    client = config.get_client()
    messages = []

    console.print(f"Chatting with {config.MODEL} - type 'exit' or 'quit' to stop.\n")

    while True:
        # Get user prompt
        try:
            user_input = console.input(f"[{USER_STYLE}]User:[/{USER_STYLE}] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        # Handle empty string or exit/quit
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        # Save user input to message history
        messages.append({"role": "user", "content": user_input})

        # Print assistant output
        console.print(f"\n[{ASSISTANT_STYLE}]Assistant:[/{ASSISTANT_STYLE}]")
        stream = client.chat(model=config.MODEL, messages=messages, stream=True)

        # Stream response to console, re-rendering as markdown as it grows
        assistant_response = ""
        with Live(console=console, refresh_per_second=10) as live:
            for chunk in stream:
                assistant_response += chunk["message"]["content"]
                live.update(Markdown(assistant_response))
        console.print()

        # Save response to message history
        messages.append({"role": "assistant", "content": assistant_response})
