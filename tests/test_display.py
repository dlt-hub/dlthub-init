import unittest
from pathlib import Path

from dlthub_init import display
from dlthub_init.collisions import Outcome, PlannedPath


class PrintSummaryTest(unittest.TestCase):
    def _render(self, plan):
        with display.console.capture() as capture:
            display.print_summary(plan)
        return capture.get()

    def test_groups_by_outcome(self):
        plan = [
            PlannedPath(Path("pyproject.toml"), Outcome.CREATE),
            PlannedPath(Path(".dlt/secrets.toml"), Outcome.SKIP),
            PlannedPath(Path(".gitignore"), Outcome.DISABLED),
        ]
        out = self._render(plan)
        self.assertIn("Created", out)
        self.assertIn("pyproject.toml", out)
        self.assertIn("already exist", out)
        self.assertIn("disabled by flag", out)

    def test_nothing_written_message_for_empty_plan(self):
        self.assertIn("nothing", self._render([]).lower())


class DisplayPathTest(unittest.TestCase):
    def test_cwd_is_dot(self):
        self.assertEqual(display._display_path(Path.cwd()), ".")


if __name__ == "__main__":
    unittest.main()
