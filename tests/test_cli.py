import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dlthub_init.display as display
from dlthub_init.cli import main


class CliFilesOnlyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self._tmp.name) / "ws"
        display.console.quiet = True
        display.err_console.quiet = True

    def tearDown(self):
        self._tmp.cleanup()
        display.console.quiet = False
        display.err_console.quiet = False

    def run_cli(self, *extra):
        return main([str(self.project_dir), "--no-sync", *extra])

    def test_no_sync_scaffolds_files_and_exits_zero(self):
        self.assertEqual(self.run_cli(), 0)
        self.assertTrue((self.project_dir / "pyproject.toml").exists())
        self.assertTrue((self.project_dir / "uv.lock").exists())
        self.assertTrue((self.project_dir / ".dlt/config.toml").exists())

    def test_config_has_no_workspace_name(self):
        self.run_cli()
        config = (self.project_dir / ".dlt/config.toml").read_text(encoding="utf-8")
        self.assertNotIn("[workspace.settings]", config)

    def test_pyproject_name_stays_static(self):
        self.run_cli()
        pyproject = (self.project_dir / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "dlthub-workspace"', pyproject)

    def test_rerun_collides_with_exit_code_2(self):
        self.assertEqual(self.run_cli(), 0)
        self.assertEqual(self.run_cli(), 2)

    def test_no_pyproject_flag_skips_file(self):
        self.assertEqual(self.run_cli("--no-pyproject"), 0)
        self.assertFalse((self.project_dir / "pyproject.toml").exists())

    def test_force_preserves_secrets(self):
        self.run_cli()
        secrets = self.project_dir / ".dlt/secrets.toml"
        secrets.write_text("token = 'KEEP'\n", encoding="utf-8")
        self.assertEqual(self.run_cli("--force"), 0)
        self.assertIn("KEEP", secrets.read_text(encoding="utf-8"))

    def test_sync_path_invokes_uv_sync(self):
        with (
            patch("dlthub_init.cli.find_uv", return_value="/usr/bin/uv"),
            patch("dlthub_init.cli.run_uv_sync") as sync,
        ):
            self.assertEqual(main([str(self.project_dir), "--yes"]), 0)
        sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
