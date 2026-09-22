# Personas are system prompts stored as markdown files in the personas/
# directory. A persona's name is its filename without the .md extension.
# The special "none" persona (the default) sends no system prompt at all,
# leaving the model's built-in behavior as a baseline to compare against.

from pathlib import Path

# Directory holding one <name>.md file per persona
PERSONAS_DIR = Path(__file__).parent / "personas"

# Persona used when none is chosen; has no file and sends no system prompt
DEFAULT_PERSONA = "none"


def list_personas() -> list[str]:
    """
    Return the sorted names of all available personas: every .md file in
    PERSONAS_DIR, plus the built-in "none" persona. Eg:
    - ["none", "pirate", "socratic", "terse"]
    """
    return sorted({DEFAULT_PERSONA, *(p.stem for p in PERSONAS_DIR.glob("*.md"))})


def load_persona(name: str) -> str:
    """
    Return the system prompt text for the named persona, read from
    PERSONAS_DIR/<name>.md. Not valid for "none", which has no file.
    """
    return (PERSONAS_DIR / f"{name}.md").read_text().strip()


def initial_messages(name: str) -> list[dict]:
    """
    Return the messages a conversation should start with for the named
    persona. This is a single system message holding the persona's prompt,
    or an empty list for "none". Since agents resend the full message
    history every turn, the system message stays at the front of every
    request. Eg:
    - "none"  : []
    - "terse" : [{"role": "system", "content": "Answer in exactly one sentence..."}]
    """
    if name == DEFAULT_PERSONA:
        return []
    return [{"role": "system", "content": load_persona(name)}]
