import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dlthub_init.skills as skills


class InstallSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.project_dir = root / "ws"
        self.project_dir.mkdir()
        self.source = root / "src_skills"
        self._make_skill("foo")
        self._make_skill("bar")

    def tearDown(self):
        self._tmp.cleanup()

    def _make_skill(self, name):
        skill = self.source / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")

    def _install(self):
        with patch("dlthub_init.skills.skills_source", return_value=self.source):
            return skills.install_skills(self.project_dir)

    def test_copies_into_agents_skills(self):
        created = self._install()
        self.assertEqual(set(created), {"foo", "bar"})
        self.assertTrue((self.project_dir / ".agents/skills/foo/SKILL.md").exists())
        self.assertTrue((self.project_dir / ".agents/skills/bar/SKILL.md").exists())

    def test_links_into_claude_skills(self):
        self._install()
        link = self.project_dir / ".claude/skills/foo"
        self.assertTrue(os.path.lexists(link))
        self.assertTrue((link / "SKILL.md").exists())

    @unittest.skipIf(sys.platform == "win32", "POSIX symlink semantics")
    def test_claude_link_is_relative_symlink(self):
        self._install()
        link = self.project_dir / ".claude/skills/foo"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), os.path.join("..", "..", ".agents", "skills", "foo"))

    def test_skips_existing_agents_skill(self):
        dest = self.project_dir / ".agents/skills/foo"
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("USER OWNED", encoding="utf-8")
        created = self._install()
        self.assertNotIn("foo", created)
        self.assertEqual((dest / "SKILL.md").read_text(encoding="utf-8"), "USER OWNED")

    def test_skips_existing_claude_link(self):
        existing = self.project_dir / ".claude/skills/foo"
        existing.mkdir(parents=True)
        self._install()
        self.assertTrue(existing.is_dir())

    def test_no_source_returns_empty(self):
        with patch("dlthub_init.skills.skills_source", return_value=None):
            self.assertEqual(skills.install_skills(self.project_dir), [])

    def test_copies_when_symlink_unavailable(self):
        with patch("dlthub_init.skills.os.symlink", side_effect=OSError("no symlinks")):
            self._install()
        link = self.project_dir / ".claude/skills/foo"
        self.assertFalse(link.is_symlink())
        self.assertTrue((link / "SKILL.md").exists())


class SkillsSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.bundled = self.root / "bundled"
        self.source = self.root / "source"

    def tearDown(self):
        self._tmp.cleanup()

    def _resolve(self):
        with (
            patch.object(skills, "_BUNDLED_SKILLS", self.bundled),
            patch.object(skills, "_SOURCE_SKILLS", self.source),
        ):
            return skills.skills_source()

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
