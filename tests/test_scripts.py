import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_skills  # noqa: E402
import update_skills  # noqa: E402


class SkillToolkitsTest(unittest.TestCase):
    def test_skill_toolkits_is_a_tuple(self):
        # A bare string iterates per-character in `for toolkit in toolkits`.
        self.assertIsInstance(generate_skills.SKILL_TOOLKITS, tuple)
        self.assertTrue(generate_skills.SKILL_TOOLKITS)


class SelectedToolkitsTest(unittest.TestCase):
    def test_default_when_env_unset(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(generate_skills._selected_toolkits(), generate_skills.SKILL_TOOLKITS)

    def test_env_override_parsed(self):
        with patch.dict("os.environ", {"DLTHUB_SKILL_TOOLKITS": "init, rest-api-pipeline ,, transformations"}):
            self.assertEqual(
                generate_skills._selected_toolkits(),
                ("init", "rest-api-pipeline", "transformations"),
            )


class PinFullRefTest(unittest.TestCase):
    def test_rewrites_full_ref_line(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write('WORKBENCH_REF_SHORT = "old1234"\nWORKBENCH_REF = "old1234old1234"\n')
            script = Path(fh.name)
        self.addCleanup(script.unlink)
        new_full = "a" * 40
        with patch.object(generate_skills, "SCRIPT_PATH", script), contextlib.redirect_stdout(io.StringIO()):
            generate_skills._pin_full_ref(new_full)
        content = script.read_text(encoding="utf-8")
        self.assertIn(f'WORKBENCH_REF = "{new_full}"', content)
        self.assertIn('WORKBENCH_REF_SHORT = "old1234"', content)  # short line untouched


class CopyToolkitSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills_dir = self.root / "out"
        self.skills_dir.mkdir()
        self.workbench = self.root / "wb"

    def tearDown(self):
        self._tmp.cleanup()

    def _make(self, toolkit, skill):
        d = self.workbench / "workbench" / toolkit / "skills" / skill
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {skill}\n", encoding="utf-8")

    def test_copies_selected_toolkit_skills(self):
        self._make("init", "router")
        self._make("rest-api-pipeline", "find-source")
        with patch.object(generate_skills, "SKILLS_DIR", self.skills_dir):
            collected = generate_skills._copy_toolkit_skills(self.workbench, ("init", "rest-api-pipeline"))
        self.assertEqual(set(collected), {"router", "find-source"})
        self.assertTrue((self.skills_dir / "router" / "SKILL.md").exists())

    def test_duplicate_skill_name_raises(self):
        self._make("init", "dup")
        self._make("rest-api-pipeline", "dup")
        with patch.object(generate_skills, "SKILLS_DIR", self.skills_dir):
            with self.assertRaises(SystemExit):
                generate_skills._copy_toolkit_skills(self.workbench, ("init", "rest-api-pipeline"))

    def test_missing_toolkit_raises(self):
        with patch.object(generate_skills, "SKILLS_DIR", self.skills_dir):
            with self.assertRaises(SystemExit):
                generate_skills._copy_toolkit_skills(self.workbench, ("nope",))


class ResolveShortTest(unittest.TestCase):
    def test_full_sha_truncated_to_seven(self):
        self.assertEqual(update_skills._resolve_short("0123456789abcdef0123"), "0123456")

    def test_short_sha_passthrough(self):
        self.assertEqual(update_skills._resolve_short("abc1234"), "abc1234")


class WriteShortTest(unittest.TestCase):
    def test_rewrites_short_ref_line(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write('WORKBENCH_REF_SHORT = "old1234"\nWORKBENCH_REF = "old1234old1234"\n')
            script = Path(fh.name)
        self.addCleanup(script.unlink)
        with patch.object(update_skills, "GENERATE_SCRIPT", script):
            update_skills._write_short("new5678")
        content = script.read_text(encoding="utf-8")
        self.assertIn('WORKBENCH_REF_SHORT = "new5678"', content)
        self.assertIn('WORKBENCH_REF = "old1234old1234"', content)  # full line untouched


if __name__ == "__main__":
    unittest.main()
