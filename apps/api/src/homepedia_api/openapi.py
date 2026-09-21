"""Export the OpenAPI contract without a database or any environment variable."""

import json
import sys
from pathlib import Path

from homepedia_api.main import create_app


def main() -> None:
    target = Path(sys.argv[1])
    schema = create_app().openapi()
    target.write_text(json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
