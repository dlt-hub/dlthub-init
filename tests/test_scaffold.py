import tempfile
import unittest
from pathlib import Path

from dlthub_init.collisions import Flags
from dlthub_init.errors import CollisionError, ScaffoldError
from dlthub_init.scaffold import apply_scaffold, enumerate_payload, resolve_target, validate_scaffold_name

SCAFFOLD = "minimal_workspace"
EXPECTED = {
    Path("pyproject.toml"),
    Path(".gitignore"),
    Path("uv.lock"),
    Path(".python-version"),
    Path("__deployment__.py"),
    Path(".dlt/.workspace"),
    Path(".dlt/config.toml"),
    Path(".dlt/secrets.toml"),
}


class EnumeratePayloadTest(unittest.TestCase):
    def test_payload_matches_expected_files(self):
        self.assertEqual(set(enumerate_payload(SCAFFOLD)), EXPECTED)

    def test_payload_has_no_agent_or_toolkit_artifacts(self):
        relatives = set(enumerate_payload(SCAFFOLD))
        self.assertFalse(any("_agents" in p.parts for p in relatives))
        self.assertNotIn(Path(".dlt/.toolkits"), relatives)
        self.assertFalse(any(p.name == "pipeline.py" for p in relatives))


class ValidateScaffoldNameTest(unittest.TestCase):
    def test_unknown_scaffold_raises(self):
        with self.assertRaises(ScaffoldError):
            validate_scaffold_name("does_not_exist")

    def test_known_scaffold_ok(self):
        validate_scaffold_name(SCAFFOLD)


class ApplyScaffoldTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_all_payload_files(self):
        apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())
        for relative in EXPECTED:
            self.assertTrue((self.project_dir / relative).exists(), relative)

    def test_pyproject_name_is_static(self):
        apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())
        content = (self.project_dir / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "dlthub-workspace"', content)

    def test_second_run_raises_collision(self):
        apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())
        with self.assertRaises(CollisionError):
            apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())

    def test_collision_leaves_user_file_untouched(self):
        apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())
        edited = self.project_dir / "pyproject.toml"
        edited.write_text("USER OWNED", encoding="utf-8")
        with self.assertRaises(CollisionError):
            apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())
        self.assertEqual(edited.read_text(encoding="utf-8"), "USER OWNED")

    def test_existing_pyproject_does_not_block_and_skips_lock(self):
        existing = self.project_dir / "pyproject.toml"
        existing.write_text("USER OWNED", encoding="utf-8")
        apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags())
        self.assertEqual(existing.read_text(encoding="utf-8"), "USER OWNED")
        self.assertFalse((self.project_dir / "uv.lock").exists())
        self.assertTrue((self.project_dir / ".dlt/.workspace").exists())

    def test_merge_appends_missing_gitignore_entries(self):
        gitignore = self.project_dir / ".gitignore"
        gitignore.write_text("custom-rule/\n", encoding="utf-8")
        apply_scaffold(self.project_dir, scaffold=SCAFFOLD, flags=Flags(force=True, merge=True))
        merged = gitignore.read_text(encoding="utf-8")
        self.assertIn("custom-rule/", merged)
        self.assertIn("*.duckdb", merged)


class ResolveTargetTest(unittest.TestCase):
    def test_default_is_cwd(self):
        self.assertEqual(resolve_target(None), Path.cwd().resolve())

    def test_explicit_arg_resolved(self):
        self.assertEqual(resolve_target("some/where"), (Path.cwd() / "some/where").resolve())


if __name__ == "__main__":
    unittest.main()
