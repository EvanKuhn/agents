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

import time

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown

from . import config
from .personas import initial_messages
from .ui import console, get_agent_theme


def main() -> None:
    # Initialize client and other fields
    client = config.get_client()
    think = config.supports_thinking(client)
    theme = get_agent_theme(config.THEME)
    messages = initial_messages(config.PERSONA)

    # Print header
    console.print(
        f"Chatting with {config.MODEL} (persona: {config.PERSONA}) - type 'exit' or 'quit' to stop.\n"
    )

    while True:
        # Get user prompt
        try:
            user_input = console.input(
                f"[{theme.USER_PROMPT_COLOR}]User:[/{theme.USER_PROMPT_COLOR}] "
            ).strip()
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
        console.print(f"\n[{theme.AGENT_PROMPT_COLOR}]Assistant:[/{theme.AGENT_PROMPT_COLOR}]")
        stream = client.chat(model=config.MODEL, messages=messages, stream=True, think=think)

        # Stream response to console, re-rendering as markdown as it grows,
        # with a status line showing elapsed time / tokens / state
        assistant_response = ""
        token_count = 0
        start = time.monotonic()
        with Live(console=console, refresh_per_second=10, vertical_overflow="ellipsis") as live:
            for chunk in stream:
                message = chunk["message"]
                content = message["content"]
                assistant_response += content
                if content:
                    token_count += 1

                done = chunk.get("done", False)
                if done:
                    # Ollama reports the exact output token count on the
                    # final chunk; prefer it over our running approximation
                    token_count = chunk.get("eval_count", token_count)

                # Get agent status
                if done:
                    status_word = "Done"
                elif message.get("thinking"):
                    status_word = "Thinking..."
                else:
                    status_word = "Generating..."

                # Assemble status line
                elapsed = time.monotonic() - start
                status_str = f"{elapsed:.0f}s - {token_count} tokens - {status_word}"
                status_style = f"{theme.STATUS_BAR_FG_COLOR} on {theme.STATUS_BAR_BG_COLOR}"

                # Update console output
                live.update(Group(Markdown(assistant_response), f"[{status_style}]{status_str}[/{status_style}]"))
        console.print()

        # Save response to message history
        messages.append({"role": "assistant", "content": assistant_response})
