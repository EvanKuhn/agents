# CLI entry point. `agents <name>` dispatches to one of the agents below -
# add new agents here as they're built.

import argparse

from . import chat, config, simple

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
    args = parser.parse_args()

    if args.theme:
        config.THEME = args.theme

    AGENTS[args.agent]()
