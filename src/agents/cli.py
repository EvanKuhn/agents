# CLI entry point. `agent` parses options into a Config, then starts the chat
# agent with it.

import argparse

import ollama

from . import chat
from .config import Config
from .personas import list_personas


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent", description="Chat with a local AI agent.")

    # Define options

    parser.add_argument(
        "--model",
        help=f"Ollama model to use (default: $AGENTS_MODEL or '{Config.model}')",
    )
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
        help=f"Most rounds of tool calls per question (default: {Config.max_rounds})",
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

    # Build the config from user-provided options. Flags that weren't given
    # are None, so the environment variables and defaults apply instead.

    try:
        config = Config.from_env(
            model=args.model,
            theme=args.theme,
            persona=args.persona,
            max_rounds=args.max_rounds,
            tools_enabled=False if args.no_tools else None,
            show_thinking=args.show_thinking or None,
            show_system_prompt=args.show_system_prompt or None,
        )
    except ValueError as e:
        parser.error(str(e))

    # Run the chat. Ollama's own messages are clear, e.g. "model 'x' not found"
    # or "Failed to connect to Ollama", so show them without a traceback.

    try:
        chat.main(config)
    except (ollama.ResponseError, ConnectionError) as e:
        parser.exit(1, f"agent: error: {e}\n")
