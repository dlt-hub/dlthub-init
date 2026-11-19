from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from packaging.version import Version

from dlthub_init.cli import build_parser, main
from dlthub_init.errors import UvError


@pytest.fixture
def cli(tmp_path, monkeypatch, render):
    mocks = SimpleNamespace(
        project_dir=tmp_path / "ws",
        dlt_version=MagicMock(return_value=Version("1.33.0")),
        returncodes=[],
        dependency_file="pyproject.toml",
        sync=MagicMock(),
        build_env=MagicMock(return_value={}),
    )

    def run_step(dlthub: str, step, project_dir: Path, env) -> int:
        # dlthub writes the dependency file
        (project_dir / mocks.dependency_file).touch()
        return mocks.returncodes.pop(0) if mocks.returncodes else 0

    mocks.run_step = MagicMock(side_effect=run_step)
    mocks.run = lambda *extra: render(lambda: main([str(mocks.project_dir), *extra]))
    monkeypatch.setattr("dlthub_init.cli.get_dlt_version", mocks.dlt_version)
    monkeypatch.setattr("dlthub_init.cli.find_dlthub", lambda: "/venv/bin/dlthub")
    monkeypatch.setattr("dlthub_init.cli.find_uv", lambda: "/usr/bin/uv")
    monkeypatch.setattr("dlthub_init.cli.build_env", mocks.build_env)
    monkeypatch.setattr("dlthub_init.cli.run_step", mocks.run_step)
    monkeypatch.setattr("dlthub_init.cli.run_uv_sync", mocks.sync)
    return mocks


def step_args(cli) -> list[list[str]]:
    return [call.args[1].args for call in cli.run_step.call_args_list]


def test_creates_the_dir_runs_init_and_syncs(cli) -> None:
    code, out = cli.run()
    assert code == 0
    assert cli.project_dir.is_dir()
    assert step_args(cli) == [["-v", "init", "--agent"]]
    assert cli.run_step.call_args.args[2] == cli.project_dir.resolve()
    cli.sync.assert_called_once()
    assert "dlt 1.33.0" in out
    assert "Start a new session of your coding agent" in out


def test_passes_the_init_arguments(cli) -> None:
    cli.run("--name", "ws1", "--dependencies", "pyproject", "--agent", "cursor", "-y")
    assert step_args(cli) == [["-v", "-y", "init", "--name", "ws1", "--dependencies", "pyproject", "--agent", "cursor"]]


def test_force_is_overwrite(cli) -> None:
    cli.run("--force")
    assert "--overwrite" in step_args(cli)[0]


def test_overwrite_and_skip_exclude_each_other() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--overwrite", "--skip"])


def test_agent_never_takes_the_directory() -> None:
    args = build_parser().parse_args(["--agent", "claude", "my-ws"])
    assert (args.agent, args.project_dir) == ("claude", "my-ws")
    with pytest.raises(SystemExit):
        build_parser().parse_args(["my-ws", "--agent"])


def test_dry_run_does_not_sync(cli) -> None:
    code, out = cli.run("--dry-run")
    assert code == 0
    cli.sync.assert_not_called()
    assert "Next step" not in out


def test_no_sync_lists_uv_sync_as_next_step(cli) -> None:
    code, out = cli.run("--no-sync")
    assert code == 0
    cli.sync.assert_not_called()
    assert "uv sync" in out


def test_requirements_workspace_is_not_synced(cli) -> None:
    cli.dependency_file = "requirements.txt"
    code, out = cli.run("--dependencies", "requirements")
    assert code == 0
    cli.sync.assert_not_called()
    assert "uv sync" not in out


def test_failed_init_returns_its_exit_code_with_a_hint(cli) -> None:
    cli.returncodes = [255]
    code, out = cli.run()
    assert code == 255
    cli.sync.assert_not_called()
    assert "dlthub init failed (exit 255)" in out
    assert "-y" in out


def test_killed_init_returns_one(cli) -> None:
    cli.returncodes = [-9]
    code, _ = cli.run()
    assert code == 1


def test_old_dlt_runs_ai_init(cli) -> None:
    cli.dlt_version.return_value = Version("1.32.0")
    code, _ = cli.run("--agent", "claude")
    assert code == 0
    assert step_args(cli) == [["-v", "init"], ["-v", "ai", "init", "--agent", "claude"]]


def test_old_dlt_sets_up_only_the_agent_in_an_existing_workspace(cli) -> None:
    cli.dlt_version.return_value = Version("1.32.0")
    (cli.project_dir / ".dlt").mkdir(parents=True)
    (cli.project_dir / ".dlt" / ".workspace").touch()
    code, _ = cli.run()
    assert code == 0
    assert step_args(cli) == [["-v", "ai", "init"]]
    cli.sync.assert_called_once()


def test_old_dlt_ai_init_failure_says_how_to_finish(cli) -> None:
    cli.dlt_version.return_value = Version("1.32.0")
    cli.returncodes = [0, 1]
    code, out = cli.run()
    assert code == 1
    assert "dlthub ai init failed (exit 1)" in out
    assert "uv run dlthub ai init --agent" in out


def test_failed_sync_still_succeeds_and_shows_uv_output(cli) -> None:
    cli.sync.side_effect = UvError("Command failed with exit code 1: uv sync\n\n[resolution] failed")
    code, out = cli.run()
    assert code == 0
    assert "[resolution] failed" in out
    assert "Install dependencies" in out


@pytest.mark.parametrize(
    "flag,telemetry_off",
    [pytest.param("--no-telemetry", True, id="no-telemetry"), pytest.param("--no-sync", False, id="telemetry-on")],
)
def test_no_telemetry_turns_dlt_telemetry_off(cli, flag: str, telemetry_off: bool) -> None:
    cli.run(flag)
    assert cli.build_env.call_args.kwargs["telemetry_off"] is telemetry_off
