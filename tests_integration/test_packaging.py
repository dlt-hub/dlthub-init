import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from dlthub_init.scaffold import enumerate_payload
from dlthub_init.uv import find_uv

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = "minimal_workspace"
WHEEL_SCAFFOLD_DIR = f"dlthub_init/scaffolds/{SCAFFOLD}"


class WheelPayloadTest(unittest.TestCase):
    # enumerate_payload walks the source tree, so every other test passes even when
    # the build drops a payload file. Most of the payload is dotfiles, which build
    # backends are prone to exclude silently.
    def test_wheel_ships_every_scaffold_file(self):
        uv = find_uv()
        if uv is None:
            self.skipTest("uv is not installed")
        with tempfile.TemporaryDirectory() as out_dir:
            subprocess.run(
                [uv, "build", "--wheel", "--out-dir", out_dir],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
            )
            wheel = next(Path(out_dir).glob("*.whl"))
            with zipfile.ZipFile(wheel) as archive:
                shipped = set(archive.namelist())

        expected = {f"{WHEEL_SCAFFOLD_DIR}/{relative.as_posix()}" for relative in enumerate_payload(SCAFFOLD)}
        self.assertEqual(sorted(expected - shipped), [])


if __name__ == "__main__":
    unittest.main()
