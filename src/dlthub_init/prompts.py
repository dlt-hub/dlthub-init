"""Interactive prompts shown during the run."""

from __future__ import annotations

import sys
from typing import cast

import beaupy

from .display import console

CURSOR = "❯"
CURSOR_STYLE = "#59C1D5"
TICK_CHAR = "●"


def _echo_selection(value: str) -> None:
    console.print(f"[{CURSOR_STYLE}]{TICK_CHAR}[/{CURSOR_STYLE}] [bold]{value}[/bold]")


def stdin_is_interactive() -> bool:
    stream = sys.stdin
    try:
        return stream is not None and stream.isatty()
    except (OSError, ValueError):
        return False


def confirm(message: str, *, default: bool = True) -> bool:
    console.print(f"\n[bold]{message}[/bold]")
    if not stdin_is_interactive():
        # No TTY to read a selection from (piped stdin, CI, agents). beaupy would
        # crash with a termios error, so fall back to the default answer instead.
        _echo_selection("Yes" if default else "No")
        return default
    choice = cast(
        str,
        beaupy.select(
            ["Yes", "No"],
            cursor=CURSOR,
            cursor_style=CURSOR_STYLE,
            cursor_index=0 if default else 1,
        ),
    )
    result = choice == "Yes"
    _echo_selection("Yes" if result else "No")
    return result
