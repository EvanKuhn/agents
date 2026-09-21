# CLI entry point. `agents <name>` dispatches to one of the agents below -
# add new agents here as they're built.

import argparse

from . import simple, working_memory

AGENTS = {
    "simple": simple.main,
    "chat": working_memory.main,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents", description="Run one of the agents in this project."
    )
    parser.add_argument("agent", choices=sorted(AGENTS), help="which agent to run")
    args = parser.parse_args()

    AGENTS[args.agent]()
