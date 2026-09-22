# CLI entry point. `agents <name>` dispatches to one of the agents below -
# add new agents here as they're built.

import argparse

from . import chat, config, simple
from .personas import list_personas

AGENTS = {
    "simple": simple.main,
    "chat": chat.main,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents", description="Run one of the agents in this project."
    )
    parser.add_argument("agent", choices=sorted(AGENTS), help="which agent to run")
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        help="color theme for prompts and status bar (default: $AGENTS_THEME or 'dark')",
    )
    parser.add_argument(
        "--persona",
        choices=list_personas(),
        help="system prompt to use, from src/agents/personas/ (default: $AGENTS_PERSONA or 'none', i.e. no system prompt)",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="don't offer tools (calculator, clock, file reading) to the model",
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

    AGENTS[args.agent]()
