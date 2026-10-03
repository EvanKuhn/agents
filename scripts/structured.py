#!/usr/bin/env -S uv run python
# Compares two ways of getting structured answers from the model:
# - constrained : the JSON schema is passed as Ollama's `format` param, so the
#                 reply has to match it
# - free        : the model is only asked for JSON, and can reply with anything
#
# Each task runs in both modes through Agent.run_structured_turn(), which
# validates the answer with pydantic and retries with the errors if it fails.
# The table at the end shows how many attempts each needed, and whether it
# ended with a valid answer.
#
# Each task's schema has a check the JSON schema can't express (a word limit,
# an "@" in an email), so even constrained replies can fail validation.
#
# Run it from anywhere inside the repo with ./scripts/structured.py. qwen3 is
# slow with thinking on; --no-think makes a run much quicker.

import argparse
import time
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from rich.table import Table

from agents.agent import Agent, AgentObserver, Reply, StructuredOutputError
from agents.config import Config, model_capabilities
from agents.prompts import initial_messages
from agents.tools import TOOLS
from agents.ui import console

# --------------------------------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------------------------------


class Contact(BaseModel):
    name: str = Field(description="The person's full name")
    email: str = Field(description="Their email address")
    phone: str | None = Field(description="Their current phone number, or null if not given")

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("must be an email address, containing '@'")
        return value


class Review(BaseModel):
    sentiment: Literal["positive", "negative", "mixed"]
    score: float = Field(ge=-1, le=1, description="-1 (very negative) to 1 (very positive)")
    summary: str = Field(description="One-sentence summary, at most 12 words")

    @field_validator("summary")
    @classmethod
    def check_summary(cls, value: str) -> str:
        if len(value.split()) > 12:
            raise ValueError(f"must be at most 12 words, not {len(value.split())}")
        return value


class Calculation(BaseModel):
    expression: str = Field(description="The arithmetic you did, e.g. '2 * 3'")
    result: float = Field(description="The final number")


# --------------------------------------------------------------------------------------------------
# Tasks
# --------------------------------------------------------------------------------------------------


@dataclass
class Task:
    """
    A prompt to answer in the shape of a schema.
    - name   : short name for the results table
    - prompt : the user's message
    - schema : pydantic model the answer must match
    - tools  : whether to offer tools while answering
    """

    name: str
    prompt: str
    schema: type[BaseModel]
    tools: bool = False


TASKS = [
    Task(
        name="contact",
        prompt=(
            "Extract the contact details from this message: \"Hi, I'm Dana Whitfield, the new ops "
            "lead. Reach me at dana.w at example dot org or 555-0142 (my old number, 555-0199, "
            'no longer works)."'
        ),
        schema=Contact,
    ),
    Task(
        name="review",
        prompt=(
            'Classify this product review: "The battery lasts forever and the screen is gorgeous, '
            "but the speakers crackle at any volume above half and support never answered my "
            'emails. I kept it, but I would not buy it again."'
        ),
        schema=Review,
    ),
    Task(
        name="calculation",
        prompt="What is 1234 * 5678, minus the number of days in a leap year?",
        schema=Calculation,
        tools=True,
    ),
]


# --------------------------------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------------------------------


class CountingObserver(AgentObserver):
    """
    Counts what happens during a turn, and prints validation errors as they come.
    """

    def __init__(self) -> None:
        self.replies = 0
        self.tool_calls = 0
        self.failures = 0

    def reply_finished(self, reply: Reply) -> None:
        self.replies += 1

    def tool_called(self, name: str, arguments: dict, result: str) -> None:
        self.tool_calls += 1

    def validation_failed(self, errors: str) -> None:
        self.failures += 1
        console.print(f"    failed validation:\n{errors}", style="yellow", markup=False)


def run_task(config: Config, task: Task, constrained: bool, think: bool, has_tools: bool) -> list:
    """
    Run one task in one mode, print the answer, and return a row for the table.
    """
    mode = "constrained" if constrained else "free"
    console.print(f"[bold]{task.name}[/bold] ({mode})")

    tools = TOOLS if task.tools and has_tools else None
    observer = CountingObserver()
    agent = Agent(
        client=config.get_client(),
        model=config.model,
        messages=initial_messages(config.model, config.persona, tools_enabled=bool(tools)),
        tools=tools,
        think=think,
        max_rounds=config.max_rounds,
        observer=observer,
    )

    start = time.monotonic()
    try:
        answer = agent.run_structured_turn(task.prompt, task.schema, constrained=constrained)
        console.print(f"    {answer!r}", markup=False, highlight=False)
        valid = True
    except StructuredOutputError:
        console.print("    gave up", style="red")
        valid = False
    elapsed = time.monotonic() - start

    # Every failed attempt was reported to the observer; a valid answer took one more
    attempts = observer.failures + 1 if valid else observer.failures
    return [
        task.name,
        mode,
        "[green]valid[/green]" if valid else "[red]gave up[/red]",
        str(attempts),
        str(observer.tool_calls),
        f"{elapsed:.0f}s",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare schema-constrained and free JSON answers."
    )
    parser.add_argument("--no-think", action="store_true", help="Turn off thinking (much faster)")
    parser.add_argument("--task", choices=[task.name for task in TASKS], help="Run only this task")
    args = parser.parse_args()

    config = Config.from_env()
    capabilities = model_capabilities(config.get_client(), config.model)
    think = "thinking" in capabilities and not args.no_think
    has_tools = "tools" in capabilities
    console.print(f"Model: {config.model} (thinking {'on' if think else 'off'})\n")

    table = Table("Task", "Mode", "Outcome", "Attempts", "Tool calls", "Time")
    for task in TASKS:
        if args.task and task.name != args.task:
            continue
        for constrained in (True, False):
            table.add_row(*run_task(config, task, constrained, think, has_tools))
        console.print()
    console.print(table)


if __name__ == "__main__":
    main()
