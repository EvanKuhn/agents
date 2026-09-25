# CLI entry point. `agent` parses options into config, then starts the chat
# agent.

import argparse

from . import chat, config
from .personas import list_personas


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent", description="Chat with a local AI agent.")

    # Define options

    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        help="Color theme for prompts and status bar",
    )
    parser.add_argument(
        "--persona",
        choices=list_personas(),
        help="Agent personality, or 'none' for no personality",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Don't offer tools (calculator, clock, file reading) to the model",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        metavar="N",
        help=f"Most rounds of tool calls per question (default: {config.MAX_ROUNDS})",
    )
    parser.add_argument(
        "--show-thinking",
        action="store_true",
        help="Show the model's thinking (thinking models only)",
    )
    parser.add_argument(
        "--show-system-prompt",
        action="store_true",
        help="Print the system prompt at the start of the chat",
    )
    args = parser.parse_args()

    # Update config with user-provided options

    if args.no_tools:
        config.TOOLS_ENABLED = False
    if args.max_rounds is not None:
        if args.max_rounds < 1:
            parser.error("--max-rounds must be at least 1")
        config.MAX_ROUNDS = args.max_rounds
    if args.show_thinking:
        config.SHOW_THINKING = True
    if args.show_system_prompt:
        config.SHOW_SYSTEM_PROMPT = True
    if args.theme:
        config.THEME = args.theme
    if args.persona:
        config.PERSONA = args.persona
    if config.PERSONA not in list_personas():
        parser.error(
            f"unknown persona {config.PERSONA!r} (choose from {', '.join(list_personas())})"
        )

    # Run the chat

    chat.main()
