import tempfile
import unittest
from pathlib import Path

from dlthub_init.collisions import Flags, Outcome, build_plan, conflicts

PYPROJECT = Path("pyproject.toml")
GITIGNORE = Path(".gitignore")
SECRETS = Path(".dlt/secrets.toml")
CONFIG = Path(".dlt/config.toml")
LOCK = Path("uv.lock")
WORKSPACE = Path(".dlt/.workspace")

ALL_PATHS = [PYPROJECT, GITIGNORE, SECRETS, CONFIG, LOCK, WORKSPACE]


def outcome_for(plan, relative):
    return next(p.outcome for p in plan if p.relative == relative)


class CollisionPlanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, relative):
        target = self.project_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("existing", encoding="utf-8")

    def plan(self, flags=Flags()):
        return build_plan(ALL_PATHS, self.project_dir, flags)

    def test_empty_dir_creates_everything(self):
        plan = self.plan()
        self.assertTrue(all(p.outcome is Outcome.CREATE for p in plan))
        self.assertEqual(conflicts(plan), [])

    def test_only_workspace_marker_conflicts(self):
        self._touch(WORKSPACE)
        plan = self.plan()
        self.assertIs(outcome_for(plan, WORKSPACE), Outcome.CONFLICT)
        self.assertEqual(conflicts(plan), [str(WORKSPACE)])

    def test_existing_pyproject_and_config_are_skipped_not_conflict(self):
        self._touch(PYPROJECT)
        self._touch(CONFIG)
        plan = self.plan()
        self.assertIs(outcome_for(plan, PYPROJECT), Outcome.SKIP)
        self.assertIs(outcome_for(plan, CONFIG), Outcome.SKIP)
        self.assertEqual(conflicts(plan), [])

    def test_force_overwrites_generated_files(self):
        self._touch(PYPROJECT)
        self._touch(WORKSPACE)
        plan = self.plan(Flags(force=True))
        self.assertIs(outcome_for(plan, PYPROJECT), Outcome.OVERWRITE)
        self.assertIs(outcome_for(plan, WORKSPACE), Outcome.OVERWRITE)
        self.assertEqual(conflicts(plan), [])

    def test_lock_dropped_when_pyproject_skipped_and_absent(self):
        self._touch(PYPROJECT)
        plan = self.plan()
        self.assertIs(outcome_for(plan, PYPROJECT), Outcome.SKIP)
        self.assertNotIn(LOCK, [p.relative for p in plan])

    def test_existing_lock_preserved_when_pyproject_skipped(self):
        self._touch(PYPROJECT)
        self._touch(LOCK)
        self.assertIs(outcome_for(self.plan(), LOCK), Outcome.SKIP)

    def test_lock_created_with_pyproject_in_empty_dir(self):
        plan = self.plan()
        self.assertIs(outcome_for(plan, PYPROJECT), Outcome.CREATE)
        self.assertIs(outcome_for(plan, LOCK), Outcome.CREATE)

    def test_lock_dropped_with_no_pyproject_flag(self):
        plan = self.plan(Flags(no_pyproject=True))
        self.assertIs(outcome_for(plan, PYPROJECT), Outcome.DISABLED)
        self.assertNotIn(LOCK, [p.relative for p in plan])

    def test_existing_secret_is_skipped_not_conflict(self):
        self._touch(SECRETS)
        self.assertIs(outcome_for(self.plan(), SECRETS), Outcome.SKIP)

    def test_force_never_overwrites_secret(self):
        self._touch(SECRETS)
        self.assertIs(outcome_for(self.plan(Flags(force=True)), SECRETS), Outcome.SKIP)

    def test_existing_gitignore_skipped_without_merge(self):
        self._touch(GITIGNORE)
        self.assertIs(outcome_for(self.plan(), GITIGNORE), Outcome.SKIP)

    def test_existing_gitignore_merges_with_flag(self):
        self._touch(GITIGNORE)
        self.assertIs(outcome_for(self.plan(Flags(merge=True)), GITIGNORE), Outcome.MERGE)

    def test_no_pyproject_flag_disables(self):
        plan = self.plan(Flags(no_pyproject=True))
        self.assertIs(outcome_for(plan, PYPROJECT), Outcome.DISABLED)

    def test_no_gitignore_flag_disables_even_when_present(self):
        self._touch(GITIGNORE)
        plan = self.plan(Flags(no_gitignore=True))
        self.assertIs(outcome_for(plan, GITIGNORE), Outcome.DISABLED)


if __name__ == "__main__":
    unittest.main()
