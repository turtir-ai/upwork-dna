#!/bin/bash
# Fix the Upwork DNA launcher script

APP_PATH="/Applications/Upwork DNA.app"
EXECUTABLE="$APP_PATH/Contents/MacOS/Upwork DNA"

echo "🔧 Fixing Upwork DNA launcher..."

# Create proper launcher script
cat > "$EXECUTABLE" << 'LAUNCHER_EOF'
#!/bin/bash
# Upwork DNA Launcher (macOS .app bundle)

set -e

MACOS_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$MACOS_DIR/../Resources"
ELECTRON_EXE="$RESOURCES_DIR/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"

if [ ! -d "$RESOURCES_DIR" ]; then
  echo "❌ Resources directory not found: $RESOURCES_DIR"
  exit 1
fi

cd "$RESOURCES_DIR"

if [ ! -f "$ELECTRON_EXE" ]; then
  echo "❌ Electron executable not found: $ELECTRON_EXE"
  echo "   Reinstall dependencies with: cd '$RESOURCES_DIR' && npm install"
  exit 1
fi

# Ensure Electron runs in app mode (not Node compatibility mode).
unset ELECTRON_RUN_AS_NODE

# IMPORTANT: app root must be Resources (contains package.json/main.js), not Contents.
exec "$ELECTRON_EXE" "$RESOURCES_DIR" "$@"
LAUNCHER_EOF

chmod +x "$EXECUTABLE"

echo "✅ Launcher fixed!"
echo ""
echo "📦 App location: $APP_PATH"
echo ""
echo "🚀 To launch:"
echo "   1. Open Applications folder (Cmd+Shift+A)"
echo "   2. Double-click 'Upwork DNA'"
echo "   3. Or use Spotlight: Cmd+Space → 'Upwork DNA'"
