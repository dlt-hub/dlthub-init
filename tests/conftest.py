import re
from typing import Callable, TypeVar

import pytest

import dlthub_init.display as display
from dlthub_init import telemetry

T = TypeVar("T")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(autouse=True)
def no_telemetry_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a PostHog key no test sends an event, unless it sets one. Opt-outs of the shell are cleared."""
    monkeypatch.delenv("DLTHUB_INIT_POSTHOG_KEY", raising=False)
    for name in ("DLTHUB_INIT_TELEMETRY", "DO_NOT_TRACK", "RUNTIME__DLTHUB_TELEMETRY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(telemetry, "POSTHOG_PROJECT_KEY", "")
    monkeypatch.setattr(telemetry, "_enabled", False)
    monkeypatch.setattr(telemetry, "_properties", {})


@pytest.fixture
def render(monkeypatch: pytest.MonkeyPatch) -> Callable[[Callable[[], T]], tuple[T, str]]:
    """Calls a function and returns its result and what it printed, without colors."""
    # wide enough that rich does not wrap the lines the tests look for
    monkeypatch.setattr(display.console, "_width", 200)

    def _render(fn: Callable[[], T]) -> tuple[T, str]:
        with display.console.capture() as capture:
            result = fn()
        return result, _ANSI.sub("", capture.get())

    return _render
