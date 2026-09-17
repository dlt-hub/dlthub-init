"""Five jaffle pipelines, an alerts job, and both hackathon agent tracks."""

from alerts import alerts
from diagnostics import endpoint_report
from jaffle_shop.bad_config import load_jaffle_bad_config
from jaffle_shop.bad_incremental import load_jaffle_bad_incremental
from jaffle_shop.bad_pagination import load_jaffle_bad_pagination
from jaffle_shop.bad_selector import load_jaffle_bad_selector
from jaffle_shop.correct import load_jaffle_correct
from loop_probe import loop_probe
from my_agent import my_agent
from verified_agent import job_inspector

__all__ = [
    # --- jaffle_shop/ — one correct pipeline and four broken ones -----------
    "load_jaffle_correct",  # tag:jaffle -> 935 / 10 / 6 rows
    "load_jaffle_bad_pagination",  # tag:jaffle -> GREEN, 100 of 935 rows
    "load_jaffle_bad_selector",  # tag:jaffle -> GREEN, 0 of 6 rows
    "load_jaffle_bad_config",  # tag:jaffle -> FAILS, 404 on /api/v2/
    "load_jaffle_bad_incremental",  # tag:jaffle -> FAILS, bad cursor_path
    # --- what reacts to them ------------------------------------------------
    "alerts",  # records that a job failed; Track B starts here
    "job_inspector",  # Track A, the workbench agent
    "my_agent",  # Track B, yours to edit
    "loop_probe",  # smoke test
    "endpoint_report",  # which model endpoint resolved; no key needed
]
