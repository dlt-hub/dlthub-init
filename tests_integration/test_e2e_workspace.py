import tomllib

import pytest

from dlthub_init.cli import main
from dlthub_init.dlthub import get_dlt_version, has_agent_init
from dlthub_init.uv import find_uv

pytestmark = pytest.mark.skipif(find_uv() is None, reason="uv is not installed")

MERGES = has_agent_init(get_dlt_version())


@pytest.fixture
def existing_project(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "pyproject.toml").write_text(
        '[project]\nname = "project"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = ["requests"]\n',
        encoding="utf-8",
    )
    (project_dir / ".gitignore").write_text("notes/\n", encoding="utf-8")
    return project_dir


def test_creates_workspace_sets_up_agent_and_syncs(tmp_path) -> None:
    """Runs the real `dlthub init` of the installed dlt, fetches the AI harness and syncs."""
    project_dir = tmp_path / "ws"
    assert main([str(project_dir), "--agent", "claude", "--no-telemetry"]) == 0
    assert (project_dir / ".dlt" / ".workspace").exists()
    assert (project_dir / "pyproject.toml").exists()
    assert (project_dir / ".claude" / "skills").is_dir()
    assert (project_dir / ".mcp.json").exists()
    assert (project_dir / ".venv" / "pyvenv.cfg").exists()


def test_dry_run_writes_nothing(tmp_path) -> None:
    project_dir = tmp_path / "ws"
    assert main([str(project_dir), "--agent", "claude", "--dry-run", "--no-telemetry"]) == 0
    assert list(project_dir.iterdir()) == []


@pytest.mark.skipif(not MERGES, reason="this dlt cannot merge into existing projects")
def test_merges_into_an_existing_project(existing_project) -> None:
    assert main([str(existing_project), "--agent", "claude", "-y", "--no-sync", "--no-telemetry"]) == 0
    dependencies = tomllib.loads((existing_project / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    assert "requests" in dependencies
    assert any(dependency.startswith("dlt") for dependency in dependencies)
    gitignore = (existing_project / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "notes/" in gitignore
    assert len(gitignore) > 1
    assert (existing_project / ".dlt" / ".workspace").exists()
    assert (existing_project / ".claude" / "skills").is_dir()


@pytest.mark.skipif(MERGES, reason="this dlt merges into existing projects")
def test_keeps_existing_files_on_older_dlt(existing_project) -> None:
    pyproject = (existing_project / "pyproject.toml").read_text(encoding="utf-8")
    gitignore = (existing_project / ".gitignore").read_text(encoding="utf-8")
    assert main([str(existing_project), "--agent", "claude", "--no-sync", "--no-telemetry"]) == 0
    assert (existing_project / "pyproject.toml").read_text(encoding="utf-8") == pyproject
    assert (existing_project / ".gitignore").read_text(encoding="utf-8") == gitignore
    assert (existing_project / ".dlt" / ".workspace").exists()
    assert (existing_project / ".claude" / "skills").is_dir()
