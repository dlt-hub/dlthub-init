"""BROKEN #2 — wrong API config. Fails hard on the first request.

Two config mistakes stacked, both of them things people really do:

  1. `base_url` points at `/api/v2/` — this API only serves `/api/v1/`.
     Every request 404s.
  2. A bearer token is configured even though the Jaffle Shop API takes no
     auth at all, and the token is a placeholder that was never filled in.

Expected failure:
    ResourceExtractionError: ... 404 Client Error: Not Found for url:
    https://jaffle-shop.dlthub.com/api/v2/products

This is the loud, easy class of bug — it fails on the first request, so it
never writes a partial table. It exists here to trigger the `alerts` job.
"""

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import rest_api_source

from jaffle_shop import DATASET, PAGE_SIZE, TAG

# BUG: the API serves /api/v1/ only. Should be "https://jaffle-shop.dlthub.com/api/v1/"
WRONG_BASE_URL = "https://jaffle-shop.dlthub.com/api/v2/"


def misconfigured_source():
    return rest_api_source(
        {
            "client": {
                "base_url": WRONG_BASE_URL,
                # BUG: this API is unauthenticated, and the token is a placeholder
                # that was never replaced with a real secret.
                "auth": {"type": "bearer", "token": "REPLACE_ME"},
                "paginator": "header_link",
            },
            "resource_defaults": {
                "write_disposition": "replace",
                "endpoint": {"params": {"page_size": PAGE_SIZE}},
            },
            "resources": [
                {"name": "products_bad_config", "endpoint": {"path": "products"}},
            ],
        }
    )


@run.pipeline(
    "jaffle_bad_config",
    section="jaffle_shop",
    trigger=trigger.tag(TAG),
    expose={
        "display_name": "Jaffle — BROKEN api config (404)",
        "tags": ["jaffle", "broken", "fails"],
    },
)
def load_jaffle_bad_config() -> None:
    """Always fails with a 404 — wrong base_url and a placeholder token."""
    pipeline = dlt.pipeline(
        pipeline_name="jaffle_bad_config",
        destination="playground",
        dataset_name=DATASET,
    )
    info = pipeline.run(misconfigured_source())
    print(info)


if __name__ == "__main__":
    load_jaffle_bad_config()
