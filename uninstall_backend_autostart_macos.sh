#!/bin/bash
set -euo pipefail

PLIST_NAME="com.upworkdna.backend.api"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
WATCHDOG_PLIST_NAME="com.upworkdna.backend.watchdog"
WATCHDOG_PLIST_PATH="$HOME/Library/LaunchAgents/$WATCHDOG_PLIST_NAME.plist"
DASHBOARD_PLIST_NAME="com.upworkdna.dashboard"
DASHBOARD_PLIST_PATH="$HOME/Library/LaunchAgents/$DASHBOARD_PLIST_NAME.plist"
USER_ID="$(id -u)"

if [ -f "$PLIST_PATH" ]; then
  launchctl bootout "gui/$USER_ID" "$PLIST_PATH" >/dev/null 2>&1 || true
  rm -f "$PLIST_PATH"
fi

launchctl disable "gui/$USER_ID/$PLIST_NAME" >/dev/null 2>&1 || true
if [ -f "$WATCHDOG_PLIST_PATH" ]; then
  launchctl bootout "gui/$USER_ID" "$WATCHDOG_PLIST_PATH" >/dev/null 2>&1 || true
  rm -f "$WATCHDOG_PLIST_PATH"
fi

launchctl disable "gui/$USER_ID/$WATCHDOG_PLIST_NAME" >/dev/null 2>&1 || true

if [ -f "$DASHBOARD_PLIST_PATH" ]; then
  launchctl bootout "gui/$USER_ID" "$DASHBOARD_PLIST_PATH" >/dev/null 2>&1 || true
  rm -f "$DASHBOARD_PLIST_PATH"
fi

launchctl disable "gui/$USER_ID/$DASHBOARD_PLIST_NAME" >/dev/null 2>&1 || true

echo "Removed LaunchAgent: $PLIST_PATH"
echo "Removed LaunchAgent: $WATCHDOG_PLIST_PATH"
echo "Removed LaunchAgent: $DASHBOARD_PLIST_PATH"
