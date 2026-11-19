import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import dlthub_init.uv as uv
from dlthub_init.errors import UvError


def test_isolated_env_drops_venv_hints() -> None:
    with patch.dict(
        os.environ, {"VIRTUAL_ENV": "/a", "CONDA_PREFIX": "/b", "PYTHONPATH": "/c", "PATH": "/x"}, clear=True
    ):
        assert uv.isolated_project_env() == {"PATH": "/x"}


def test_find_uv_prefers_the_uv_that_runs_us(monkeypatch) -> None:
    monkeypatch.setenv("UV", "/uvx/uv")
    monkeypatch.setattr(uv.shutil, "which", lambda _: "/usr/bin/uv")
    assert uv.find_uv() == "/uvx/uv"


@pytest.mark.parametrize("on_path", [pytest.param("/usr/bin/uv", id="on-path"), pytest.param(None, id="missing")])
def test_find_uv_falls_back_to_path(monkeypatch, on_path) -> None:
    monkeypatch.delenv("UV", raising=False)
    monkeypatch.setattr(uv.shutil, "which", lambda _: on_path)
    assert uv.find_uv() == on_path


def test_failed_sync_carries_uv_output(monkeypatch) -> None:
    failed = subprocess.CalledProcessError(1, ["uv", "sync"], output=b"out", stderr=b"[resolution] failed")
    monkeypatch.setattr(uv.subprocess, "run", MagicMock(side_effect=failed))
    with pytest.raises(UvError, match=r"exit code 1: uv sync\n\n\[resolution\] failed\n\nout"):
        uv.run_uv_sync("uv", Path("/ws"))
