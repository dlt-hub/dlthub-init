"""BROKEN #1 — pagination bug. The run goes green and loads 100 of 935 customers.

The mistake: the `json_link` paginator looks for a `next` key **in the response
body**, but this API advertises the next page in the `Link` response **header**.
The body is a bare array, so `next` is never found, the paginator concludes
there is no next page, and extraction stops after page one.

    correct (`header_link`) -> 935 rows
    this    (`json_link`)   ->  100 rows   (10.7% of the data)

This is the dangerous class of bug: nothing fails. No exception, no warning, a
green run, and a table that is quietly missing 89% of its rows. Compare
`customers_bad_pagination` against `customers` in the `jaffle_shop` dataset.

Two variants of the same mistake are shown below — the second one caps at a
fixed page count, which breaks the day the dataset outgrows the cap.
"""

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import rest_api_source

from jaffle_shop import BASE_URL, DATASET, PAGE_SIZE, TAG


def broken_source():
    return rest_api_source(
        {
            "client": {
                "base_url": BASE_URL,
                # BUG: this API has no `next` key in the body — it uses a Link header.
                # Should be: "paginator": "header_link"
                "paginator": {"type": "json_link", "next_url_path": "next"},
            },
            "resource_defaults": {
                "write_disposition": "replace",
                "endpoint": {"params": {"page_size": PAGE_SIZE}},
            },
            "resources": [
                {
                    "name": "customers_bad_pagination",
                    "endpoint": {"path": "customers"},
                },
                {
                    # BUG (variant): hard-capped page count. Fine today at 6 stores,
                    # silently truncating the day there are more than 2 pages of them.
                    "name": "stores_bad_pagination",
                    "endpoint": {
                        "path": "stores",
                        "paginator": {
                            "type": "page_number",
                            "base_page": 1,
                            "page_param": "page",
                            "total_path": None,
                            "maximum_page": 2,
                        },
                    },
                },
            ],
        }
    )


@run.pipeline(
    "jaffle_bad_pagination",
    section="jaffle_shop",
    trigger=trigger.tag(TAG),
    expose={
        "display_name": "Jaffle — BROKEN pagination (silent under-load)",
        "tags": ["jaffle", "broken", "silent"],
    },
)
def load_jaffle_bad_pagination() -> None:
    """Succeeds, but loads 100 customers instead of 935."""
    pipeline = dlt.pipeline(
        pipeline_name="jaffle_bad_pagination",
        destination="playground",
        dataset_name=DATASET,
    )
    info = pipeline.run(broken_source())
    print(info)
    print(
        "NOTE: this run is green but incomplete — expected 935 customers, "
        "loaded 100. Compare with the `customers` table from jaffle_correct."
    )


if __name__ == "__main__":
    load_jaffle_bad_pagination()
