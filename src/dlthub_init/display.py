"""Rich-powered terminal output: header, sync spinner, failures, next steps."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from packaging.version import Version
from rich.console import Console
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import strings
from .errors import DlthubCommandError, UvError

console = Console()


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
    console.print(f"[green]✓[/green] {done}")


def print_header(project_dir: Path, dlt_version: Version) -> None:
    console.print(strings.MSG_HEADER.format(project_dir=escape(_display_path(project_dir)), dlt_version=dlt_version))


def print_command_failed(exc: DlthubCommandError) -> None:
    console.print(strings.MSG_STEP_FAILED.format(step=exc.step, returncode=exc.returncode))
    if exc.hint:
        console.print(exc.hint)


def print_sync_failed(exc: UvError) -> None:
    console.print(strings.MSG_SYNC_FAILED.format(message=escape(str(exc))))


def print_next_steps(project_dir: Path, *, sync_pending: bool) -> None:
    steps: list[tuple[str, str | None]] = []
    cd = _display_path(project_dir)
    if cd != ".":
        steps.append((strings.STEPS_LABEL_CD, strings.CMD_CD.format(project_dir=cd)))
    if sync_pending:
        steps.append((strings.STEPS_LABEL_INSTALL_DEPS, strings.CMD_UV_SYNC))
    steps.append((strings.STEPS_LABEL_OPEN_AGENT, None))

    single = len(steps) == 1
    header = strings.LABEL_NEXT_STEP if single else strings.LABEL_NEXT_STEPS
    console.print(f"\n[bold #C6D300]{header}[/bold #C6D300]")
    for index, (label, command) in enumerate(steps, start=1):
        prefix = "" if single else f"{index}. "
        console.print(f"  {prefix}{label}")
        if command is not None:
            console.print(f"     [bold #59C1D5]{escape(command)}[/bold #59C1D5]")


def _display_path(project_dir: Path) -> str:
    try:
        relative = Path(os.path.relpath(project_dir))
    except ValueError:
        return str(project_dir)
    if os.pardir in relative.parts:
        return str(project_dir)
    return str(relative)
