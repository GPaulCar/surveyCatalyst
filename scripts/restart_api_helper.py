from __future__ import annotations

import sys
import time

from service_control import api_start, _clear_pid, _terminate_pid


def main() -> None:
    current_pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    delay_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    time.sleep(max(delay_seconds, 0))
    if current_pid > 0:
        try:
            _terminate_pid(current_pid)
        except Exception:
            pass
        _clear_pid()
    time.sleep(1)
    api_start()


if __name__ == "__main__":
    main()
