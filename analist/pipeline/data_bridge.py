#!/usr/bin/env python3
"""
DATA PIPELINE BRIDGE (P2.1)
===========================
Watch upwork_dna/ directory for new exports and trigger analysis pipeline.

Features:
- Real-time file watching with watchdog
- Auto-trigger analysis on new data
- Queue management integration
- CSV/JSON export detection

Author: Upwork Extension Pipeline
Date: 2026-02-07
"""

import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, List
from urllib.request import Request, urlopen
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataPipelineBridge')


class DataPipelineBridge:
    """
    Bridge between data exports and analysis pipeline.

    Watches upwork_dna/ directory for new CSV/JSON exports
    and triggers the analysis pipeline automatically.
    """

    def __init__(
        self,
        watch_directory: str = str(Path.home() / "Downloads" / "upwork_dna"),
        callback: Optional[Callable] = None,
        cooldown_seconds: int = 30
    ):
        """
        Initialize the data pipeline bridge.

        Args:
            watch_directory: Directory to watch for new exports
            callback: Function to call when new data detected
            cooldown_seconds: Minimum seconds between triggers
        """
        self.watch_directory = Path(watch_directory)
        self.callback = callback
        self.cooldown_seconds = cooldown_seconds
        self.last_trigger_time = 0
        self.observer: Optional[Observer] = None
        self.processed_files: set = set()

        # Ensure watch directory exists
        self.watch_directory.mkdir(parents=True, exist_ok=True)

        # Load processed files cache
        self._load_processed_cache()

    def _load_processed_cache(self):
        """Load cache of already processed files."""
        cache_file = self.watch_directory / ".processed_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.processed_files = set(json.load(f))
                logger.info(f"Loaded {len(self.processed_files)} processed files from cache")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.processed_files = set()

    def _save_processed_cache(self):
        """Save cache of processed files."""
        cache_file = self.watch_directory / ".processed_cache.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(list(self.processed_files), f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _is_data_file(self, path: Path) -> bool:
        """Check if file is a data export."""
        return path.suffix.lower() in {'.csv', '.json'}

    def _extract_keyword_from_path(self, path: Path) -> Optional[str]:
        """Extract keyword from file path."""
        # Path format: upwork_dna/YYYY-MM-DD/keyword_time/file.csv
        parts = path.parts
        if len(parts) >= 3:
            # Extract from folder name
            folder_name = parts[-2]
            # Remove timestamp suffix
            keyword = folder_name.rsplit('_', 1)[0]
            return keyword.replace('_', ' ')
        return None

    def _trigger_pipeline(self, keyword_path: Path):
        """Trigger analysis pipeline for new data."""
        current_time = time.time()

        # Check cooldown
        if current_time - self.last_trigger_time < self.cooldown_seconds:
            logger.debug(f"Cooldown active, skipping trigger")
            return

        # Check if already processed
        file_id = f"{keyword_path}_{os.path.getmtime(keyword_path)}"
        if file_id in self.processed_files:
            logger.debug(f"File already processed: {keyword_path}")
            return

        logger.info(f"New data detected: {keyword_path}")

        # Extract keyword
        keyword = self._extract_keyword_from_path(keyword_path)
        if not keyword:
            keyword = keyword_path.parent.name

        # Mark as processed
        self.processed_files.add(file_id)
        self._save_processed_cache()
        self.last_trigger_time = current_time

        # Call callback if provided
        if self.callback:
            try:
                self.callback(keyword, keyword_path)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        # Log trigger
        self._log_trigger(keyword, keyword_path)

    def _log_trigger(self, keyword: str, path: Path):
        """Log pipeline trigger to file."""
        log_file = self.watch_directory / "pipeline_triggers.log"
        try:
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} | {keyword} | {path}\n")
        except Exception as e:
            logger.warning(f"Failed to log trigger: {e}")

    def watch_directory(self):
        """Start watching directory for new files."""
        if self.observer and self.observer.is_alive():
            logger.warning("Observer already running")
            return

        handler = PipelineEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.watch_directory), recursive=True)
        self.observer.start()

        logger.info(f"Started watching: {self.watch_directory}")

    def stop_watching(self):
        """Stop watching directory."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching directory")

    def trigger_pipeline(self, keyword_path: str):
        """Manually trigger pipeline for specific path."""
        path = Path(keyword_path)
        if path.exists():
            self._trigger_pipeline(path)
        else:
            logger.warning(f"Path does not exist: {keyword_path}")

    def scan_existing_files(self):
        """Scan existing files and trigger pipeline if needed."""
        logger.info("Scanning existing files...")

        for csv_file in self.watch_directory.rglob("*.csv"):
            if self._is_data_file(csv_file):
                self._trigger_pipeline(csv_file)

        for json_file in self.watch_directory.rglob("*.json"):
            # Skip cache file
            if json_file.name == ".processed_cache.json":
                continue
            if self._is_data_file(json_file):
                self._trigger_pipeline(json_file)

        logger.info("Scan complete")


class PipelineEventHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, bridge: DataPipelineBridge):
        self.bridge = bridge

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self.bridge._is_data_file(path):
            self.bridge._trigger_pipeline(path)


def default_pipeline_callback(keyword: str, path: Path):
    """Default callback for pipeline trigger."""
    logger.info(f"Pipeline triggered for keyword: {keyword}")
    logger.info(f"Data location: {path}")
    api_base = os.getenv("UPWORK_ORCHESTRATOR_API", "http://127.0.0.1:8000")
    url = f"{api_base}/v1/ingest/scan"
    req = Request(url, method="POST")

    print(f"\n{'='*60}")
    print("🚀 PIPELINE TRIGGERED")
    print(f"Keyword: {keyword}")
    print(f"Path: {path}")
    print(f"Time: {datetime.now().isoformat()}")
    try:
        with urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            print(f"Ingest scan: {payload.get('new_files', 0)} new files")
    except Exception as exc:
        logger.warning(f"Orchestrator scan failed: {exc}")
        print("Ingest scan: failed (orchestrator unavailable)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Example usage
    bridge = DataPipelineBridge(
        watch_directory=str(Path.home() / "Downloads" / "upwork_dna"),
        callback=default_pipeline_callback
    )

    # Start watching
    bridge.watch_directory()

    # Scan existing files
    bridge.scan_existing_files()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop_watching()
        logger.info("Bridge stopped")
