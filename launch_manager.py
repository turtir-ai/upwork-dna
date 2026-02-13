#!/usr/bin/env python3
"""
Upwork DNA - Unified Launch Manager
Starts all components: auto-sync, dashboard, and controls the workflow
"""

import os
import sys
import subprocess
import time
import json
import socket
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Paths
PROJECT_DIR = Path("/Users/dev/Documents/upworkextension")
EXTENSION_DIR = PROJECT_DIR / "original_repo_v2"
ANALIST_DIR = PROJECT_DIR / "analist"
BACKEND_DIR = PROJECT_DIR / "backend"
DOWNLOADS_DIR = Path.home() / "Downloads" / "upwork_dna"
DATA_DIR = ANALIST_DIR / "data" / "dataanalist"
SYNC_SCRIPT = PROJECT_DIR / "auto_sync_extension.py"
DASHBOARD_APP = ANALIST_DIR / "dashboard" / "app.py"
BACKEND_APP = BACKEND_DIR / "main.py"
PID_FILE = PROJECT_DIR / ".upwork_dna_pids.json"
LOG_FILE = PROJECT_DIR / "upwork_dna.log"


def pick_python(*candidates):
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return sys.executable


BACKEND_PYTHON = pick_python(BACKEND_DIR / "venv" / "bin" / "python")
ANALIST_PYTHON = pick_python(ANALIST_DIR / "venv" / "bin" / "python")

# Colors for output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def log(message, color=""):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{RESET}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def is_running(pid):
    """Check if process is running"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def save_pids(pids):
    """Save process IDs to file"""
    with open(PID_FILE, "w") as f:
        json.dump({k: str(v) for k, v in pids.items()}, f)

def load_pids():
    """Load process IDs from file"""
    if PID_FILE.exists():
        with open(PID_FILE, "r") as f:
            return json.load(f)
    return {}


def is_port_open(port):
    """Return True if a local TCP port is already in use."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0
    finally:
        sock.close()


def is_http_ok(url, timeout=1.5):
    """Return True when endpoint responds with HTTP 2xx/3xx."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            return 200 <= int(status) < 400
    except Exception:
        return False

def stop_existing():
    """Stop existing processes"""
    pids = load_pids()
    stopped = []
    for name, pid_str in pids.items():
        try:
            pid = int(pid_str)
            if is_running(pid):
                os.kill(pid, 15)  # SIGTERM
                stopped.append(name)
                log(f"Stopped {name} (PID {pid})", YELLOW)
        except (ValueError, OSError):
            pass
    return stopped

def start_auto_sync():
    """Start the auto-sync script"""
    log("Starting auto-sync script...", BLUE)
    process = subprocess.Popen(
        [ANALIST_PYTHON, str(SYNC_SCRIPT)],
        cwd=str(PROJECT_DIR),
        stdout=open(PROJECT_DIR / "auto_sync.log", "a"),
        stderr=subprocess.STDOUT
    )
    log(f"Auto-sync started (PID {process.pid})", GREEN)
    return {"auto_sync": process.pid}


def start_orchestrator():
    """Start local FastAPI orchestrator on port 8000."""
    log("Starting orchestrator API...", BLUE)
    process = subprocess.Popen(
        [
            BACKEND_PYTHON,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(BACKEND_DIR),
        stdout=open(PROJECT_DIR / "orchestrator.log", "a"),
        stderr=subprocess.STDOUT,
    )
    log(f"Orchestrator started on http://127.0.0.1:8000 (PID {process.pid})", GREEN)
    return {"orchestrator": process.pid}

def start_dashboard():
    """Start the Streamlit dashboard"""
    log("Starting dashboard...", BLUE)
    process = subprocess.Popen(
        [
            ANALIST_PYTHON,
            "-m",
            "streamlit",
            "run",
            "dashboard/app.py",
            "--server.headless",
            "true",
            "--server.port",
            "8501",
        ],
        cwd=str(ANALIST_DIR),
        stdout=open(PROJECT_DIR / "dashboard.log", "a"),
        stderr=subprocess.STDOUT
    )
    log(f"Dashboard started on http://localhost:8501 (PID {process.pid})", GREEN)
    return {"dashboard": process.pid}

def ensure_directories():
    """Ensure all required directories exist"""
    directories = [DOWNLOADS_DIR, DATA_DIR]
    for d in directories:
        d.mkdir(parents=True, exist_ok=True)
    log("Directories ready", GREEN)

def check_extension_queue():
    """Check if extension has active queue"""
    # We'll create a simple file-based queue indicator
    queue_file = PROJECT_DIR / "queue_status.json"
    if queue_file.exists():
        with open(queue_file, "r") as f:
            return json.load(f)
    return {"queue": [], "active": False}

def print_status():
    """Print system status"""
    print("\n" + "="*60)
    print(f"     {GREEN}UPWORK DNA - SYSTEM STATUS{RESET}")
    print("="*60)

    # Check auto-sync
    sync_log = PROJECT_DIR / "auto_sync.log"
    if sync_log.exists():
        with open(sync_log, "r") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                print(f"📡 Auto-Sync: {GREEN}Active{RESET}")
                print(f"   Last: {last_line[:50]}...")

    # Check dashboard
    try:
        urllib.request.urlopen("http://localhost:8501", timeout=1)
        print(f"📊 Dashboard: {GREEN}Running{RESET} at http://localhost:8501")
    except:
        print(f"📊 Dashboard: {RED}Not responding{RESET}")

    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
        print(f"🧠 Orchestrator: {GREEN}Running{RESET} at http://127.0.0.1:8000")
    except:
        print(f"🧠 Orchestrator: {RED}Not responding{RESET}")

    # Check for new data
    data_files = list(DATA_DIR.glob("*.csv")) + list(DATA_DIR.glob("*.json"))
    today = datetime.now().strftime("%Y-%m-%d")
    today_files = [f for f in data_files if today in f.name or f.stat().st_mtime > time.time() - 86400]

    print(f"📁 Data Files: {len(data_files)} total, {len(today_files)} from today")

    # Check downloads directory
    download_files = list(DOWNLOADS_DIR.glob("**/*.csv")) + list(DOWNLOADS_DIR.glob("**/*.json"))
    print(f"⬇️  Downloads: {len(download_files)} files")

    # Queue status
    queue = check_extension_queue()
    if queue.get("queue"):
        print(f"📋 Queue: {len(queue['queue'])} keywords")

    # Check NLP keywords
    nlp_file = DATA_DIR / "recommended_keywords.json"
    if nlp_file.exists():
        with open(nlp_file) as f:
            nlp_data = json.load(f)
            if nlp_data.get("keywords"):
                print(f"🤖 NLP Keywords: {len(nlp_data['keywords'])} generated")

    print("="*60 + "\n")

def run_nlp_analysis():
    """Run NLP analysis and generate new keywords"""
    log("Running NLP analysis...", BLUE)
    nlp_script = ANALIST_DIR / "nlp_keyword_generator.py"

    if nlp_script.exists():
        try:
            result = subprocess.run(
                [ANALIST_PYTHON, str(nlp_script)],
                capture_output=True,
                text=True,
                timeout=120
            )
            log(f"NLP Analysis complete", GREEN)
            return True
        except Exception as e:
            log(f"NLP Analysis failed: {e}", RED)
            return False
    else:
        log("NLP script not found", YELLOW)
        return False


def wait_for_orchestrator(timeout_seconds=20):
    """Wait until orchestrator health endpoint is reachable."""
    start = time.time()
    while time.time() - start <= timeout_seconds:
        if is_http_ok("http://127.0.0.1:8000/health", timeout=1):
            return True
        time.sleep(0.5)
    return False

def main():
    """Main launch manager"""
    print("\n" + "="*60)
    print(f"     {GREEN}UPWORK DNA - LAUNCH MANAGER{RESET}")
    print("="*60 + "\n")

    import argparse
    parser = argparse.ArgumentParser(description="Upwork DNA Launch Manager")
    parser.add_argument("action", nargs="?", default="start", choices=["start", "stop", "status", "restart", "nlp"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "stop":
        stopped = stop_existing()
        if stopped:
            log(f"Stopped: {', '.join(stopped)}", GREEN)
        else:
            log("No running processes found", YELLOW)
        PID_FILE.unlink(missing_ok=True)
        return

    if args.action == "status":
        print_status()
        return

    if args.action == "nlp":
        run_nlp_analysis()
        return

    if args.action == "restart":
        stop_existing()
        time.sleep(2)
        # Fall through to start

    # Start everything
    ensure_directories()

    pids = {}
    orchestrator_running = is_http_ok("http://127.0.0.1:8000/health", timeout=1)
    if orchestrator_running:
        log("Orchestrator already running on 127.0.0.1:8000, skipping start.", GREEN)
    else:
        if is_port_open(8000):
            log("Port 8000 is in use but /health is not responding. Stop conflicting process first.", RED)
            sys.exit(1)
        pids.update(start_orchestrator())
        if not wait_for_orchestrator(timeout_seconds=20):
            log("Orchestrator failed health check on port 8000.", RED)
            sys.exit(1)
        log("Orchestrator health check passed.", GREEN)

    pids.update(start_auto_sync())
    time.sleep(1)

    if is_port_open(8501):
        log("Port 8501 already in use; dashboard start skipped (API remains active).", YELLOW)
    else:
        pids.update(start_dashboard())

    save_pids(pids)

    log("\n" + "="*60, GREEN)
    log("SYSTEM STARTED SUCCESSFULLY!", GREEN)
    log("="*60 + "\n", GREEN)

    log("Next steps:", BLUE)
    log("1. Open Chrome and load the extension from:", BLUE)
    log(f"   {EXTENSION_DIR}", BLUE)
    log("2. Open the dashboard at:", BLUE)
    log("   http://localhost:8501", BLUE)
    log("3. Verify orchestrator API:", BLUE)
    log("   http://127.0.0.1:8000/docs", BLUE)
    log("4. Add keywords to the queue in the extension popup", BLUE)
    log("5. Data will automatically sync to the dashboard", BLUE)
    log("\nPress Ctrl+C to stop all services\n", BLUE)

    try:
        while True:
            time.sleep(10)
            # Check if processes are still running
            all_running = True
            for name, pid_str in load_pids().items():
                try:
                    pid = int(pid_str)
                    if not is_running(pid):
                        log(f"Process {name} (PID {pid}) died!", RED)
                        all_running = False
                except (ValueError, OSError):
                    pass

            if not all_running:
                log("Some processes died. Restarting...", YELLOW)
                stop_existing()
                time.sleep(2)
                main()  # Restart
                return

    except KeyboardInterrupt:
        log("\nShutting down...", YELLOW)
        stop_existing()
        PID_FILE.unlink(missing_ok=True)
        log("Done. Goodbye!", GREEN)

if __name__ == "__main__":
    main()
