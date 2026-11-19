"""Command-line entrypoint for the `dlthub-init` CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import strings, telemetry
from .config import DISTRIBUTION_NAME
from .display import console, print_command_failed, print_header, print_next_steps, print_sync_failed, substep
from .dlthub import (
    InitMode,
    InitOptions,
    build_env,
    build_steps,
    find_dlthub,
    get_dlt_version,
    has_workspace,
    raise_on_failure,
    run_step,
)
from .errors import DlthubCommandError, UvError, WorkspaceError
from .uv import find_uv, run_uv_sync


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
        prog=DISTRIBUTION_NAME,
        description=(
            "Create a dltHub workspace with `dlthub init`, set up your coding agent and install the"
            " dependencies. In an existing project, dlthub lists the changes and asks first."
        ),
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=None,
        help="Directory to initialize, created when missing. Defaults to the current directory.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Workspace name. Defaults to the directory name.",
    )
    existing = parser.add_mutually_exclusive_group()
    existing.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Overwrite the existing dependency file, .gitignore and .dlt/.workspace instead of merging"
            " into them. The settings files are never overwritten."
        ),
    )
    existing.add_argument("--force", dest="overwrite", action="store_true", help=argparse.SUPPRESS)
    existing.add_argument(
        "--skip",
        action="store_true",
        help="Keep existing files as they are and create only the missing ones, without asking.",
    )
    parser.add_argument(
        "--dependencies",
        choices=["auto", "pyproject", "requirements"],
        default=None,
        help="Dependency file to create. See `dlthub init --help`.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without writing anything.",
    )
    # takes a required value, unlike in `dlthub init`, so it never swallows the directory
    parser.add_argument(
        "--agent",
        default=None,
        metavar="NAME",
        help="Coding agent to set up, for example claude, cursor, codex or cortex. Detected when omitted.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Apply the changes to existing files without asking.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show the output of uv sync.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not install the dependencies with uv sync.",
    )
    parser.add_argument(
        "--no-telemetry",
        action="store_true",
        help="Disable usage telemetry for this run, also in the dlthub commands it runs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_io_on_windows()
    args = build_parser().parse_args(argv)
    telemetry.init(no_telemetry=args.no_telemetry)

    try:
        run(args)
    except KeyboardInterrupt:
        telemetry.track_run("cancelled")
        console.print(strings.MSG_CANCELLED)
        return 130
    except DlthubCommandError as exc:
        telemetry.add_properties(failed_step=exc.step)
        telemetry.track_run("failed", error_code=type(exc).__name__)
        print_command_failed(exc)
        return exc.returncode if exc.returncode > 0 else 1
    except WorkspaceError as exc:
        telemetry.track_run("failed", error_code=type(exc).__name__)
        console.print(strings.MSG_ERROR_PREFIX.format(message=exc))
        return 1
    except Exception as exc:
        telemetry.track_run("failed", error_code=type(exc).__name__)
        console.print(strings.MSG_UNEXPECTED_ERROR.format(message=exc))
        if args.verbose:
            console.print_exception()
        else:
            console.print(strings.MSG_UNEXPECTED_ERROR_HINT)
        return 1
    telemetry.track_run("success")
    return 0


def run(args: argparse.Namespace) -> None:
    project_dir = resolve_target(args.project_dir)
    dlt_version = get_dlt_version()
    telemetry.add_properties(dlt_version=str(dlt_version))
    options = InitOptions(
        mode=_get_mode(args),
        name=args.name,
        dependencies=args.dependencies,
        dry_run=args.dry_run,
        agent=args.agent,
        yes=args.yes,
    )
    dlthub = find_dlthub()
    uv_executable = find_uv()
    env = build_env(uv_executable, telemetry_off=telemetry.is_opted_out(args.no_telemetry))

    print_header(project_dir, dlt_version)
    _make_dir(project_dir)
    for step in build_steps(options, dlt_version, workspace_exists=has_workspace(project_dir)):
        raise_on_failure(step, run_step(dlthub, step, project_dir, env), options, dlt_version)
    if options.dry_run:
        return

    if not (project_dir / "pyproject.toml").is_file():
        # `uv sync` needs a pyproject.toml, dlthub already said how to install a requirements.txt
        print_next_steps(project_dir, sync_pending=False)
        return
    synced = _maybe_sync(project_dir, uv_executable, no_sync=args.no_sync, verbose=args.verbose)
    print_next_steps(project_dir, sync_pending=not synced)


def resolve_target(requested_arg: str | None) -> Path:
    if requested_arg is not None:
        return Path(requested_arg).expanduser().resolve()
    return Path.cwd().resolve()


def _get_mode(args: argparse.Namespace) -> InitMode:
    if args.overwrite:
        return "overwrite"
    if args.skip:
        return "skip"
    return "merge"


def _make_dir(project_dir: Path) -> None:
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(strings.ERROR_WRITE_FAILED.format(path=project_dir, reason=exc)) from exc


def _maybe_sync(project_dir: Path, uv_executable: str | None, *, no_sync: bool, verbose: bool) -> bool:
    if no_sync:
        return False
    if uv_executable is None:
        console.print(strings.MSG_NO_UV)
        return False
    try:
        with substep(strings.MSG_INSTALLING_DEPS, strings.MSG_INSTALLED_DEPS, verbose=verbose):
            run_uv_sync(uv_executable, project_dir, verbose=verbose)
    except UvError as exc:
        print_sync_failed(exc)
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
