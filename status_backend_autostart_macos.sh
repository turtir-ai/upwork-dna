#!/bin/bash
set -euo pipefail

PLIST_NAME="com.upworkdna.backend.api"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
WATCHDOG_PLIST_NAME="com.upworkdna.backend.watchdog"
WATCHDOG_PLIST_PATH="$HOME/Library/LaunchAgents/$WATCHDOG_PLIST_NAME.plist"
DASHBOARD_PLIST_NAME="com.upworkdna.dashboard"
DASHBOARD_PLIST_PATH="$HOME/Library/LaunchAgents/$DASHBOARD_PLIST_NAME.plist"
USER_ID="$(id -u)"

if [ ! -f "$PLIST_PATH" ]; then
  echo "LaunchAgent not installed: $PLIST_PATH"
  exit 1
fi

echo "LaunchAgent file (backend):"
echo "  $PLIST_PATH"
if [ -f "$WATCHDOG_PLIST_PATH" ]; then
  echo "LaunchAgent file (watchdog):"
  echo "  $WATCHDOG_PLIST_PATH"
fi
if [ -f "$DASHBOARD_PLIST_PATH" ]; then
  echo "LaunchAgent file (dashboard):"
  echo "  $DASHBOARD_PLIST_PATH"
fi
echo
launchctl print "gui/$USER_ID/$PLIST_NAME" | head -60 || true
echo
if [ -f "$WATCHDOG_PLIST_PATH" ]; then
  launchctl print "gui/$USER_ID/$WATCHDOG_PLIST_NAME" | head -60 || true
fi
echo
if [ -f "$DASHBOARD_PLIST_PATH" ]; then
  launchctl print "gui/$USER_ID/$DASHBOARD_PLIST_NAME" | head -60 || true
fi
echo
echo "Health:"
curl -sS -m 5 "http://127.0.0.1:8000/health" || true
echo
echo "Dashboard health:"
curl -sS -m 5 "http://127.0.0.1:8501/_stcore/health" || true
echo
