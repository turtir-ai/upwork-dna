#!/usr/bin/env python3
"""
Auto-sync script for Upwork DNA Extension
Monitors Downloads/upwork_dna and copies to dashboard data directory
"""

import os
import shutil
import time
from pathlib import Path

# Try to import watchdog, fall back to polling
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️ Watchdog not available, using polling mode")

# Configuration
SOURCE_DIR = Path.home() / "Downloads" / "upwork_dna"
TARGET_DIR = Path("/Users/dev/Documents/upworkextension/analist/data/dataanalist")
DASHBOARD_DIR = Path("/Users/dev/Documents/upworkextension/analist")

print(f"📁 Source: {SOURCE_DIR}")
print(f"📁 Target: {TARGET_DIR}")
print(f"📁 Dashboard: {DASHBOARD_DIR}")
print()

# Only define the watchdog handler class if watchdog is available
if WATCHDOG_AVAILABLE:
    class UpworkDNAHandler(FileSystemEventHandler):
        """Handle new files in upwork_dna directory"""

        def on_created(self, event):
            if event.is_directory:
                return

            src_path = Path(event.src_path)
            if not src_path.suffix in ['.csv', '.json']:
                return

            print(f"📄 New file: {src_path.name}")

            # Copy to dashboard data directory
            rel_path = src_path.relative_to(SOURCE_DIR)
            dest_path = TARGET_DIR / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(src_path, dest_path)
            print(f"   ✅ Copied to: {dest_path}")

            # Trigger dashboard refresh
            print(f"   🔄 Dashboard updated!")
            print()

def main():
    print("🚀 Upwork DNA Auto-Sync Started")
    print("=" * 50)

    # Ensure directories exist
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Copy existing files
    print("📋 Copying existing files...")
    count = 0
    for csv_file in SOURCE_DIR.rglob("*.csv"):
        rel_path = csv_file.relative_to(SOURCE_DIR)
        dest_path = TARGET_DIR / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(csv_file, dest_path)
        count += 1
    print(f"✅ Copied {count} existing files")
    print()

    if WATCHDOG_AVAILABLE:
        # Start watching with watchdog
        event_handler = UpworkDNAHandler()
        observer = Observer()
        observer.schedule(event_handler, str(SOURCE_DIR), recursive=True)
        observer.start()

        print(f"👀 Watching: {SOURCE_DIR}")
        print("Press Ctrl+C to stop...")
        print()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\n👋 Stopped")
    else:
        # Fallback to polling
        print("⚠️ Using polling mode (5 second intervals)")
        print("Press Ctrl+C to stop...")
        print()

        known_files = set()

        try:
            while True:
                # Check for new files (both CSV and JSON)
                current_files = set(SOURCE_DIR.rglob("*.csv")) | set(SOURCE_DIR.rglob("*.json"))
                new_files = current_files - known_files

                for new_file in new_files:
                    print(f"📄 New file: {new_file.name}")
                    rel_path = new_file.relative_to(SOURCE_DIR)
                    dest_path = TARGET_DIR / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(new_file, dest_path)
                    print(f"   ✅ Copied to: {dest_path}")

                known_files = current_files
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 Stopped")

if __name__ == "__main__":
    main()
