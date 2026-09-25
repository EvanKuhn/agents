# The terminal chat: reads your messages, hands each one to the agent (see
# agent.py), and shows what the agent is doing as it works. The agent keeps
# the full conversation history, resending it to the model on every turn.
# This is what gives it "memory" of what's been said so far - the model
# itself is stateless, so without resending history it would forget every
# prior turn.
#
# Tools (see tools.py) are offered to the model unless --no-tools is given.
# The agent may call tools over several rounds before answering, up to
# --max-rounds per question.
#
# Type 'exit' or 'quit' to end the conversation, or press Ctrl+D/Ctrl+C.
#
# Try deliberately having a long conversation (or pasting in a big block of
# text) to see what happens when the conversation outgrows the model's
# context window.

import time

from rich.console import Group, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from . import config
from .agent import Agent, AgentObserver, Reply
from .prompts import initial_messages
from .tools import ALLOWED_DIR, TOOLS, TOOLS_BY_NAME
from .ui import agent_prompt, console, get_agent_theme, system_prompt, user_prompt


def main() -> None:
    # Initialize client and other fields
    client = config.get_client()
    theme = get_agent_theme(config.THEME)
    tools = TOOLS if config.TOOLS_ENABLED and config.supports_tools(client) else None
    agent = Agent(
        client=client,
        model=config.MODEL,
        messages=initial_messages(config.PERSONA, tools_enabled=bool(tools)),
        tools=tools,
        think=config.supports_thinking(client),
        max_rounds=config.MAX_ROUNDS,
        observer=ConsoleObserver(theme, config.SHOW_THINKING, config.MAX_ROUNDS),
    )

    # Print header
    console.print(
        f"Chatting with {config.MODEL} (persona: {config.PERSONA}) - type 'exit' or 'quit' to stop."
    )
    if tools:
        console.print(
            f"Tools: {', '.join(TOOLS_BY_NAME)} (up to {config.MAX_ROUNDS} rounds per question; "
            f"files limited to {ALLOWED_DIR})\n"
        )
    elif config.TOOLS_ENABLED:
        console.print(f"Tools: off ({config.MODEL} doesn't support tool calling)\n")
    else:
        console.print("Tools: off\n")

    # Optionally print the system prompt. It's the first message in the history.
    if config.SHOW_SYSTEM_PROMPT:
        console.print(system_prompt(theme))
        console.print(
            agent.messages[0]["content"] + "\n",
            style=theme.THINKING_COLOR,
            markup=False,
            highlight=False,
        )

    while True:
        # Get user prompt
        try:
            user_input = console.input(user_prompt(theme)).strip()
        except EOFError, KeyboardInterrupt:
            console.print()
            break

        # Handle empty string or exit/quit
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        # Let the agent work on it; the observer prints its progress
        console.print(agent_prompt(theme))
        agent.run_turn(user_input)


class ConsoleObserver(AgentObserver):
    """
    Shows the agent's progress in the terminal: each reply streams in as
    markdown, with a status line showing elapsed time / tokens / round /
    state, and each tool call is printed with a preview of its result.
    """

    def __init__(self, theme, show_thinking: bool, max_rounds: int) -> None:
        """
        Args:
            theme: Theme class with the colors to use (see ui.py).
            show_thinking: Whether to show the model's thinking above its reply.
            max_rounds: Round limit, shown in the status line.
        """
        self.theme = theme
        self.show_thinking = show_thinking
        self.max_rounds = max_rounds
        self.live: Live | None = None
        self.round_number: int | None = None
        self.start = 0.0

    def reply_started(self, round_number: int | None) -> None:
        self.round_number = round_number
        self.start = time.monotonic()
        self.live = Live(console=console, refresh_per_second=10, vertical_overflow="ellipsis")
        self.live.start()

    def reply_updated(self, reply: Reply) -> None:
        if self.live:
            self.live.update(self._render(reply))

    def reply_finished(self, reply: Reply) -> None:
        if self.live:
            self.live.update(self._render(reply))
            self.live.stop()
            self.live = None
        console.print()

    def tool_called(self, name: str, arguments: dict, result: str) -> None:
        """
        Print a one-line summary of a tool call and its (shortened) result. Eg:
        → calculate(expression='1234*5678') = 7006652
        """
        args = ", ".join(f"{key}={value!r}" for key, value in arguments.items())
        preview = result.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        console.print(
            f"Tool → {name}({args}) = {preview}\n",
            style=self.theme.TOOL_CALL_COLOR,
            markup=False,
            highlight=False,
        )

    def _render(self, reply: Reply) -> RenderableType:
        """
        Build what the live display shows for a reply: its thinking (if
        shown), the reply text as markdown, and the status line.
        """
        # Determine status
        if reply.done:
            status_word = "Done"
        elif reply.tool_calls:
            status_word = "Calling tools..."
        elif reply.thinking_now:
            status_word = "Thinking..."
        else:
            status_word = "Generating..."

        # Build prompt parts: elapsed time, token count, round number, status
        elapsed = time.monotonic() - self.start
        parts = [f"{elapsed:.0f}s", f"{reply.token_count} tokens"]
        if self.round_number:
            parts.append(f"Round {self.round_number}/{self.max_rounds}")
        parts.append(status_word)
        status = Text(
            " - ".join(parts),
            style=f"{self.theme.STATUS_BAR_FG_COLOR} on {self.theme.STATUS_BAR_BG_COLOR}",
        )

        renderables: list[RenderableType] = []
        if self.show_thinking and reply.thinking.strip():
            renderables.append(Text(reply.thinking.strip() + "\n", style=self.theme.THINKING_COLOR))
        renderables.append(Markdown(reply.text))
        renderables.append(status)
        return Group(*renderables)
