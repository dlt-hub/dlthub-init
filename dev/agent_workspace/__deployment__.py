"""Five jaffle pipelines, the jobs that react to them, and your agents."""

from alerts import alerts
from diagnostics import endpoint_report
from jaffle_shop.bad_config import load_jaffle_bad_config
from jaffle_shop.bad_incremental import load_jaffle_bad_incremental
from jaffle_shop.bad_pagination import load_jaffle_bad_pagination
from jaffle_shop.bad_selector import load_jaffle_bad_selector
from jaffle_shop.correct import load_jaffle_correct
from loop_probe import loop_probe

__all__ = [
    # --- jaffle_shop/ — one correct pipeline and four broken ones -----------
    "load_jaffle_correct",  # tag:jaffle -> 935 / 10 / 6 rows
    "load_jaffle_bad_pagination",  # tag:jaffle -> GREEN, 100 of 935 rows
    "load_jaffle_bad_selector",  # tag:jaffle -> GREEN, 0 of 6 rows
    "load_jaffle_bad_config",  # tag:jaffle -> FAILS, 404 on /api/v2/
    "load_jaffle_bad_incremental",  # tag:jaffle -> FAILS, bad cursor_path
    # --- what reacts to them ------------------------------------------------
    "alerts",  # records that a job failed, but not why
    "loop_probe",  # smoke test
    "endpoint_report",  # which model endpoint resolved; no key needed
    # Your agents go here once written. Import them above too.
    # Step 1: "job_inspector" from verified_agent.py
    # Step 2: whatever you write in my_agent.py
]
