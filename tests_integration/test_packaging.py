import subprocess
import zipfile
from pathlib import Path

import pytest

from dlthub_init.uv import find_uv

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_wheel_ships_code_only(tmp_path) -> None:
    uv = find_uv()
    if uv is None:
        pytest.skip("uv is not installed")
    subprocess.run([uv, "build", "--wheel", "--out-dir", str(tmp_path)], cwd=REPO_ROOT, check=True, capture_output=True)
    with zipfile.ZipFile(next(tmp_path.glob("*.whl"))) as archive:
        shipped = [name for name in archive.namelist() if name.startswith("dlthub_init/")]

    assert "dlthub_init/dlthub.py" in shipped
    assert [name for name in shipped if not name.endswith(".py")] == []
