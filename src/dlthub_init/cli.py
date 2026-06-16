"""Command-line entrypoint for the `dlthub-init` CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import strings
from .collisions import Flags
from .config import DEFAULT_SCAFFOLD
from .display import (
    console,
    err_console,
    print_collision,
    print_header,
    print_next_steps,
    print_summary,
    substep,
    substep_detail,
)
from .errors import CollisionError, UvError, WorkspaceError
from .prompts import confirm
from .scaffold import apply_scaffold, resolve_target
from .skills import install_skills
from .uv import execute_uv_install, find_uv, run_uv_sync


def _ensure_utf8_io_on_windows() -> None:
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dlthub-init",
        description="Scaffold a dltHub workspace into a new or existing directory.",
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="Directory to initialize. Defaults to the current directory.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Stream output from uv.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Scaffold files only; do not create a virtual environment or install dependencies.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated files (never secrets).",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Append missing entries to an existing .gitignore instead of skipping it.",
    )
    parser.add_argument(
        "--no-pyproject",
        action="store_true",
        help="Skip pyproject.toml.",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Skip .gitignore.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_io_on_windows()
    args = build_parser().parse_args(argv)

    try:
        run(args)
    except KeyboardInterrupt:
        console.print(strings.MSG_CANCELLED)
        return 130
    except CollisionError as exc:
        print_collision(exc.conflicts)
        return 2
    except WorkspaceError as exc:
        console.print(strings.MSG_ERROR_PREFIX.format(message=exc))
        return 1
    except Exception as exc:
        console.print(strings.MSG_UNEXPECTED_ERROR.format(message=exc))
        if args.verbose:
            console.print_exception()
        else:
            console.print(strings.MSG_UNEXPECTED_ERROR_HINT)
        return 1
    return 0


def run(args: argparse.Namespace) -> None:
    if args.yes:
        err_console.print(strings.MSG_TESTING_SHORTCUT_NOTE)

    verbose = args.verbose
    scaffold = DEFAULT_SCAFFOLD
    flags = Flags(
        force=args.force,
        merge=args.merge,
        no_pyproject=args.no_pyproject,
        no_gitignore=args.no_gitignore,
    )

    project_dir = resolve_target(args.project_dir)
    print_header(project_dir)

    plan = apply_scaffold(project_dir, scaffold=scaffold, flags=flags)
    installed_skills = install_skills(project_dir)
    print_summary(plan)
    if installed_skills:
        substep_detail(strings.MSG_SKILLS_INSTALLED.format(count=len(installed_skills)))

    synced = _maybe_sync(project_dir, args, verbose=verbose)
    print_next_steps(project_dir, synced=synced, uv_installed=find_uv() is not None)


def _maybe_sync(project_dir: Path, args: argparse.Namespace, *, verbose: bool) -> bool:
    if args.no_sync:
        console.print(strings.MSG_SKIPPED_SYNC)
        return False

    uv_executable = find_uv()
    if uv_executable is None and not (args.yes or confirm(strings.PROMPT_INSTALL_UV, default=True)):
        console.print(strings.MSG_SKIPPED_SYNC)
        return False

    if not args.yes and not confirm(strings.PROMPT_CREATE_VENV, default=True):
        console.print(strings.MSG_SKIPPED_SYNC)
        return False

    try:
        if uv_executable is None:
            uv_executable = execute_uv_install(verbose=verbose)
        with substep(strings.MSG_INSTALLING_DEPS, strings.MSG_INSTALLED_DEPS, verbose=verbose):
            run_uv_sync(uv_executable, project_dir, verbose=verbose)
    except UvError as exc:
        console.print(strings.MSG_SYNC_FAILED.format(message=exc))
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
