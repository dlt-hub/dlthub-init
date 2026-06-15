import unittest
from unittest.mock import patch

from dlthub_init import display
from dlthub_init.prompts import confirm


class ConfirmTest(unittest.TestCase):
    def setUp(self):
        display.console.quiet = True

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


if __name__ == "__main__":
    unittest.main()
