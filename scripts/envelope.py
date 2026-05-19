from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = ROOT / "envelope"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_env() -> dict:
    if not ENVELOPE.exists():
        return {
            "updated_at_utc": None,
            "author": None,
            "type": None,
            "command": None,
            "response": None,
        }
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


def write_env(payload: dict) -> None:
    ENVELOPE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear(author: str | None = None) -> None:
    write_env(
        {
            "updated_at_utc": now_utc(),
            "author": author,
            "type": "clear",
            "command": None,
            "response": None,
        }
    )


def set_command(text: str, author: str | None) -> None:
    write_env(
        {
            "updated_at_utc": now_utc(),
            "author": author,
            "type": "command",
            "command": text,
            "response": None,
        }
    )


def set_response(text: str, author: str | None) -> None:
    write_env(
        {
            "updated_at_utc": now_utc(),
            "author": author,
            "type": "response",
            "command": None,
            "response": text,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Single-record command/response envelope.")
    sub = parser.add_subparsers(dest="action", required=True)

    p_clear = sub.add_parser("clear")
    p_clear.add_argument("--author", default=None)

    p_set = sub.add_parser("set")
    p_set.add_argument("text")
    p_set.add_argument("--author", default=None)

    p_reply = sub.add_parser("reply")
    p_reply.add_argument("text")
    p_reply.add_argument("--author", default=None)

    sub.add_parser("show")

    args = parser.parse_args()

    if args.action == "clear":
        clear(args.author)
    elif args.action == "set":
        set_command(args.text, args.author)
    elif args.action == "reply":
        set_response(args.text, args.author)
    elif args.action == "show":
        pass

    print(json.dumps(read_env(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
