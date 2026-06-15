"""Interactive prompts shown during the run."""

from __future__ import annotations

from typing import cast

import beaupy

from .display import console

CURSOR = "❯"
CURSOR_STYLE = "#59C1D5"
TICK_CHAR = "●"


def _echo_selection(value: str) -> None:
    console.print(f"[{CURSOR_STYLE}]{TICK_CHAR}[/{CURSOR_STYLE}] [bold]{value}[/bold]")


def confirm(message: str, *, default: bool = True) -> bool:
    console.print(f"\n[bold]{message}[/bold]")
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
