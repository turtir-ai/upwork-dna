#!/usr/bin/env python3
"""
Local backend watchdog for Upwork DNA.
Restarts the launchd backend service if /health is unresponsive repeatedly.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_DIR = Path("/Users/dev/Documents/upworkextension")
LOG_PATH = PROJECT_DIR / "backend.watchdog.log"
HEALTH_URL = os.getenv("UPWORK_BACKEND_HEALTH_URL", "http://127.0.0.1:8000/health")
BACKEND_LABEL = os.getenv("UPWORK_BACKEND_LABEL", "com.upworkdna.backend.api")
CHECK_INTERVAL_SECONDS = max(5, int(os.getenv("UPWORK_WATCHDOG_INTERVAL_SECONDS", "15")))
FAIL_THRESHOLD = max(2, int(os.getenv("UPWORK_WATCHDOG_FAIL_THRESHOLD", "3")))
RESTART_COOLDOWN_SECONDS = max(5, int(os.getenv("UPWORK_WATCHDOG_RESTART_COOLDOWN", "20")))
REQUEST_TIMEOUT_SECONDS = max(1, int(os.getenv("UPWORK_WATCHDOG_TIMEOUT_SECONDS", "2")))


def log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line)


def health_ok() -> bool:
    req = Request(HEALTH_URL, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if int(getattr(response, "status", 0)) != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "healthy"
    except (URLError, TimeoutError, ValueError, OSError):
        return False


def restart_backend() -> None:
    uid = os.getuid()
    target = f"gui/{uid}/{BACKEND_LABEL}"
    subprocess.run(["launchctl", "kickstart", "-k", target], check=False)
    log(f"Watchdog restart requested for {target}")


def main() -> None:
    log(
        "Watchdog started "
        f"(url={HEALTH_URL}, interval={CHECK_INTERVAL_SECONDS}s, fail_threshold={FAIL_THRESHOLD})"
    )
    consecutive_failures = 0
    while True:
        if health_ok():
            if consecutive_failures:
                log("Health recovered; failure counter reset")
            consecutive_failures = 0
            time.sleep(CHECK_INTERVAL_SECONDS)
            continue

        consecutive_failures += 1
        log(f"Health check failed ({consecutive_failures}/{FAIL_THRESHOLD})")
        if consecutive_failures >= FAIL_THRESHOLD:
            restart_backend()
            consecutive_failures = 0
            time.sleep(RESTART_COOLDOWN_SECONDS)
            continue

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
