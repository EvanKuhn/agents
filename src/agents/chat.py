# Working memory agent. Wraps the LLM call in a REPL loop and keeps a
# running list of messages, resending the full conversation history
# to the model on every turn. This is what gives the agent "memory" of
# what's been said so far - the model itself is stateless, so without
# resending history it would forget every prior turn.
#
# Tools (see tools.py) are offered to the model unless --no-tools is given.
# If the model asks to call one, we run it, add the result to the history,
# and ask the model again so it can answer using the result.
#
# Type 'exit' or 'quit' to end the conversation, or press Ctrl+D/Ctrl+C.
#
# Try deliberately having a long conversation (or pasting in a big block of
# text) to see what happens when the conversation outgrows the model's
# context window.

import time

import ollama
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown

from . import config
from .prompts import initial_messages
from .tools import ALLOWED_DIR, TOOLS, TOOLS_BY_NAME, run_tool
from .ui import console, get_agent_theme


def main() -> None:
    # Initialize client and other fields
    client = config.get_client()
    think = config.supports_thinking(client)
    theme = get_agent_theme(config.THEME)
    tools = TOOLS if config.TOOLS_ENABLED and config.supports_tools(client) else None
    messages = initial_messages(config.PERSONA, tools_enabled=bool(tools))

    # Print header
    console.print(
        f"Chatting with {config.MODEL} (persona: {config.PERSONA}) - type 'exit' or 'quit' to stop."
    )
    if tools:
        console.print(f"Tools: {', '.join(TOOLS_BY_NAME)} (files limited to {ALLOWED_DIR})\n")
    elif config.TOOLS_ENABLED:
        console.print(f"Tools: off ({config.MODEL} doesn't support tool calling)\n")
    else:
        console.print("Tools: off\n")

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

        # Print assistant output, and save it (including any tool calls it
        # asked for) to message history
        console.print(f"\n[{theme.AGENT_PROMPT_COLOR}]Assistant:[/{theme.AGENT_PROMPT_COLOR}]")
        reply, tool_calls = stream_reply(client, messages, theme, think, tools)
        messages.append({"role": "assistant", "content": reply, "tool_calls": tool_calls})

        # If the model asked for tools, run them, save the results to message
        # history, and ask again so it can answer using them. The follow-up
        # request offers no tools, so there's at most one round of tool calls.
        if tool_calls:
            for call in tool_calls:
                name, arguments = call.function.name, call.function.arguments
                result = run_tool(name, arguments)
                print_tool_call(theme, name, arguments, result)
                messages.append({"role": "tool", "tool_name": name, "content": result})

            # TODO: do we really want/need to disable tools here?
            reply, _ = stream_reply(client, messages, theme, think, tools=None)
            messages.append({"role": "assistant", "content": reply})


def stream_reply(
    client: ollama.Client,
    messages: list,
    theme,
    think: bool,
    tools: list | None,
) -> tuple[str, list]:
    """
    Send the conversation to the model and stream its reply to the console,
    re-rendering it as markdown as it grows, with a status line showing
    elapsed time / tokens / state. Returns the reply text and any tool calls
    the model asked for (an empty list if none).
    """
    stream = client.chat(model=config.MODEL, messages=messages, stream=True, think=think, tools=tools)

    reply = ""
    tool_calls = []
    token_count = 0
    start = time.monotonic()
    with Live(console=console, refresh_per_second=10, vertical_overflow="ellipsis") as live:
        for chunk in stream:
            message = chunk["message"]
            content = message["content"]
            reply += content
            if content:
                token_count += 1

            # Tool calls can arrive in any chunk, so collect them as we go
            tool_calls.extend(message.get("tool_calls") or [])

            done = chunk.get("done", False)
            if done:
                # Ollama reports the exact output token count on the
                # final chunk; prefer it over our running approximation
                token_count = chunk.get("eval_count", token_count)

            # Get agent status
            if done:
                status_word = "Done"
            elif tool_calls:
                status_word = "Calling tools..."
            elif message.get("thinking"):
                status_word = "Thinking..."
            else:
                status_word = "Generating..."

            # Assemble status line
            elapsed = time.monotonic() - start
            status_str = f"{elapsed:.0f}s - {token_count} tokens - {status_word}"
            status_style = f"{theme.STATUS_BAR_FG_COLOR} on {theme.STATUS_BAR_BG_COLOR}"

            # Update console output
            live.update(Group(Markdown(reply), f"[{status_style}]{status_str}[/{status_style}]"))
    console.print()

    return reply, tool_calls


def print_tool_call(theme, name: str, arguments: dict, result: str) -> None:
    """
    Print a one-line summary of a tool call and its (shortened) result. Eg:
    → calculate(expression='1234*5678') = 7006652
    """
    args = ", ".join(f"{key}={value!r}" for key, value in arguments.items())
    preview = result.replace("\n", " ")
    if len(preview) > 80:
        preview = preview[:77] + "..."
    console.print(
        f"→ {name}({args}) = {preview}\n", style=theme.TOOL_CALL_COLOR, markup=False, highlight=False
    )
