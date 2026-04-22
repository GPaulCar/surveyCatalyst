from __future__ import annotations

from service_control import api_start


def main() -> None:
    result = api_start()
    print(result["detail"])


if __name__ == "__main__":
    main()
