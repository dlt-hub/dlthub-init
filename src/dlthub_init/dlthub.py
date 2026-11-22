"""Build and run the `dlthub` commands that create the workspace and set up the coding agent."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from packaging.version import Version

from . import strings
from .config import AGENT_INIT_MIN_DLT
from .errors import DlthubCommandError, WorkspaceError
from .uv import isolated_project_env

InitMode = Literal["merge", "overwrite", "skip"]
StepName = Literal["init", "ai init"]


@dataclass(frozen=True)
class InitOptions:
    mode: InitMode = "merge"
    name: str | None = None
    dependencies: str | None = None
    dry_run: bool = False
    agent: str | None = None
    """Name of the coding agent, `None` to detect it."""
    yes: bool = False


@dataclass(frozen=True)
class DlthubStep:
    name: StepName
    args: list[str]
    """Arguments that follow the `dlthub` executable."""


def get_dlt_version() -> Version:
    return Version(version("dlt"))


def has_agent_init(dlt_version: Version) -> bool:
    """True when `dlthub init` sets up the coding agent and merges into existing projects."""
    return dlt_version >= Version(AGENT_INIT_MIN_DLT)


def has_workspace(project_dir: Path) -> bool:
    return (project_dir / ".dlt" / ".workspace").is_file()


def build_steps(options: InitOptions, dlt_version: Version, *, workspace_exists: bool = False) -> list[DlthubStep]:
    """The `dlthub` commands that create the workspace with `options` on `dlt_version`."""
    global_args = ["-v", *(["-y"] if options.yes else [])]
    init_args = ["init"]
    if options.name:
        init_args += ["--name", options.name]
    if options.dependencies:
        init_args += ["--dependencies", options.dependencies]
    if options.dry_run:
        init_args.append("--dry-run")

    if has_agent_init(dlt_version):
        if options.mode != "merge":
            init_args.append(f"--{options.mode}")
        # `--agent` takes an optional value, so it goes last
        init_args += ["--agent", *([options.agent] if options.agent else [])]
        return [DlthubStep("init", [*global_args, *init_args])]

    steps: list[DlthubStep] = []
    if options.mode == "overwrite":
        steps.append(DlthubStep("init", [*global_args, *init_args, "--force"]))
    elif not workspace_exists:
        # older dlt cannot merge and stops on an existing workspace, which then only gets the agent
        steps.append(DlthubStep("init", [*global_args, *init_args]))
    if not options.dry_run:
        ai_args = ["ai", "init", *(["--agent", options.agent] if options.agent else [])]
        steps.append(DlthubStep("ai init", [*global_args, *ai_args]))
    return steps


def find_dlthub() -> str:
    """The `dlthub` executable of the dlt installed next to this interpreter."""
    scripts_dir = sysconfig.get_path("scripts")
    found = shutil.which("dlthub", path=scripts_dir)
    if found is None:
        raise WorkspaceError(strings.ERROR_DLTHUB_NOT_FOUND.format(path=scripts_dir))
    return found


def build_env(uv_executable: str | None, *, telemetry_off: bool) -> dict[str, str]:
    """Environment of the `dlthub` commands."""
    env = isolated_project_env()
    if uv_executable is not None:
        # dlthub runs `uv` from PATH
        env["PATH"] = os.pathsep.join(p for p in (str(Path(uv_executable).parent), env.get("PATH")) if p)
    if telemetry_off:
        env["RUNTIME__DLTHUB_TELEMETRY"] = "false"
    return env


def run_step(dlthub: str, step: DlthubStep, project_dir: Path, env: dict[str, str]) -> int:
    """Runs `step` attached to the terminal and returns its exit code."""
    # the child writes to the same terminal, after what is buffered here
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        return subprocess.run([dlthub, *step.args], cwd=project_dir, env=env, check=False).returncode
    except OSError as exc:
        raise WorkspaceError(strings.ERROR_DLTHUB_FAILED_TO_START.format(cmd=dlthub, reason=exc)) from exc


def raise_on_failure(step: DlthubStep, returncode: int, options: InitOptions, dlt_version: Version) -> None:
    if returncode == 0:
        return
    raise DlthubCommandError(step.name, returncode, hint=get_failure_hint(step, options, dlt_version))


def get_failure_hint(step: DlthubStep, options: InitOptions, dlt_version: Version) -> str | None:
    """What to do next after `step` failed."""
    if step.name == "ai init":
        return strings.HINT_FINISH_AGENT_SETUP.format(agent=options.agent or "<agent>")
    # only an init that merges or overwrites asks, so only there a failure may be a "no"
    if has_agent_init(dlt_version) and not (options.yes or options.dry_run or options.mode == "skip"):
        return strings.HINT_CONFIRM_CHANGES
    return None
