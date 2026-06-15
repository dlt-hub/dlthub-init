"""Rich-powered terminal output: status lines, write summary, next steps."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import strings
from .collisions import Outcome, PlannedPath

console = Console()
err_console = Console(stderr=True)

_SUMMARY_SECTIONS = (
    (Outcome.CREATE, strings.LABEL_CREATED, "green"),
    (Outcome.OVERWRITE, strings.LABEL_OVERWRITTEN, "yellow"),
    (Outcome.MERGE, strings.LABEL_MERGED, "yellow"),
    (Outcome.SKIP, strings.LABEL_SKIPPED, "dim"),
    (Outcome.DISABLED, strings.LABEL_DISABLED, "dim"),
)


def substep_done(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def substep_detail(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")


@contextmanager
def substep(running: str, done: str, *, verbose: bool = False) -> Iterator[None]:
    if verbose:
        console.print(f"[dim]{running}…[/dim]")
        yield
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(running, total=None)
            yield
    substep_done(done)


def print_header(project_dir: Path) -> None:
    console.print(strings.MSG_HEADER.format(project_dir=_display_path(project_dir)))


def print_summary(plan: list[PlannedPath]) -> None:
    printed = False
    for outcome, label, style in _SUMMARY_SECTIONS:
        entries = sorted(str(p.relative) for p in plan if p.outcome is outcome)
        if not entries:
            continue
        printed = True
        console.print(f"\n[bold {style}]{label}:[/bold {style}]")
        for entry in entries:
            console.print(f"  {entry}")
    if not printed:
        console.print(strings.MSG_NOTHING_WRITTEN)


def print_next_steps(project_dir: Path, *, synced: bool, uv_installed: bool) -> None:
    steps: list[tuple[str, str | None]] = []
    cd = _display_path(project_dir)
    if cd != ".":
        steps.append((strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=cd)))
    if not synced:
        if not uv_installed:
            steps.append((strings.STEPS_LABEL_INSTALL_UV, strings.CMD_INSTALL_UV_UNIX))
        steps.append((strings.STEPS_LABEL_INSTALL_DEPS, strings.CMD_UV_SYNC))
    steps.append((strings.STEPS_LABEL_ADD_SECRETS, None))
    steps.append((strings.STEPS_LABEL_BUILD, None))

    console.print(f"\n[bold #C6D300]{strings.LABEL_NEXT_STEPS}[/bold #C6D300]")
    for index, (label, command) in enumerate(steps, start=1):
        console.print(f"  {index}. {label}")
        if command is not None:
            console.print(f"     [bold #59C1D5]{command}[/bold #59C1D5]")


def print_collision(conflicts: list[str]) -> None:
    err_console.print(strings.MSG_COLLISION_HEADER)
    for path in conflicts:
        err_console.print(f"  [bold]{path}[/bold]")
    err_console.print(strings.MSG_COLLISION_NO_CHANGES)
    err_console.print(strings.MSG_COLLISION_HINT)


def _display_path(project_dir: Path) -> str:
    try:
        relative = Path(os.path.relpath(project_dir))
    except ValueError:
        return str(project_dir)
    if os.pardir in relative.parts:
        return str(project_dir)
    return str(relative)
