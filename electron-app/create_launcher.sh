#!/bin/bash
# Upwork DNA Launcher - Fixed for macOS app bundle

set -e

# Get the real path to the Resources directory
SCRIPT_PATH="$0"
while [ -h "$SCRIPT_PATH" ]; do
    SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
done

RESOURCES_DIR="$(dirname "$SCRIPT_PATH")/../Resources"
PARENT_DIR="$(dirname "$RESOURCES_DIR")/.."

# Change to the Resources directory where files are
cd "$RESOURCES_DIR" || exit 1

# Create log directory
mkdir -p ~/Library/Logs/UpworkDNA
LOG_FILE="$HOME/Library/Logs/UpworkDNA/startup.log"

echo "🚀 Starting Upwork DNA..." | tee -a "$LOG_FILE"
echo "   Date: $(date)" | tee -a "$LOG_FILE"
echo "   Resources: $RESOURCES_DIR" | tee -a "$LOG_FILE"
echo "   Working: $(pwd)" | tee -a "$LOG_FILE"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found" | tee -a "$LOG_FILE"
    echo "   Installing Node.js via Homebrew..." | tee -a "$LOG_FILE"
    brew install node
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..." | tee -a "$LOG_FILE"
    npm install --silent --no-audit --no-fund 2>&1 | tee -a "$LOG_FILE"
fi

# Check if Electron is installed
if [ ! -d "node_modules/electron" ]; then
    echo "❌ Electron not installed" | tee -a "$LOG_FILE"
    exit 1
fi

# Find Electron executable
ELECTRON_EXE=""
if [ -d "node_modules/electron/dist" ]; then
    ELECTRON_EXE="node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
elif [ -d "node_modules/.bin/electron" ]; then
    ELECTRON_EXE="node_modules/.bin/electron"
fi

if [ -z "$ELECTRON_EXE" ] || [ ! -f "$ELECTRON_EXE" ]; then
    echo "⚠️  Electron executable not found, using node directly" | tee -a "$LOG_FILE"
    # Start Electron using npx
    npx electron . > /tmp/upwork_dna.log 2>&1 &
else
    echo "✅ Using Electron: $ELECTRON_EXE" | tee -a "$LOG_FILE"
    unset ELECTRON_RUN_AS_NODE
    # Start Electron app directly
    "$ELECTRON_EXE" . > /tmp/upwork_dna.log 2>&1 &
fi

# Wait a moment to ensure it started
sleep 2

# Check if process is running
if pgrep -f "Electron.*Upwork DNA" > /dev/null || pgrep -f "node.*electron" > /dev/null; then
    echo "✅ Upwork DNA started successfully!" | tee -a "$LOG_FILE"
else
    echo "⚠️  Check logs for issues: $LOG_FILE" | tee -a "$LOG_FILE"
fi
