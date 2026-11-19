import pytest

from dlthub_init.cli import main
from dlthub_init.uv import find_uv

pytestmark = pytest.mark.skipif(find_uv() is None, reason="uv is not installed")


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
