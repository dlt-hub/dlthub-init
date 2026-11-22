import json
from typing import Any, Callable
from unittest.mock import MagicMock, call

import pytest

from dlthub_init import telemetry
from dlthub_init.cli import main
from dlthub_init.errors import DlthubCommandError, WorkspaceError


@pytest.fixture
def env(monkeypatch) -> Callable[..., None]:
    """Sets a PostHog key. Call it to set more variables."""
    monkeypatch.setenv("DLTHUB_INIT_POSTHOG_KEY", "phc_test")

    def set_env(**values: str) -> None:
        for name, value in values.items():
            monkeypatch.setenv(name, value)

    return set_env


@pytest.fixture
def urlopen(monkeypatch, env) -> MagicMock:
    """Turns telemetry on and records the requests instead of sending them."""
    opened = MagicMock()
    monkeypatch.setattr(telemetry.urllib.request, "urlopen", opened)
    monkeypatch.setattr(telemetry, "get_anonymous_id", lambda: "device-123")
    monkeypatch.setattr(telemetry, "_enabled", True)
    return opened


def sent_event(urlopen: MagicMock) -> dict[str, Any]:
    request = urlopen.call_args.args[0]
    assert request.full_url == f"{telemetry.POSTHOG_HOST}/i/v0/e/"
    event: dict[str, Any] = json.loads(request.data)
    return event


@pytest.mark.parametrize(
    "no_telemetry,env_vars,opted_out",
    [
        pytest.param(True, {}, True, id="no-telemetry-flag"),
        pytest.param(False, {}, False, id="default"),
        pytest.param(False, {"DLTHUB_INIT_TELEMETRY": "0"}, True, id="tool-opt-out"),
        pytest.param(False, {"DLTHUB_INIT_TELEMETRY": "1", "DO_NOT_TRACK": "1"}, False, id="tool-opt-in-wins"),
        pytest.param(False, {"DO_NOT_TRACK": "1"}, True, id="do-not-track"),
        # dlt's opt-out turns off only this tool's event, not dlt's own telemetry
        pytest.param(False, {"RUNTIME__DLTHUB_TELEMETRY": "false"}, False, id="dlt-opt-out"),
    ],
)
def test_is_opted_out(env, no_telemetry: bool, env_vars: dict[str, str], opted_out: bool) -> None:
    env(**env_vars)
    assert telemetry.is_opted_out(no_telemetry) is opted_out


@pytest.mark.parametrize(
    "no_telemetry,env_vars,enabled",
    [
        pytest.param(False, {"RUNTIME__DLTHUB_TELEMETRY": "true"}, True, id="dlt-opt-in"),
        pytest.param(False, {"RUNTIME__DLTHUB_TELEMETRY": "false"}, False, id="dlt-opt-out"),
        pytest.param(True, {"RUNTIME__DLTHUB_TELEMETRY": "true"}, False, id="no-telemetry-flag"),
        pytest.param(
            False,
            {"DLTHUB_INIT_TELEMETRY": "1", "RUNTIME__DLTHUB_TELEMETRY": "false"},
            True,
            id="tool-opt-in-beats-dlt-opt-out",
        ),
        pytest.param(
            False, {"DLTHUB_INIT_POSTHOG_KEY": "", "RUNTIME__DLTHUB_TELEMETRY": "true"}, False, id="no-posthog-key"
        ),
    ],
)
def test_is_enabled(env, no_telemetry: bool, env_vars: dict[str, str], enabled: bool) -> None:
    env(**env_vars)
    assert telemetry._is_enabled(no_telemetry) is enabled


def test_disabled_when_dlt_config_fails(env, monkeypatch) -> None:
    monkeypatch.setattr(telemetry, "resolve_configuration", MagicMock(side_effect=ValueError("bad toml")))
    assert telemetry._is_enabled(False) is False


def test_sends_one_event(urlopen) -> None:
    telemetry.track_run("success")
    event = sent_event(urlopen)
    assert event["api_key"] == "phc_test"
    assert event["event"] == telemetry.EVENT_NAME
    assert event["distinct_id"] == "device-123"
    props = event["properties"]
    assert props["object_id"] == "dlthub-init"
    assert props["device_id"] == "device-123"
    assert props["status"] == "success"
    assert props["$geoip_disable"] is True
    assert "error_code" not in props


def test_failed_run_carries_error_and_added_properties(urlopen) -> None:
    telemetry.add_properties(dlt_version="1.33.0", failed_step="init")
    telemetry.track_run("failed", error_code="DlthubCommandError")
    props = sent_event(urlopen)["properties"]
    assert props["error_code"] == "DlthubCommandError"
    assert props["dlt_version"] == "1.33.0"
    assert props["failed_step"] == "init"


def test_sends_nothing_when_disabled(urlopen, monkeypatch) -> None:
    monkeypatch.setattr(telemetry, "_enabled", False)
    telemetry.track_run("success")
    urlopen.assert_not_called()


def test_no_telemetry_run_sends_nothing(urlopen, monkeypatch) -> None:
    monkeypatch.setattr("dlthub_init.cli.run", MagicMock())
    assert main(["--no-telemetry"]) == 0
    urlopen.assert_not_called()


def test_swallows_network_errors(urlopen) -> None:
    urlopen.side_effect = OSError("network down")
    telemetry.track_run("success")


def test_notice_shown_once_and_only_when_enabled(env, monkeypatch, tmp_path) -> None:
    env(RUNTIME__DLTHUB_TELEMETRY="true")
    monkeypatch.setattr(telemetry.run_context, "active", lambda: MagicMock(global_dir=str(tmp_path)))
    printer = MagicMock()
    monkeypatch.setattr(telemetry.console, "print", printer)
    telemetry.init(no_telemetry=True)
    printer.assert_not_called()
    telemetry.init(no_telemetry=False)
    telemetry.init(no_telemetry=False)
    printer.assert_called_once()


def test_notice_errors_do_not_propagate(env, monkeypatch) -> None:
    env(RUNTIME__DLTHUB_TELEMETRY="true")
    monkeypatch.setattr(telemetry.run_context, "active", MagicMock(side_effect=RuntimeError("boom")))
    telemetry.init(no_telemetry=False)


@pytest.mark.parametrize(
    "raised,exit_code,tracked",
    [
        pytest.param(None, 0, call("success"), id="success"),
        pytest.param(KeyboardInterrupt(), 130, call("cancelled"), id="cancelled"),
        pytest.param(WorkspaceError("boom"), 1, call("failed", error_code="WorkspaceError"), id="workspace-error"),
        pytest.param(RuntimeError("kaboom"), 1, call("failed", error_code="RuntimeError"), id="unexpected-error"),
        pytest.param(
            DlthubCommandError("ai init", 2), 2, call("failed", error_code="DlthubCommandError"), id="dlthub-failed"
        ),
    ],
)
def test_main_tracks_the_outcome(monkeypatch, raised: BaseException | None, exit_code: int, tracked) -> None:
    track_run = MagicMock()
    monkeypatch.setattr(telemetry, "track_run", track_run)
    monkeypatch.setattr("dlthub_init.cli.run", MagicMock(side_effect=raised))
    assert main([]) == exit_code
    assert track_run.call_args_list == [tracked]


def test_main_tracks_the_failed_step(monkeypatch) -> None:
    monkeypatch.setattr("dlthub_init.cli.run", MagicMock(side_effect=DlthubCommandError("ai init", 2)))
    main([])
    assert telemetry._properties["failed_step"] == "ai init"
