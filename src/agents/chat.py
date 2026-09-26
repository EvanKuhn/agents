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

from .agent import Agent, AgentObserver, Reply
from .config import Config, model_capabilities
from .prompts import initial_messages
from .tools import ALLOWED_DIR, TOOLS, TOOLS_BY_NAME
from .ui import agent_prompt, console, get_agent_theme, system_prompt, user_prompt


def main(config: Config) -> None:
    AgentChat(config).run()


# --------------------------------------------------------------------------------------------------
# AgentChat
# --------------------------------------------------------------------------------------------------


class AgentChat:
    """
    A chat session in the terminal: sets up the agent from config, then
    reads the user's messages and hands each one to the agent.
    """

    def __init__(self, config: Config) -> None:
        """
        Args:
            config: Settings for the chat and the agent.
        """
        self.config = config
        client = config.get_client()
        capabilities = model_capabilities(client, config.model)
        self.theme = get_agent_theme(config.theme)
        self.tools = TOOLS if config.tools_enabled and "tools" in capabilities else None
        self.agent = Agent(
            client=client,
            model=config.model,
            messages=initial_messages(config.model, config.persona, tools_enabled=bool(self.tools)),
            tools=self.tools,
            think="thinking" in capabilities,
            max_rounds=config.max_rounds,
            observer=ConsoleObserver(self.theme, config.show_thinking, config.max_rounds),
        )

    def run(self) -> None:
        """
        Print the header (and the system prompt, if asked), then chat until
        the user types 'exit' or 'quit', or presses Ctrl+D/Ctrl+C.
        """
        self._print_header()
        self._print_system_prompt_if_enabled()
        self._run_agent_loop()

    def _print_header(self) -> None:
        """
        Print which model and persona the chat uses, and which tools are available.
        """
        console.print(
            f"Chatting with {self.config.model} (persona: {self.config.persona}) - "
            "type 'exit' or 'quit' to stop."
        )
        if self.tools:
            console.print(f"- Tools: {', '.join(TOOLS_BY_NAME)}")
            console.print(f"- Max {self.config.max_rounds} tool calls per query")
            console.print(f"- File access limited to {ALLOWED_DIR}")
        elif self.config.tools_enabled:
            console.print(f"- Tools: off ({self.config.model} doesn't support tool calling)")
        else:
            console.print("- Tools: off")
        console.print()

    def _print_system_prompt_if_enabled(self) -> None:
        """
        Print the system prompt the model receives, if --show-system-prompt was given.
        It's the first message in the history.
        """
        if self.config.show_system_prompt:
            console.print(system_prompt(self.theme))
            console.print(
                self.agent.messages[0]["content"] + "\n",
                style=self.theme.THINKING_COLOR,
                markup=False,
                highlight=False,
            )

    def _run_agent_loop(self) -> None:
        """
        Read the user's messages and hand each one to the agent, until the
        user types 'exit' or 'quit', or presses Ctrl+D/Ctrl+C.
        """
        while True:
            # Get user prompt
            try:
                user_input = console.input(user_prompt(self.theme)).strip()
            except EOFError, KeyboardInterrupt:
                console.print()
                break

            # Handle empty string or exit/quit
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            # Let the agent work on it; the observer prints its progress
            console.print(agent_prompt(self.theme))
            self.agent.run_turn(user_input)


# --------------------------------------------------------------------------------------------------
# ConsoleObserver
# --------------------------------------------------------------------------------------------------


class ConsoleObserver(AgentObserver):
    """
    Shows the agent's progress in the terminal: each reply streams in as
    markdown, with a status line showing elapsed time / tokens / tool use /
    state, and each tool call is printed with a preview of its result. The
    elapsed time and tokens are totals for the whole turn, so they keep
    counting across tool calls rather than restarting with each reply.
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
        self.turn_start = 0.0
        self.turn_tokens = 0  # tokens from this turn's finished replies

    def turn_started(self) -> None:
        self.turn_start = time.monotonic()
        self.turn_tokens = 0

    def reply_started(self, round_number: int | None) -> None:
        self.round_number = round_number
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
        self.turn_tokens += reply.token_count
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

        # Build status parts: elapsed time and tokens for the whole turn, rounds
        # of tool calls made so far this turn (one fewer than the round this
        # reply is in), status
        elapsed = time.monotonic() - self.turn_start
        tokens = self.turn_tokens + reply.token_count
        parts = [f"{elapsed:.0f}s", f"{tokens} tokens"]
        if self.round_number:
            parts.append(f"Tool calls: {self.round_number - 1}/{self.max_rounds}")
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
