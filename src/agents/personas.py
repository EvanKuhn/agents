# Personas give the agent a personality. Each is a markdown file in the
# personas/ directory whose text is appended to the shared system prompt
# (see prompts.py). A persona's name is its filename without the .md
# extension. The special "none" persona (the default) adds no personality,
# leaving the model's built-in style; the shared instructions still apply.

from pathlib import Path

# Directory holding one <name>.md file per persona
PERSONAS_DIR = Path(__file__).parent / "personas"

# Persona used when none is chosen; has no file and adds no personality
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
    Return the text for the named persona, read from PERSONAS_DIR/<name>.md.
    Not valid for "none", which has no file.
    """
    return (PERSONAS_DIR / f"{name}.md").read_text().strip()
