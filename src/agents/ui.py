# Shared console and styling, so every agent's output looks consistent.

from rich.console import Console

# Single shared rich console that all agents print through
console = Console()

class Theme:
    pass


class DarkTheme(Theme):
    """Colors for terminals with a dark background"""

    USER_PROMPT_COLOR = "bold cyan"
    AGENT_PROMPT_COLOR = "bold yellow"
    STATUS_BAR_FG_COLOR = "grey70"
    STATUS_BAR_BG_COLOR = "grey11"
    SYSTEM_PROMPT_COLOR = "bold red"
    TOOL_CALL_COLOR = "green"
    THINKING_COLOR = "italic grey58"


class LightTheme(Theme):
    """Colors for terminals with a light background"""

    USER_PROMPT_COLOR = "bold blue"
    AGENT_PROMPT_COLOR = "bold magenta"
    STATUS_BAR_FG_COLOR = "grey30"
    STATUS_BAR_BG_COLOR = "grey89"
    SYSTEM_PROMPT_COLOR = "bold red"
    TOOL_CALL_COLOR = "dark_green"
    THINKING_COLOR = "italic grey42"


# Theme name (as passed via --theme / AGENTS_THEME) -> theme class
THEMES = {"dark": DarkTheme, "light": LightTheme}


def get_agent_theme(name: str) -> type[DarkTheme] | type[LightTheme]:
    """
    Return the theme class for the given theme name.
    Raises ValueError for an unknown name.
    """
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(f"Unknown theme {name!r}; choose from {sorted(THEMES)}") from None
