import json
from pathlib import Path

from uvts_api.main import create_app


def main() -> None:
    output = Path(__file__).parents[4] / "contracts" / "openapi.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")
    print(output)


if __name__ == "__main__":
    main()
