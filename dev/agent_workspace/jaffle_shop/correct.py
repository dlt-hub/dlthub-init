"""Jaffle Shop, done right — the reference every broken example is compared against.

Loads customers (935), products (10) and stores (6). Orders and items are left
out on purpose: at 62k and 91k rows they make a demo run slow without teaching
anything extra.
"""

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import rest_api_source

from jaffle_shop import BASE_URL, DATASET, PAGE_SIZE, TAG


def jaffle_source():
    return rest_api_source(
        {
            "client": {
                "base_url": BASE_URL,
                # correct: this API advertises the next page in the `Link` response header
                "paginator": "header_link",
            },
            "resource_defaults": {
                "write_disposition": "replace",
                "endpoint": {"params": {"page_size": PAGE_SIZE}},
            },
            "resources": [
                {"name": "customers", "endpoint": {"path": "customers"}},
                {"name": "products", "endpoint": {"path": "products"}},
                {"name": "stores", "endpoint": {"path": "stores"}},
            ],
        }
    )


@run.pipeline(
    "jaffle_correct",
    section="jaffle_shop",
    trigger=trigger.tag(TAG),
    expose={
        "display_name": "Jaffle — correct baseline",
        "tags": ["jaffle", "reference"],
        "starred": True,
    },
)
def load_jaffle_correct() -> None:
    """Expect 935 customers, 10 products, 6 stores."""
    pipeline = dlt.pipeline(
        pipeline_name="jaffle_correct",
        destination="playground",
        dataset_name=DATASET,
    )
    info = pipeline.run(jaffle_source())
    print(info)


if __name__ == "__main__":
    load_jaffle_correct()
