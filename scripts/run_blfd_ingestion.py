from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion.providers.blfd import BLfDProvider


def main():
    typename = None
    max_features = 5000

    args = sys.argv[1:]
    if args:
        typename = args[0]
    if len(args) > 1:
        max_features = int(args[1])

    provider = BLfDProvider()
    result = provider.run(typename=typename, max_features=max_features)
    print(result)


if __name__ == "__main__":
    main()
