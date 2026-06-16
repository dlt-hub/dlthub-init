import tempfile
import unittest
from pathlib import Path

from dlthub_init.cli import main
from dlthub_init.uv import find_uv


@unittest.skipIf(find_uv() is None, "uv is not installed")
class EndToEndWorkspaceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self._tmp.name) / "ws"

    def tearDown(self):
        self._tmp.cleanup()

    def test_yes_scaffolds_and_syncs(self):
        self.assertEqual(main([str(self.project_dir), "--yes"]), 0)
        self.assertTrue((self.project_dir / "pyproject.toml").exists())
        self.assertTrue((self.project_dir / ".venv" / "pyvenv.cfg").exists())
        self.assertTrue((self.project_dir / ".agents" / "skills").is_dir())


if __name__ == "__main__":
    unittest.main()
