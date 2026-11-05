"""Print dlt's workspace deps as one JSON line."""

import importlib
import json

MODULE = "dlt._workspace.cli.dlthub.utils"


def main() -> None:
    utils = importlib.import_module(MODULE)
    # dlt >= 1.32.0 computes the list; older dlt keeps a WORKSPACE_DEPS constant
    fn = getattr(utils, "workspace_deps", None)
    deps = fn() if fn is not None else list(utils.WORKSPACE_DEPS)
    print(json.dumps(list(deps)))


if __name__ == "__main__":
    main()
