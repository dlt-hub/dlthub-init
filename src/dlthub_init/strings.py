"""User-facing CLI copy. Single source of truth for everything the user reads
in the terminal.

Naming convention:
  ERROR_*   : exception messages — use `.format()` with named placeholders
  MSG_*     : status / info lines printed during execution
  HINT_*    : what to do after a failed step
  LABEL_*   : section labels in the next-steps output
  STEPS_*   : prose labels for ordered command lists
  CMD_*     : shell command snippets shown to the user

Rich markup stays in the strings. argparse `help=` text stays in `cli.py`,
bound to the argument definitions.
"""

from __future__ import annotations

ERROR_WRITE_FAILED = "Couldn't create {path}: {reason}"
ERROR_DLTHUB_NOT_FOUND = "The `dlthub` command was not found in {path}. Run it with `uvx dlthub-init@latest`."
ERROR_DLTHUB_FAILED_TO_START = "Couldn't start {cmd}: {reason}"
ERROR_UV_COMMAND_FAILED = "Command failed with exit code {returncode}: {cmd}"
ERROR_UV_COMMAND_NOT_FOUND = "Command not found: {cmd}"

MSG_CANCELLED = "\n[yellow]Cancelled.[/yellow]"
MSG_ERROR_PREFIX = "[red]Error:[/red] {message}"
MSG_UNEXPECTED_ERROR = "[red]Unexpected error:[/red] {message}"
MSG_UNEXPECTED_ERROR_HINT = "[dim]Re-run with --verbose to see the full traceback.[/dim]"
MSG_HEADER = "Initializing a dltHub workspace in [bold]{project_dir}[/bold] (dlt {dlt_version})"
MSG_STEP_FAILED = "\n[red]✗[/red] dlthub {step} failed (exit {returncode})"
MSG_INSTALLING_DEPS = "Installing dependencies"
MSG_INSTALLED_DEPS = "Installed dependencies into .venv"
MSG_SYNC_FAILED = "\n[red]✗[/red] Installing dependencies failed: {message}"
MSG_NO_UV = "\n[yellow]Skipped[/yellow] dependency sync: uv was not found."

HINT_CONFIRM_CHANGES = (
    "If dlthub listed changes above, nothing was changed: re-run with [bold]-y[/bold] to apply"
    " them, or with [bold]--skip[/bold] to keep existing files."
)
HINT_FINISH_AGENT_SETUP = (
    "The workspace exists. Finish the agent setup with [bold]uv run dlthub ai init --agent {agent}[/bold]."
)

LABEL_NEXT_STEPS = "Next steps"
LABEL_NEXT_STEP = "Next step"

STEPS_LABEL_CD = "Change into the workspace:"
STEPS_LABEL_INSTALL_DEPS = "Install dependencies:"
STEPS_LABEL_OPEN_AGENT = "Start a new session of your coding agent in the workspace and tell it what to build."

CMD_UV_SYNC = "uv sync"
CMD_CD = "cd {project_dir}"

MSG_TELEMETRY_NOTICE = (
    "[dim]dlthub-init sends anonymous usage events to help us improve user experience. "
    "Opt out with --no-telemetry, DLTHUB_INIT_TELEMETRY=0, or DO_NOT_TRACK=1.[/dim]"
)
