# Shared console and styling, so every agent's output looks consistent.

from rich.console import Console

# Single shared rich console that all agents print through
console = Console()


class Theme:
    """Colors every theme defines, as rich style strings"""

    USER_PROMPT_COLOR: str
    AGENT_PROMPT_COLOR: str
    SYSTEM_PROMPT_COLOR: str
    STATUS_BAR_FG_COLOR: str
    STATUS_BAR_BG_COLOR: str
    TOOL_CALL_COLOR: str
    THINKING_COLOR: str


class DarkTheme(Theme):
    """Colors for terminals with a dark background"""

    USER_PROMPT_COLOR = "bold cyan"
    AGENT_PROMPT_COLOR = "bold yellow"
    SYSTEM_PROMPT_COLOR = "bold red"
    STATUS_BAR_FG_COLOR = "grey70"
    STATUS_BAR_BG_COLOR = "grey11"
    TOOL_CALL_COLOR = "green"
    THINKING_COLOR = "italic grey58"


class LightTheme(Theme):
    """Colors for terminals with a light background"""

    USER_PROMPT_COLOR = "bold blue"
    AGENT_PROMPT_COLOR = "bold magenta"
    SYSTEM_PROMPT_COLOR = "bold red"
    STATUS_BAR_FG_COLOR = "grey30"
    STATUS_BAR_BG_COLOR = "grey89"
    TOOL_CALL_COLOR = "dark_green"
    THINKING_COLOR = "italic grey42"


# Theme name (as passed via --theme / AGENTS_THEME) -> theme class
THEMES = {"dark": DarkTheme, "light": LightTheme}


def get_agent_theme(name: str) -> type[Theme]:
    """
    Return the theme class for the given theme name.
    Raises ValueError for an unknown name.
    """
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(f"Unknown theme {name!r}; choose from {sorted(THEMES)}") from None


def user_prompt(theme: type[Theme]) -> str:
    """Return the user prompt string"""
    return f"[{theme.USER_PROMPT_COLOR}]User:[/{theme.USER_PROMPT_COLOR}] "


def agent_prompt(theme: type[Theme]) -> str:
    """Return the agent prompt string"""
    return f"\n[{theme.AGENT_PROMPT_COLOR}]Assistant:[/{theme.AGENT_PROMPT_COLOR}]"


def system_prompt(theme: type[Theme]) -> str:
    """Return the system prompt string"""
    return f"[{theme.SYSTEM_PROMPT_COLOR}]System:[/{theme.SYSTEM_PROMPT_COLOR}]"
