#!/bin/bash
set -euo pipefail

PROJECT_DIR="/Users/dev/Documents/upworkextension"
BACKEND_DIR="$PROJECT_DIR/backend"
ANALIST_DIR="$PROJECT_DIR/analist"
PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
ANALIST_PYTHON_BIN="$ANALIST_DIR/venv/bin/python"
WATCHDOG_SCRIPT="$PROJECT_DIR/backend_watchdog.py"
PLIST_NAME="com.upworkdna.backend.api"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
WATCHDOG_PLIST_NAME="com.upworkdna.backend.watchdog"
WATCHDOG_PLIST_PATH="$HOME/Library/LaunchAgents/$WATCHDOG_PLIST_NAME.plist"
DASHBOARD_PLIST_NAME="com.upworkdna.dashboard"
DASHBOARD_PLIST_PATH="$HOME/Library/LaunchAgents/$DASHBOARD_PLIST_NAME.plist"
LOG_OUT="$PROJECT_DIR/orchestrator.autostart.log"
LOG_ERR="$PROJECT_DIR/orchestrator.autostart.err.log"
WATCHDOG_LOG_OUT="$PROJECT_DIR/backend.watchdog.log"
WATCHDOG_LOG_ERR="$PROJECT_DIR/backend.watchdog.err.log"
DASHBOARD_LOG_OUT="$PROJECT_DIR/dashboard.autostart.log"
DASHBOARD_LOG_ERR="$PROJECT_DIR/dashboard.autostart.err.log"
USER_ID="$(id -u)"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python not found: $PYTHON_BIN"
  exit 1
fi
if [ ! -x "$ANALIST_PYTHON_BIN" ]; then
  echo "Analist Python not found: $ANALIST_PYTHON_BIN"
  exit 1
fi
if [ ! -f "$WATCHDOG_SCRIPT" ]; then
  echo "Watchdog script not found: $WATCHDOG_SCRIPT"
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_NAME</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>-m</string>
    <string>uvicorn</string>
    <string>main:app</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>8000</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$BACKEND_DIR</string>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$LOG_OUT</string>
  <key>StandardErrorPath</key>
  <string>$LOG_ERR</string>
</dict>
</plist>
EOF

cat > "$WATCHDOG_PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$WATCHDOG_PLIST_NAME</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$WATCHDOG_SCRIPT</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$WATCHDOG_LOG_OUT</string>
  <key>StandardErrorPath</key>
  <string>$WATCHDOG_LOG_ERR</string>
</dict>
</plist>
EOF

cat > "$DASHBOARD_PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$DASHBOARD_PLIST_NAME</string>

  <key>ProgramArguments</key>
  <array>
    <string>$ANALIST_PYTHON_BIN</string>
    <string>-m</string>
    <string>streamlit</string>
    <string>run</string>
    <string>dashboard/app.py</string>
    <string>--server.headless</string>
    <string>true</string>
    <string>--server.address</string>
    <string>127.0.0.1</string>
    <string>--server.port</string>
    <string>8501</string>
    <string>--browser.gatherUsageStats</string>
    <string>false</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$ANALIST_DIR</string>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$DASHBOARD_LOG_OUT</string>
  <key>StandardErrorPath</key>
  <string>$DASHBOARD_LOG_ERR</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$USER_ID" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$USER_ID" "$PLIST_PATH"
launchctl enable "gui/$USER_ID/$PLIST_NAME"
launchctl kickstart -k "gui/$USER_ID/$PLIST_NAME"

launchctl bootout "gui/$USER_ID" "$WATCHDOG_PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$USER_ID" "$WATCHDOG_PLIST_PATH"
launchctl enable "gui/$USER_ID/$WATCHDOG_PLIST_NAME"
launchctl kickstart -k "gui/$USER_ID/$WATCHDOG_PLIST_NAME"

launchctl bootout "gui/$USER_ID" "$DASHBOARD_PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$USER_ID" "$DASHBOARD_PLIST_PATH"
launchctl enable "gui/$USER_ID/$DASHBOARD_PLIST_NAME"
launchctl kickstart -k "gui/$USER_ID/$DASHBOARD_PLIST_NAME"

echo "Installed LaunchAgent: $PLIST_PATH"
echo "Installed LaunchAgent: $WATCHDOG_PLIST_PATH"
echo "Installed LaunchAgent: $DASHBOARD_PLIST_PATH"
echo "Check status:"
echo "  launchctl print gui/$USER_ID/$PLIST_NAME | head -40"
echo "  launchctl print gui/$USER_ID/$WATCHDOG_PLIST_NAME | head -40"
echo "  launchctl print gui/$USER_ID/$DASHBOARD_PLIST_NAME | head -40"
echo "Health:"
echo "  curl http://127.0.0.1:8000/health"
echo "Dashboard health:"
echo "  curl http://127.0.0.1:8501/_stcore/health"
