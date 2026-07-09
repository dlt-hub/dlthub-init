import unittest
from unittest.mock import patch

import dlthub_init.display as display
from dlthub_init.prompts import confirm


class ConfirmTest(unittest.TestCase):
    def setUp(self):
        display.console.quiet = True
        interactive = patch("dlthub_init.prompts.stdin_is_interactive", return_value=True)
        interactive.start()
        self.addCleanup(interactive.stop)

    def tearDown(self):
        display.console.quiet = False

    @patch("dlthub_init.prompts.beaupy.select", return_value="Yes")
    def test_yes(self, _select):
        self.assertTrue(confirm("Proceed?"))

    @patch("dlthub_init.prompts.beaupy.select", return_value="No")
    def test_no(self, _select):
        self.assertFalse(confirm("Proceed?"))

    @patch("dlthub_init.prompts.beaupy.select", return_value="Yes")
    def test_default_controls_initial_cursor(self, select):
        confirm("Proceed?", default=False)
        self.assertEqual(select.call_args.kwargs["cursor_index"], 1)


class NonInteractiveConfirmTest(unittest.TestCase):
    def setUp(self):
        display.console.quiet = True
        non_interactive = patch("dlthub_init.prompts.stdin_is_interactive", return_value=False)
        non_interactive.start()
        self.addCleanup(non_interactive.stop)

    def tearDown(self):
        display.console.quiet = False

    @patch("dlthub_init.prompts.beaupy.select")
    def test_returns_default_without_prompting(self, select):
        self.assertTrue(confirm("Proceed?", default=True))
        self.assertFalse(confirm("Proceed?", default=False))
        select.assert_not_called()


if __name__ == "__main__":
    unittest.main()
