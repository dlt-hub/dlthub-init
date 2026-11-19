import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from dlthub_init import dlthub
from dlthub_init.dlthub import (
    DlthubStep,
    InitOptions,
    build_env,
    build_steps,
    find_dlthub,
    get_dlt_version,
    get_failure_hint,
    has_workspace,
    raise_on_failure,
    run_step,
)
from dlthub_init.errors import DlthubCommandError, WorkspaceError

NEW_DLT = Version("1.33.0a2")
OLD_DLT = Version("1.32.0")
INIT = DlthubStep("init", [])


def named_args(steps: list[DlthubStep]) -> list[tuple[str, list[str]]]:
    return [(step.name, step.args) for step in steps]


@pytest.mark.parametrize(
    "options,args",
    [
        pytest.param(InitOptions(), ["-v", "init", "--agent"], id="detect-agent"),
        pytest.param(
            InitOptions(name="ws", dependencies="pyproject", agent="cortex"),
            ["-v", "init", "--name", "ws", "--dependencies", "pyproject", "--agent", "cortex"],
            id="named-agent",
        ),
        pytest.param(InitOptions(mode="overwrite"), ["-v", "init", "--overwrite", "--agent"], id="overwrite"),
        pytest.param(InitOptions(mode="skip"), ["-v", "init", "--skip", "--agent"], id="skip"),
        pytest.param(InitOptions(yes=True), ["-v", "-y", "init", "--agent"], id="yes"),
        pytest.param(InitOptions(dry_run=True), ["-v", "init", "--dry-run", "--agent"], id="dry-run"),
    ],
)
def test_new_dlt_runs_one_init_with_the_agent_last(options: InitOptions, args: list[str]) -> None:
    assert named_args(build_steps(options, NEW_DLT)) == [("init", args)]
    # new dlt merges into an existing workspace
    assert named_args(build_steps(options, NEW_DLT, workspace_exists=True)) == [("init", args)]


@pytest.mark.parametrize(
    "dlt_version,steps",
    [
        # 1.33.0a1 knows `--agent` but has neither `--overwrite` nor `--skip`
        pytest.param("1.33.0a1", 2, id="1.33.0a1"),
        pytest.param("1.33.0a2", 1, id="1.33.0a2"),
        pytest.param("1.33.0", 1, id="1.33.0"),
    ],
)
def test_first_dlt_that_merges(dlt_version: str, steps: int) -> None:
    assert len(build_steps(InitOptions(), Version(dlt_version))) == steps


@pytest.mark.parametrize(
    "options,steps",
    [
        pytest.param(InitOptions(), [("init", ["-v", "init"]), ("ai init", ["-v", "ai", "init"])], id="detect-agent"),
        pytest.param(
            InitOptions(agent="claude", name="ws"),
            [("init", ["-v", "init", "--name", "ws"]), ("ai init", ["-v", "ai", "init", "--agent", "claude"])],
            id="named-agent",
        ),
        pytest.param(
            InitOptions(mode="overwrite"),
            [("init", ["-v", "init", "--force"]), ("ai init", ["-v", "ai", "init"])],
            id="overwrite-is-force",
        ),
        pytest.param(
            InitOptions(mode="skip"), [("init", ["-v", "init"]), ("ai init", ["-v", "ai", "init"])], id="skip"
        ),
        pytest.param(InitOptions(dry_run=True), [("init", ["-v", "init", "--dry-run"])], id="dry-run"),
        pytest.param(
            InitOptions(yes=True), [("init", ["-v", "-y", "init"]), ("ai init", ["-v", "-y", "ai", "init"])], id="yes"
        ),
    ],
)
def test_old_dlt_runs_init_then_ai_init(options: InitOptions, steps: list[tuple[str, list[str]]]) -> None:
    assert named_args(build_steps(options, OLD_DLT)) == steps


@pytest.mark.parametrize(
    "options,steps",
    [
        pytest.param(InitOptions(), [("ai init", ["-v", "ai", "init"])], id="merge"),
        pytest.param(InitOptions(mode="skip"), [("ai init", ["-v", "ai", "init"])], id="skip"),
        pytest.param(
            InitOptions(mode="overwrite"),
            [("init", ["-v", "init", "--force"]), ("ai init", ["-v", "ai", "init"])],
            id="overwrite",
        ),
        pytest.param(InitOptions(dry_run=True), [], id="dry-run"),
    ],
)
def test_old_dlt_in_an_existing_workspace(options: InitOptions, steps: list[tuple[str, list[str]]]) -> None:
    assert named_args(build_steps(options, OLD_DLT, workspace_exists=True)) == steps


def test_has_workspace(tmp_path) -> None:
    assert not has_workspace(tmp_path)
    (tmp_path / ".dlt").mkdir()
    (tmp_path / ".dlt" / ".workspace").touch()
    assert has_workspace(tmp_path)


@pytest.mark.parametrize(
    "step,options,dlt_version,expected",
    [
        pytest.param(INIT, InitOptions(), NEW_DLT, "-y", id="merge-may-be-declined"),
        pytest.param(INIT, InitOptions(mode="overwrite"), NEW_DLT, "-y", id="overwrite-may-be-declined"),
        pytest.param(INIT, InitOptions(yes=True), NEW_DLT, None, id="yes-did-not-ask"),
        pytest.param(INIT, InitOptions(mode="skip"), NEW_DLT, None, id="skip-did-not-ask"),
        pytest.param(INIT, InitOptions(dry_run=True), NEW_DLT, None, id="dry-run-did-not-ask"),
        pytest.param(INIT, InitOptions(), OLD_DLT, None, id="old-init-never-asks"),
        pytest.param(
            DlthubStep("ai init", []),
            InitOptions(agent="codex"),
            OLD_DLT,
            "dlthub ai init --agent codex",
            id="ai-init-names-the-agent",
        ),
    ],
)
def test_failure_hint(step: DlthubStep, options: InitOptions, dlt_version: Version, expected: str | None) -> None:
    hint = get_failure_hint(step, options, dlt_version)
    if expected is None:
        assert hint is None
    else:
        assert expected in (hint or "")


def test_raise_on_failure() -> None:
    raise_on_failure(INIT, 0, InitOptions(), NEW_DLT)
    with pytest.raises(DlthubCommandError) as exc_info:
        raise_on_failure(INIT, 255, InitOptions(), NEW_DLT)
    assert exc_info.value.step == "init"
    assert exc_info.value.returncode == 255
    assert exc_info.value.hint is not None


def test_build_env_puts_uv_first_on_path() -> None:
    with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
        env = build_env(str(Path("/opt/uv/bin/uv")), telemetry_off=False)
        assert build_env(None, telemetry_off=False)["PATH"] == "/usr/bin"
    assert env["PATH"] == os.pathsep.join([str(Path("/opt/uv/bin")), "/usr/bin"])


def test_build_env_turns_dlt_telemetry_off() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert build_env(None, telemetry_off=True)["RUNTIME__DLTHUB_TELEMETRY"] == "false"
        assert "RUNTIME__DLTHUB_TELEMETRY" not in build_env(None, telemetry_off=False)


def test_build_env_drops_the_active_virtual_env() -> None:
    with patch.dict(os.environ, {"VIRTUAL_ENV": "/elsewhere/.venv"}, clear=True):
        assert "VIRTUAL_ENV" not in build_env(None, telemetry_off=False)


def test_find_dlthub_looks_next_to_the_interpreter(monkeypatch) -> None:
    which = MagicMock(return_value="/venv/bin/dlthub")
    monkeypatch.setattr(dlthub.sysconfig, "get_path", lambda _: "/venv/bin")
    monkeypatch.setattr(dlthub.shutil, "which", which)
    assert find_dlthub() == "/venv/bin/dlthub"
    which.assert_called_once_with("dlthub", path="/venv/bin")


def test_missing_dlthub_raises(monkeypatch) -> None:
    monkeypatch.setattr(dlthub.shutil, "which", lambda *args, **kwargs: None)
    with pytest.raises(WorkspaceError):
        find_dlthub()


def test_run_step_is_attached_to_the_terminal(monkeypatch) -> None:
    run = MagicMock(return_value=subprocess.CompletedProcess(args=[], returncode=3))
    monkeypatch.setattr(dlthub.subprocess, "run", run)
    step = DlthubStep("init", ["-v", "init", "--agent"])
    assert run_step("/venv/bin/dlthub", step, Path("/ws"), {"PATH": "/usr/bin"}) == 3
    assert run.call_args.args[0] == ["/venv/bin/dlthub", "-v", "init", "--agent"]
    kwargs = run.call_args.kwargs
    assert kwargs["cwd"] == Path("/ws")
    assert kwargs["env"] == {"PATH": "/usr/bin"}
    for captured in ("stdout", "stderr", "stdin", "capture_output"):
        assert captured not in kwargs


def test_run_step_start_failure_is_a_workspace_error(monkeypatch) -> None:
    monkeypatch.setattr(dlthub.subprocess, "run", MagicMock(side_effect=PermissionError("denied")))
    with pytest.raises(WorkspaceError):
        run_step("/venv/bin/dlthub", INIT, Path("/ws"), {})


def test_reads_installed_dlt_version(monkeypatch) -> None:
    monkeypatch.setattr(dlthub, "version", lambda _: "1.33.0a1")
    assert get_dlt_version() == Version("1.33.0a1")
