from pathlib import Path

import dlthub_init.display as display
from dlthub_init.errors import DlthubCommandError, UvError


def test_single_next_step_in_place_when_synced(render) -> None:
    _, out = render(lambda: display.print_next_steps(Path.cwd(), sync_pending=False))
    assert "Next step" in out
    assert "Next steps" not in out
    assert "1." not in out
    assert "cd " not in out
    assert "coding agent" in out


def test_numbered_next_steps_for_a_subdir(render) -> None:
    _, out = render(lambda: display.print_next_steps(Path.cwd() / "sub", sync_pending=True))
    assert "Next steps" in out
    assert "1." in out
    assert "2." in out
    assert "uv sync" in out


def test_command_failed_with_hint(render) -> None:
    _, out = render(lambda: display.print_command_failed(DlthubCommandError("init", 255, hint="re-run with -y")))
    assert "dlthub init failed (exit 255)" in out
    assert "re-run with -y" in out


def test_sync_failed_keeps_brackets_of_uv_output(render) -> None:
    _, out = render(lambda: display.print_sync_failed(UvError("[project] is missing")))
    assert "[project] is missing" in out


def test_cwd_is_displayed_as_dot() -> None:
    assert display._display_path(Path.cwd()) == "."
