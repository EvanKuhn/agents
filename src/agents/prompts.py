# Builds the system prompt every conversation starts with. It has three
# parts, in order:
# 1. Shared instructions (prompts/system.md), always included: where the
#    model is running, today's date, and formatting rules.
# 2. Tool guidance, which depends on whether tools are offered on this run:
#    how to use them (prompts/tools_on.md), or a note that there are none
#    (prompts/tools_off.md) so the model doesn't pretend to have them.
# 3. The persona's text, unless the persona is "none".

from datetime import datetime
from pathlib import Path

from .personas import DEFAULT_PERSONA, load_persona
from .tools import ALLOWED_DIR

# Directory holding the prompt template files
PROMPTS_DIR = Path(__file__).parent / "prompts"


def build_system_prompt(persona: str, tools_enabled: bool) -> str:
    """
    Assemble the full system prompt from the template files, filling in
    today's date and the directory file tools are limited to.

    Args:
        persona: Name of the persona to append, or "none" for no persona.
        tools_enabled: Whether tools are offered to the model on this run.

    Returns:
        The system prompt text.
    """
    if tools_enabled:
        tools = _load_template("tools_on.md").format(allowed_dir=ALLOWED_DIR)
    else:
        tools = _load_template("tools_off.md")

    date = datetime.now().astimezone().strftime("%A, %Y-%m-%d (%Z)")
    prompt = _load_template("system.md").format(date=date, tools=tools)

    if persona != DEFAULT_PERSONA:
        prompt += "\n\n" + load_persona(persona)
    return prompt


def initial_messages(persona: str, tools_enabled: bool) -> list[dict]:
    """
    Return the messages a conversation should start with: a single system
    message holding the full system prompt. Since agents resend the full
    message history every turn, it stays at the front of every request.

    Args:
        persona: Name of the persona to use, or "none" for no persona.
        tools_enabled: Whether tools are offered to the model on this run.

    Returns:
        [{"role": "system", "content": <system prompt>}]
    """
    return [{"role": "system", "content": build_system_prompt(persona, tools_enabled)}]


def _load_template(name: str) -> str:
    """
    Return the text of a template file in PROMPTS_DIR, without surrounding
    whitespace.

    Args:
        name: Filename within PROMPTS_DIR, e.g. "system.md".

    Returns:
        The file's text.
    """
    return (PROMPTS_DIR / name).read_text().strip()
