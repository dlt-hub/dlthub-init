"""Usage telemetry for the dlthub-init CLI: one PostHog event per run."""

from __future__ import annotations

import json
import os
import secrets
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dlt.common.configuration import resolve_configuration
from dlt.common.configuration.specs import RuntimeConfiguration
from dlt.common.runtime import run_context
from dlt.common.runtime.anon_tracker import get_anonymous_id
from dlt.common.runtime.exec_info import in_continuous_integration

from . import strings
from .config import POSTHOG_HOST, VERSION
from .display import console

try:
    from ._telemetry_key import POSTHOG_PROJECT_KEY  # type: ignore[import-untyped]
except (ImportError, SyntaxError):
    POSTHOG_PROJECT_KEY = ""

EVENT_NAME = "visitor:run:uvx_command"

RunStatus = Literal["success", "failed", "cancelled"]

_REQUEST_TIMEOUT_SECONDS = 3
_NOTICE_MARKER_FILE = ".dlthub_init_telemetry_notice"
_TRUTHY = {"1", "true", "yes", "on"}
_STARTED_AT = time.monotonic()

_enabled = False
_properties: dict[str, object] = {}


def init(*, no_telemetry: bool) -> None:
    """Turn on the event of this run unless the user or dlt opted out, and show the notice once."""
    global _enabled
    _enabled = _is_enabled(no_telemetry)
    if _enabled:
        try:
            _show_first_run_notice()
        except Exception:
            pass


def add_properties(**properties: object) -> None:
    """Add properties to the event of this run."""
    _properties.update(properties)


def track_run(status: RunStatus, error_code: str | None = None) -> None:
    """Send the event of this run. Never raises."""
    if not _enabled:
        return
    try:
        _send(status, error_code)
    except Exception:
        pass


def is_opted_out(no_telemetry: bool) -> bool:
    """True when the user turned telemetry off for this run, so dlt's telemetry goes off too."""
    if no_telemetry:
        return True
    explicit = os.environ.get("DLTHUB_INIT_TELEMETRY")
    if explicit is not None:
        return not _is_truthy(explicit)
    return _is_truthy(os.environ.get("DO_NOT_TRACK"))


def _is_enabled(no_telemetry: bool) -> bool:
    if not _project_key() or is_opted_out(no_telemetry):
        return False
    # an explicit opt-in overrides dlt's opt-out
    if os.environ.get("DLTHUB_INIT_TELEMETRY") is not None:
        return True
    try:
        return resolve_configuration(RuntimeConfiguration()).dlthub_telemetry
    except Exception:
        return False


def _send(status: RunStatus, error_code: str | None) -> None:
    device_id = get_anonymous_id()
    properties: dict[str, object] = {
        "actor_type": "visitor",
        "actor_id": device_id,
        "object_type": "uvx_command",
        "object_id": "dlthub-init",
        "context": "uvx-init",
        "source": "uvx",
        "device_id": device_id,
        "session_id": secrets.token_hex(16),
        "cli_version": VERSION,
        "ci": in_continuous_integration(),
        "status": status,
        "duration_ms": int((time.monotonic() - _STARTED_AT) * 1000),
        "$geoip_disable": True,
        **_properties,
    }
    if error_code is not None:
        properties["error_code"] = error_code
    event = {
        "api_key": _project_key(),
        "event": EVENT_NAME,
        "distinct_id": device_id,
        "properties": properties,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    request = urllib.request.Request(
        f"{_host()}/i/v0/e/",
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS):
        pass


def _show_first_run_notice() -> None:
    marker = Path(run_context.active().global_dir) / _NOTICE_MARKER_FILE
    if marker.exists():
        return
    console.print(strings.MSG_TELEMETRY_NOTICE)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in _TRUTHY


def _project_key() -> str:
    return os.environ.get("DLTHUB_INIT_POSTHOG_KEY") or POSTHOG_PROJECT_KEY


def _host() -> str:
    return os.environ.get("DLTHUB_INIT_POSTHOG_HOST") or POSTHOG_HOST
