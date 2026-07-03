import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dlthub_init.hooks as hooks


class InstallHooksTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.project_dir = root / "ws"
        self.project_dir.mkdir()
        self.source = root / "src_hooks"
        self.source.mkdir()
        (self.source / "secrets_guard.py").write_text("# guard\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _install(self):
        with patch("dlthub_init.hooks.hooks_source", return_value=self.source):
            return hooks.install_hooks(self.project_dir)

    def _read_json(self, rel):
        return json.loads((self.project_dir / rel).read_text(encoding="utf-8"))

    def test_copies_script_into_agents_hooks(self):
        self._install()
        self.assertTrue((self.project_dir / ".agents/hooks/secrets_guard.py").exists())

    def test_configures_all_three_agents(self):
        configured = self._install()
        self.assertEqual(configured, ["claude", "cursor", "codex"])

        claude = self._read_json(".claude/settings.json")
        self.assertEqual(claude["hooks"]["PreToolUse"][0]["matcher"], "Read|Grep|Bash")
        self.assertIn("$CLAUDE_PROJECT_DIR", claude["hooks"]["PreToolUse"][0]["hooks"][0]["command"])

        cursor = self._read_json(".cursor/hooks.json")
        self.assertEqual(cursor["version"], 1)
        for event in ("beforeReadFile", "beforeShellExecution"):
            self.assertIn("secrets_guard.py", cursor["hooks"][event][0]["command"])

        codex = self._read_json(".codex/hooks.json")
        self.assertEqual(codex["hooks"]["PreToolUse"][0]["matcher"], "Bash")
        self.assertIn("secrets_guard.py", codex["hooks"]["PreToolUse"][0]["hooks"][0]["command"])

    def test_merges_into_existing_claude_settings(self):
        settings_path = self.project_dir / ".claude/settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps({"permissions": {"allow": ["Bash(ls *)"]}}), encoding="utf-8")
        self._install()
        merged = self._read_json(".claude/settings.json")
        self.assertEqual(merged["permissions"]["allow"], ["Bash(ls *)"])
        self.assertIn("secrets_guard.py", json.dumps(merged["hooks"]))

    def test_skips_agents_already_configured(self):
        first = self._install()
        second = self._install()
        self.assertEqual(first, ["claude", "cursor", "codex"])
        self.assertEqual(second, [])
        claude = self._read_json(".claude/settings.json")
        self.assertEqual(len(claude["hooks"]["PreToolUse"]), 1)

    def test_leaves_invalid_json_untouched(self):
        settings_path = self.project_dir / ".claude/settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text("{not json", encoding="utf-8")
        configured = self._install()
        self.assertEqual(configured, ["cursor", "codex"])
        self.assertEqual(settings_path.read_text(encoding="utf-8"), "{not json")

    def test_never_overwrites_existing_script(self):
        dest = self.project_dir / ".agents/hooks/secrets_guard.py"
        dest.parent.mkdir(parents=True)
        dest.write_text("USER OWNED", encoding="utf-8")
        self._install()
        self.assertEqual(dest.read_text(encoding="utf-8"), "USER OWNED")

    def test_no_source_returns_empty(self):
        with patch("dlthub_init.hooks.hooks_source", return_value=None):
            self.assertEqual(hooks.install_hooks(self.project_dir), [])


class HooksSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.bundled = self.root / "bundled"
        self.source = self.root / "source"

    def tearDown(self):
        self._tmp.cleanup()

    def _resolve(self):
        with (
            patch.object(hooks, "_BUNDLED_HOOKS", self.bundled),
            patch.object(hooks, "_SOURCE_HOOKS", self.source),
        ):
            return hooks.hooks_source()

    def test_prefers_bundled(self):
        self.bundled.mkdir()
        self.source.mkdir()
        self.assertEqual(self._resolve(), self.bundled)

    def test_falls_back_to_source(self):
        self.source.mkdir()
        self.assertEqual(self._resolve(), self.source)

    def test_none_when_neither_exists(self):
        self.assertIsNone(self._resolve())


if __name__ == "__main__":
    unittest.main()
