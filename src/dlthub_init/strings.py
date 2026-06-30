"""User-facing CLI copy. Single source of truth for everything the user reads
in the terminal.

Naming convention:
  PROMPT_*  : interactive prompt text
  ERROR_*   : exception messages — use ``.format()`` with named placeholders
  MSG_*     : status / info lines printed during execution
  LABEL_*   : section labels in the summary / next-steps output
  TITLE_*   : panel titles
  HINT_*    : ancillary text (badges, notes)
  STEPS_*   : prose labels for ordered command lists
  CMD_*     : shell command snippets shown to the user

Rich markup stays in the strings. argparse ``help=`` text stays in ``cli.py``,
bound to the argument definitions.
"""

from __future__ import annotations

# Prompts ---------------------------------------------------------------
PROMPT_INSTALL_UV = "uv is required to install dependencies but was not found. Install uv now?"
PROMPT_CREATE_VENV = "Create a virtual environment and install dependencies now?"


# Errors (call sites use .format() with named placeholders) -------------
ERROR_UNKNOWN_SCAFFOLD = "Unknown scaffold {scaffold!r}. Available: {available}"
ERROR_WRITE_FAILED = "Couldn't write to {path}: {reason}"
ERROR_READ_FAILED = "Couldn't read {path}: {reason}"
ERROR_UV_NOT_ON_PATH = "uv was installed, but it is not available on PATH yet. Open a new terminal and try again."
ERROR_UV_COMMAND_FAILED = "Command failed with exit code {returncode}: {cmd}"
ERROR_UV_COMMAND_NOT_FOUND = "Command not found: {cmd}"
ERROR_UV_INSTALLER_FETCH = "Could not download uv installer: {reason}"
ERROR_UV_NEEDS_POWERSHELL = "PowerShell is required to install uv on Windows."


# Status / info messages ------------------------------------------------
MSG_TESTING_SHORTCUT_NOTE = (
    "[yellow]Note:[/yellow] --yes is a non-interactive shortcut for testing/CI. "
    "Run without it for the interactive setup."
)
MSG_CANCELLED = "\n[yellow]Cancelled.[/yellow]"
MSG_ERROR_PREFIX = "[red]Error:[/red] {message}"
MSG_UNEXPECTED_ERROR = "[red]Unexpected error:[/red] {message}"
MSG_UNEXPECTED_ERROR_HINT = "[dim]Re-run with --verbose to see the full traceback.[/dim]"
MSG_HEADER = "Initializing a dltHub workspace in [bold]{project_dir}[/bold]"
MSG_SKILLS_INSTALLED = "Added {count} skill(s) to .agents/skills/ (linked into .claude/skills/)"
MSG_INSTALLING_DEPS = "Installing dependencies"
MSG_INSTALLED_DEPS = "Installed dependencies into .venv"
MSG_SKIPPED_SYNC = "\n[yellow]Skipped[/yellow] dependency sync."
MSG_SYNC_FAILED = (
    "\n[yellow]Heads up:[/yellow] dependency sync failed ({message}). "
    "Your workspace is set up — run [bold]uv sync[/bold] yourself."
)
MSG_NOTHING_WRITTEN = "[dim]Everything was already in place — nothing to write.[/dim]"


# Collision output ------------------------------------------------------
MSG_COLLISION_HEADER = "[red]Error:[/red] cannot initialize because these paths already exist:"
MSG_COLLISION_NO_CHANGES = "\nNo files were changed."
MSG_COLLISION_HINT = (
    "\nUse [bold]--force[/bold] to overwrite generated files, [bold]--no-pyproject[/bold] / "
    "[bold]--no-gitignore[/bold] to skip them, or choose a different target directory."
)


# Summary labels --------------------------------------------------------
LABEL_CREATED = "Created"
LABEL_OVERWRITTEN = "Overwritten"
LABEL_MERGED = "Updated"
LABEL_SKIPPED = "Skipped (already exist)"
LABEL_DISABLED = "Skipped (disabled by flag)"
LABEL_NEXT_STEPS = "Next steps"
LABEL_NEXT_STEP = "Next step"


# Step labels / commands ------------------------------------------------
STEPS_LABEL_CD = "Change into the workspace:"
STEPS_LABEL_INSTALL_UV = "Install uv:"
STEPS_LABEL_INSTALL_DEPS = "Install dependencies:"
STEPS_LABEL_OPEN_AGENT = (
    "Open your coding agent (Claude Code, Cursor, Codex, …) in this workspace and tell it what to build."
)

CMD_INSTALL_UV_UNIX = "curl -LsSf https://astral.sh/uv/install.sh | sh"
CMD_UV_SYNC = "uv sync"
CMD_CD = "cd {project_dir}"


# Telemetry -------------------------------------------------------------
MSG_TELEMETRY_NOTICE = (
    "[dim]dlthub-init sends anonymous usage events to help us improve user experience. "
    "Opt out with --no-telemetry, DLTHUB_INIT_TELEMETRY=0, or DO_NOT_TRACK=1.[/dim]"
)
