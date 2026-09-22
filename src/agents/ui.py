# Shared console and styling, so every agent's output looks consistent.

from rich.console import Console

console = Console()


class DarkTheme:
    USER_PROMPT_COLOR = "bold cyan"
    AGENT_PROMPT_COLOR = "bold yellow"
    STATUS_BAR_FG_COLOR = "grey70"
    STATUS_BAR_BG_COLOR = "grey11"


class LightTheme:
    USER_PROMPT_COLOR = "bold blue"
    AGENT_PROMPT_COLOR = "bold magenta"
    STATUS_BAR_FG_COLOR = "grey30"
    STATUS_BAR_BG_COLOR = "grey89"


THEMES = {"dark": DarkTheme, "light": LightTheme}


def get_agent_theme(theme: str) -> type[DarkTheme] | type[LightTheme]:
    try:
        return THEMES[theme]
    except KeyError:
        raise ValueError(f"Unknown theme {theme!r}; choose from {sorted(THEMES)}") from None
