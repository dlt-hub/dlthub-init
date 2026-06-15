import tempfile
import unittest
from pathlib import Path

from dlthub_init.project_metadata import CONFIG_PATH, apply_workspace_name, normalize_project_name

CONFIG_TEMPLATE = """# config

[runtime]
log_level="WARNING"

[workspace.settings]
name = "dlthub-workspace"
"""


class NormalizeProjectNameTest(unittest.TestCase):
    def test_lowercases_and_dashes(self):
        self.assertEqual(normalize_project_name("My Workspace"), "my-workspace")

    def test_strips_special_chars(self):
        self.assertEqual(normalize_project_name("foo_bar.baz!"), "foo-bar-baz")

    def test_empty_falls_back(self):
        self.assertEqual(normalize_project_name("!!!"), "dlthub-workspace")


class ApplyWorkspaceNameTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_config(self, text=CONFIG_TEMPLATE):
        config = self.project_dir / CONFIG_PATH
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(text, encoding="utf-8")
        return config

    def test_rewrites_workspace_name(self):
        config = self._write_config()
        result = apply_workspace_name(self.project_dir, "My Cool WS")
        self.assertEqual(result, "my-cool-ws")
        self.assertIn('name = "my-cool-ws"', config.read_text(encoding="utf-8"))

    def test_leaves_other_sections_intact(self):
        config = self._write_config()
        apply_workspace_name(self.project_dir, "renamed")
        content = config.read_text(encoding="utf-8")
        self.assertIn('log_level="WARNING"', content)
        self.assertIn("[runtime]", content)

    def test_missing_config_returns_normalized_name(self):
        self.assertEqual(apply_workspace_name(self.project_dir, "no config"), "no-config")


if __name__ == "__main__":
    unittest.main()
