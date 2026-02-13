#!/usr/bin/env python3
"""
DATA PIPELINE FLOW TEST
=======================
Test the complete data flow from scraping to dashboard.

Tests:
1. Check ~/upwork_dna/ for new data
2. Check dashboard data directory (/Users/dev/Documents/upworkextension/analist/data/dataanalist/)
3. Identify why dashboard shows old data
4. Test manual data injection
5. Report on root cause
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def main():
    print_section("DATA PIPELINE FLOW TEST")

    # Paths
    upwork_dna_dir = Path.home() / "upwork_dna"
    dashboard_data_dir = Path("/Users/dev/Documents/upworkextension/analist/data/dataanalist")
    extension_dir = Path("/Applications/Upwork DNA.app/Contents/Resources/extension")

    # ============================================================
    # TEST 1: Check upwork_dna directory
    # ============================================================
    print_section("TEST 1: ~/upwork_dna/ Directory")

    if upwork_dna_dir.exists():
        print_success(f"upwork_dna directory exists: {upwork_dna_dir}")

        # List all files
        all_files = list(upwork_dna_dir.rglob("*"))
        csv_files = list(upwork_dna_dir.rglob("*.csv"))
        json_files = list(upwork_dna_dir.rglob("*.json"))

        print_info(f"Total files: {len(all_files)}")
        print_info(f"CSV files: {len(csv_files)}")
        print_info(f"JSON files: {len(json_files)}")

        if csv_files:
            print_success(f"Found {len(csv_files)} CSV files")

            # Get latest file
            latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest_csv.stat().st_mtime)
            print_info(f"Latest CSV: {latest_csv.name}")
            print_info(f"Modified: {mtime}")

            # Check if recent (last 24 hours)
            hours_old = (datetime.now() - mtime).total_seconds() / 3600
            if hours_old < 24:
                print_success(f"Data is recent ({hours_old:.1f} hours old)")
            else:
                print_warning(f"Data is old ({hours_old:.1f} hours old)")
        else:
            print_error("No CSV files found in upwork_dna")

        # Check for recommended_keywords.json
        rec_file = upwork_dna_dir / "recommended_keywords.json"
        if rec_file.exists():
            print_success("recommended_keywords.json exists")
            try:
                with open(rec_file) as f:
                    rec_data = json.load(f)
                print_info(f"Keywords in queue: {len(rec_data.get('keywords', []))}")
            except Exception as e:
                print_error(f"Failed to read recommendations: {e}")
        else:
            print_warning("recommended_keywords.json not found")
    else:
        print_error(f"upwork_dna directory does not exist: {upwork_dna_dir}")

    # ============================================================
    # TEST 2: Check dashboard data directory
    # ============================================================
    print_section("TEST 2: Dashboard Data Directory")

    if dashboard_data_dir.exists():
        print_success(f"Dashboard data directory exists: {dashboard_data_dir}")

        # List CSV files
        csv_files = list(dashboard_data_dir.glob("*.csv"))
        print_info(f"CSV files: {len(csv_files)}")

        if csv_files:
            # Get latest file
            latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest_csv.stat().st_mtime)
            print_info(f"Latest CSV: {latest_csv.name}")
            print_info(f"Modified: {mtime}")

            # Check if recent
            hours_old = (datetime.now() - mtime).total_seconds() / 3600
            if hours_old < 24:
                print_success(f"Data is recent ({hours_old:.1f} hours old)")
            else:
                print_warning(f"Data is old ({hours_old:.1f} hours old)")

            # Sample latest file
            try:
                df = pd.read_csv(latest_csv)
                print_info(f"Rows in latest file: {len(df)}")
                print_info(f"Columns: {list(df.columns)[:5]}...")
            except Exception as e:
                print_error(f"Failed to read CSV: {e}")
        else:
            print_warning("No CSV files in dashboard data directory")
    else:
        print_error(f"Dashboard data directory does not exist")

    # ============================================================
    # TEST 3: Check for file watcher/bridge
    # ============================================================
    print_section("TEST 3: Data Pipeline Bridge")

    bridge_file = Path("/Users/dev/Documents/upworkextension/analist/pipeline/data_bridge.py")
    if bridge_file.exists():
        print_success("Data bridge file exists")
        print_info(f"Location: {bridge_file}")

        # Check if bridge is running
        print_info("Checking for running bridge process...")
        result = os.system("pgrep -f 'data_bridge.py' > /dev/null 2>&1")
        if result == 0:
            print_success("Bridge process is running")
        else:
            print_warning("Bridge process is NOT running")

        # Check for logs
        log_file = upwork_dna_dir / "pipeline_triggers.log"
        if log_file.exists():
            print_success(f"Pipeline log exists: {log_file}")
            with open(log_file) as f:
                lines = f.readlines()
            print_info(f"Log entries: {len(lines)}")
            if lines:
                print_info("Latest log entries:")
                for line in lines[-5:]:
                    print(f"  {line.strip()}")
        else:
            print_warning("No pipeline log found")
    else:
        print_error("Data bridge file not found")

    # ============================================================
    # TEST 4: Create test data
    # ============================================================
    print_section("TEST 4: Create Test Data")

    print_info("Creating test CSV file in upwork_dna...")

    # Create test directory
    test_dir = upwork_dna_dir / "2026-02-07" / "test_keyword_1234567890"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create test CSV
    test_csv = test_dir / "upwork_jobs_test_keyword_1234567890.csv"
    test_data = pd.DataFrame({
        'title': ['Test Job 1', 'Test Job 2', 'Test Job 3'],
        'description': ['Test description 1', 'Test description 2', 'Test description 3'],
        'budget': ['$100', '$200', '$300'],
        'skills': ['python, javascript', 'python, react', 'javascript, html']
    })

    test_data.to_csv(test_csv, index=False)
    print_success(f"Created test file: {test_csv}")

    # Wait for file watcher to detect
    print_info("Waiting 5 seconds for file watcher to detect...")
    time.sleep(5)

    # Check if file was detected
    log_file = upwork_dna_dir / "pipeline_triggers.log"
    if log_file.exists():
        with open(log_file) as f:
            content = f.read()
        if "test_keyword" in content:
            print_success("File watcher detected new file!")
        else:
            print_warning("File watcher did NOT detect new file")
    else:
        print_warning("No pipeline log to check")

    # ============================================================
    # TEST 5: Root cause analysis
    # ============================================================
    print_section("TEST 5: Root Cause Analysis")

    print_info("Analyzing data flow...")

    # Check if data exists in upwork_dna
    upwork_dna_csv = list(upwork_dna_dir.rglob("*.csv"))
    dashboard_csv = list(dashboard_data_dir.glob("*.csv"))

    print(f"\n{Colors.BOLD}Data Summary:{Colors.ENDC}")
    print(f"  ~/upwork_dna/ CSV files: {len(upwork_dna_csv)}")
    print(f"  Dashboard data CSV files: {len(dashboard_csv)}")

    if len(upwork_dna_csv) == 0:
        print_error("\nROOT CAUSE: No data in ~/upwork_dna/")
        print("  → Extension is not scraping or not exporting data")
        print("  → Fix: Check if extension is loaded and scraping is working")
    elif len(dashboard_csv) == 0:
        print_error("\nROOT CAUSE: No data in dashboard directory")
        print("  → Data bridge is not moving files from ~/upwork_dna/")
        print("  → Fix: Start the data bridge pipeline")
    else:
        # Compare modification times
        if upwork_dna_csv:
            latest_upwork = max(upwork_dna_csv, key=lambda f: f.stat().st_mtime)
            mtime_upwork = datetime.fromtimestamp(latest_upwork.stat().st_mtime)

        if dashboard_csv:
            latest_dashboard = max(dashboard_csv, key=lambda f: f.stat().st_mtime)
            mtime_dashboard = datetime.fromtimestamp(latest_dashboard.stat().st_mtime)

            print(f"\n{Colors.BOLD}Latest Data Times:{Colors.ENDC}")
            print(f"  ~/upwork_dna/: {mtime_upwork}")
            print(f"  Dashboard: {mtime_dashboard}")

            if mtime_upwork > mtime_dashboard:
                print_warning("\nROOT CAUSE: Newer data exists in ~/upwork_dna/")
                print("  → Data bridge is not syncing new data to dashboard")
                print("  → Fix: Restart data bridge or manually trigger sync")
            else:
                print_warning("\nROOT CAUSE: No new data since last dashboard update")
                print("  → Extension has not scraped new data")
                print("  → Fix: Check extension queue and trigger new scraping")

    # ============================================================
    # RECOMMENDATIONS
    # ============================================================
    print_section("RECOMMENDATIONS")

    print(f"\n{Colors.BOLD}To Fix Dashboard Data Update Issue:{Colors.ENDC}\n")

    print("1. If extension is not scraping:")
    print("   - Open Chrome and navigate to upwork.com")
    print("   - Open the extension popup")
    print("   - Add keywords to the queue")
    print("   - Start scraping")

    print("\n2. If data bridge is not running:")
    print("   - Run: cd /Users/dev/Documents/upworkextension/analist/pipeline")
    print("   - Run: python3 data_bridge.py")

    print("\n3. To manually sync data:")
    print("   - Copy files from ~/upwork_dna/ to dashboard data directory")
    print("   - Or restart the Electron app")

    print("\n4. To test the pipeline:")
    print("   - Create a test file in ~/upwork_dna/")
    print("   - Check if it appears in the dashboard")

    # ============================================================
    # CLEANUP
    # ============================================================
    print_section("Cleanup")

    cleanup = input(f"\n{Colors.WARNING}Delete test data? (y/n): {Colors.ENDC}").strip().lower()
    if cleanup == 'y':
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print_success("Test data deleted")
    else:
        print_info("Test data retained")

    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Test complete!{Colors.ENDC}\n")

if __name__ == "__main__":
    main()
