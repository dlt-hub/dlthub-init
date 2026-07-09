import re
import unittest
from pathlib import Path

import dlthub_init.display as display
from dlthub_init.collisions import Outcome, PlannedPath

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _capture(render) -> str:
    """Run a print function and return its output with ANSI styling stripped.

    rich emits color codes when stdout is a TTY (e.g. `make` in a terminal) but
    not when piped, so assertions must be style-agnostic.
    """
    with display.console.capture() as capture:
        render()
    return _ANSI.sub("", capture.get())


class PrintSummaryTest(unittest.TestCase):
    def _render(self, plan):
        return _capture(lambda: display.print_summary(plan))

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


class NextStepsTest(unittest.TestCase):
    def _render(self, project_dir, *, synced, uv_installed=True, interactive=True, skills_available=False):
        return _capture(
            lambda: display.print_next_steps(
                project_dir,
                synced=synced,
                uv_installed=uv_installed,
                interactive=interactive,
                skills_available=skills_available,
            )
        )

    def test_single_step_in_place_synced(self):
        out = self._render(Path.cwd(), synced=True)
        self.assertIn("Next step", out)
        self.assertNotIn("Next steps", out)
        self.assertNotIn("1.", out)
        self.assertNotIn("cd ", out)

    def test_multiple_steps_numbered_for_subdir(self):
        out = self._render(Path.cwd() / "sub", synced=False)
        self.assertIn("Next steps", out)
        self.assertIn("1.", out)
        self.assertIn("2.", out)
        self.assertIn("uv sync", out)

    def test_interactive_points_at_coding_agent(self):
        out = self._render(Path.cwd(), synced=True, interactive=True, skills_available=True)
        self.assertIn("Open your coding agent", out)
        self.assertNotIn(".agents/skills", out)

    def test_non_interactive_points_at_skills(self):
        out = self._render(Path.cwd(), synced=True, interactive=False, skills_available=True)
        self.assertIn(".agents/skills", out)
        self.assertNotIn("Open your coding agent", out)

    def test_non_interactive_without_skills_falls_back(self):
        out = self._render(Path.cwd(), synced=True, interactive=False, skills_available=False)
        self.assertIn("Open your coding agent", out)


class DisplayPathTest(unittest.TestCase):
    def test_cwd_is_dot(self):
        self.assertEqual(display._display_path(Path.cwd()), ".")


if __name__ == "__main__":
    unittest.main()
