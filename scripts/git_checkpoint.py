import subprocess
import sys
from datetime import datetime


def run(cmd: str, allow_fail: bool = False) -> int:
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode != 0 and not allow_fail:
        sys.exit(result.returncode)
    return result.returncode


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/git_checkpoint.py <tag-name> [--no-push]")
        sys.exit(1)

    tag = sys.argv[1]
    no_push = "--no-push" in sys.argv[2:]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[checkpoint] {tag} @ {timestamp}"

    print("[INFO] git add")
    run("git add .")

    print("[INFO] git commit")
    commit_rc = run(f'git commit -m "{message}"', allow_fail=True)
    if commit_rc != 0:
        print("[INFO] commit skipped or nothing to commit")

    print("[INFO] git tag")
    tag_rc = run(f'git tag -a {tag} -m "{message}"', allow_fail=True)
    if tag_rc != 0:
        print("[INFO] tag exists already or could not be created")
        sys.exit(tag_rc)

    if not no_push:
        print("[INFO] git push")
        run("git push")

        print("[INFO] git push origin tag")
        run(f"git push origin {tag}")

    print(f"[DONE] checkpoint complete: {tag}")


if __name__ == "__main__":
    main()
