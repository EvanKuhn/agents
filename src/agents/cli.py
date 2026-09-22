# CLI entry point. `agent` parses options into config, then starts the chat
# agent.

import argparse

from . import chat, config
from .personas import list_personas


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent", description="Chat with a local AI agent.")
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
    args = parser.parse_args()

    if args.no_tools:
        config.TOOLS_ENABLED = False
    if args.theme:
        config.THEME = args.theme
    if args.persona:
        config.PERSONA = args.persona
    if config.PERSONA not in list_personas():
        parser.error(f"unknown persona {config.PERSONA!r} (choose from {', '.join(list_personas())})")

    chat.main()
