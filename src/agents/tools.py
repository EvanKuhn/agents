# Tools the model can ask us to run. Each tool is a plain Python function:
# the ollama library turns its name, type hints and docstring into the tool
# description sent to the model, so the docstrings below are written for the
# model to read. They're Google style: the summary and the "Args:" section
# are sent to the model, while "Returns:" and "Raises:" are left out.
#
# Everything the model sends is untrusted input, so the tools are read-only,
# the calculator never calls eval(), and file access is limited to
# ALLOWED_DIR.

import ast
import math
import operator
from datetime import datetime
from pathlib import Path

# Directory file tools are limited to: wherever the agent was started from,
# with symlinks resolved so the containment check compares real locations
ALLOWED_DIR = Path.cwd().resolve()

# Most bytes read_file returns, so one big file can't fill the context window
MAX_READ_BYTES = 20_000

# Most entries list_files returns
MAX_LIST_ENTRIES = 200

# Largest integer power the calculator computes, in decimal digits. Python
# refuses to convert ints over ~4300 digits to a string anyway, and this stops
# expressions like 9**9**9 from hanging.
MAX_POW_DIGITS = 4000

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def calculate(expression: str) -> str:
    """
    Evaluate an arithmetic expression and return the result. Use this for any
    math instead of computing it yourself.

    Args:
        expression: Arithmetic using numbers, parentheses and + - * / // % **, e.g. "(3 + 4) * 2**10"

    Returns:
        The result as a string, e.g. "7168".

    Raises:
        SyntaxError: The expression isn't valid Python syntax.
        ValueError: The expression uses anything other than numbers and
            arithmetic, or an integer power would be too large.
        ZeroDivisionError: The expression divides by zero.
        OverflowError: A float result is too large.
    """
    tree = ast.parse(expression, mode="eval")
    return str(_evaluate(tree.body))


def _evaluate(node: ast.AST) -> int | float:
    """
    Recursively evaluate a parsed expression, allowing only numbers and
    arithmetic operators. Anything else (names, calls, attributes...) raises.

    Args:
        node: A node from the tree produced by ast.parse(..., mode="eval").

    Returns:
        The numeric value of the expression.

    Raises:
        ValueError: The expression contains anything other than numbers and
            arithmetic operators, or an integer power would be too large.
        ZeroDivisionError: The expression divides by zero.
        OverflowError: A float result is too large.
    """
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        return _power(_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        return _BINARY_OPS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand))
    raise ValueError("only numbers, parentheses and + - * / // % ** are allowed")


def _power(base: int | float, exponent: int | float) -> int | float:
    """
    base ** exponent, refusing integer results too large to compute quickly.
    (Float results just overflow with an error, so they need no check.)

    Args:
        base: The number to raise to a power.
        exponent: The power to raise it to.

    Returns:
        base ** exponent.

    Raises:
        ValueError: Both are integers and the result would have more than
            MAX_POW_DIGITS digits.
        ZeroDivisionError: base is 0 and exponent is negative.
        OverflowError: A float result is too large.
    """
    if isinstance(base, int) and isinstance(exponent, int) and abs(base) > 1 and exponent > 0:
        if exponent * math.log10(abs(base)) > MAX_POW_DIGITS:
            raise ValueError(f"result would have more than {MAX_POW_DIGITS} digits")
    return base**exponent


def get_current_time() -> str:
    """
    Get the current local date, time and time zone.

    Returns:
        The date and time, e.g. "Tuesday, 2026-09-22 15:24:02 PDT".
    """
    return datetime.now().astimezone().strftime("%A, %Y-%m-%d %H:%M:%S %Z")


def list_files(path: str = ".") -> str:
    """
    List the files and subdirectories in a directory. Directories end in "/".
    Only paths inside the current working directory are allowed.

    Args:
        path: Directory to list, relative to the current working directory. Defaults to "."

    Returns:
        One entry per line, sorted, with directories ending in "/". Lists of
        more than MAX_LIST_ENTRIES are cut off with a note saying how many
        were left out. An empty directory returns "(empty directory)".

    Raises:
        ValueError: path is outside ALLOWED_DIR, or isn't a directory.
        OSError: The directory can't be read, e.g. no permission.
    """
    directory = _resolve_allowed_path(path)
    if not directory.is_dir():
        raise ValueError(f"{path!r} is not a directory")

    entries = sorted(e.name + ("/" if e.is_dir() else "") for e in directory.iterdir())
    if len(entries) > MAX_LIST_ENTRIES:
        extra = len(entries) - MAX_LIST_ENTRIES
        entries = entries[:MAX_LIST_ENTRIES] + [f"... ({extra} more not shown)"]
    return "\n".join(entries) or "(empty directory)"


def read_file(path: str) -> str:
    """
    Read a text file and return its contents. Only files inside the current
    working directory are allowed. Very long files are cut off.

    Args:
        path: File to read, relative to the current working directory

    Returns:
        The file's text. Files longer than MAX_READ_BYTES are cut off, with a
        note appended saying so. Invalid UTF-8 is replaced rather than raising.

    Raises:
        ValueError: path is outside ALLOWED_DIR, isn't a file, or contains a
            null byte (so is treated as binary, not text).
        OSError: The file can't be read, e.g. no permission.
    """
    file = _resolve_allowed_path(path)
    if not file.is_file():
        raise ValueError(f"{path!r} is not a file")

    with file.open("rb") as f:
        data = f.read(MAX_READ_BYTES + 1)
    if b"\0" in data:
        raise ValueError(f"{path!r} is not a text file")

    text = data[:MAX_READ_BYTES].decode("utf-8", errors="replace")
    if len(data) > MAX_READ_BYTES:
        text += f"\n\n[truncated: only the first {MAX_READ_BYTES} bytes are shown]"
    return text


def _resolve_allowed_path(path: str) -> Path:
    """
    Turn a model-supplied path into a real absolute path, and refuse it unless
    it's inside ALLOWED_DIR. resolve() follows symlinks and collapses "..", so
    tricks like "../../etc/passwd" or a symlink pointing outside are caught.

    Args:
        path: A path from the model, either relative to ALLOWED_DIR or absolute.

    Returns:
        The resolved absolute path. It isn't checked for existence.

    Raises:
        ValueError: The resolved path is outside ALLOWED_DIR.
    """
    resolved = (ALLOWED_DIR / path).resolve()
    if not resolved.is_relative_to(ALLOWED_DIR):
        raise ValueError(f"{path!r} is outside the allowed directory {ALLOWED_DIR}")
    return resolved


# All tools offered to the model, and a lookup from tool name to function
TOOLS = [calculate, get_current_time, list_files, read_file]
TOOLS_BY_NAME = {tool.__name__: tool for tool in TOOLS}


def run_tool(name: str, arguments: dict) -> str:
    """
    Run the tool the model asked for and return its result as a string. Any
    failure (unknown tool, bad arguments, a tool raising) comes back as an
    "Error: ..." string instead of an exception, so the model can see what
    went wrong and correct itself. For that reason this never raises.

    Args:
        name: Name of the tool the model asked for.
        arguments: Keyword arguments the model supplied for the tool.

    Returns:
        The tool's result, or an "Error: ..." message describing what went
        wrong.
    """
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return f"Error: unknown tool {name!r}. Available tools: {', '.join(TOOLS_BY_NAME)}"
    try:
        return tool(**arguments)
    except Exception as e:
        return f"Error: {e}"
