from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISSUES_DIR = ROOT / "tickets" / "github_issues"

def parse_issue(path: Path) -> tuple[str, list[str], str]:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    labels: list[str] = []
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            _, fm, body = parts
            for line in fm.splitlines():
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("labels:"):
                    labels = [x.strip() for x in line.split(":", 1)[1].split(",") if x.strip()]
    return title, labels, body.strip()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    files = sorted(ISSUES_DIR.glob("*.md"))
    if args.limit:
        files = files[:args.limit]

    for path in files:
        title, labels, body = parse_issue(path)
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for label in labels:
            cmd.extend(["--label", label])

        if args.dry_run:
            print(" ".join(cmd))
        else:
            print("[CREATE]", title)
            subprocess.check_call(cmd)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
