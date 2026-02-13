#!/bin/bash
# Upwork DNA - macOS App Installer Script
# Creates a proper .app bundle and adds to Applications

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="Upwork DNA"
VERSION="2.1.0"
IDENTIFIER="com.upworkdna.app"

echo "🚀 Creating Upwork DNA.app bundle..."

# Create app bundle structure
APP_BUNDLE="$HOME/Desktop/$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
EXECUTABLE="$MACOS/$APP_NAME"

echo "📁 Creating app bundle structure..."
rm -rf "$APP_BUNDLE"
mkdir -p "$MACOS"
mkdir -p "$RESOURCES"

# Create Info.plist
echo "📝 Creating Info.plist..."
cat > "$CONTENTS/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>Upwork DNA</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$IDENTIFIER</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF

# Create the launcher script
echo "📝 Creating launcher script..."
cat > "$EXECUTABLE" << 'EOF'
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
  echo "📦 Installing Node dependencies..."
  if command -v npm >/dev/null 2>&1; then
    npm install --silent --no-audit --no-fund
  else
    echo "❌ npm not found. Install Node.js first."
    exit 1
  fi
fi

# Ensure Electron runs in app mode (not Node compatibility mode).
unset ELECTRON_RUN_AS_NODE

# IMPORTANT: app root must be Resources (contains package.json/main.js), not Contents.
exec "$ELECTRON_EXE" "$RESOURCES_DIR" "$@"
EOF

chmod +x "$EXECUTABLE"

# Copy app assets
echo "🎨 Copying app assets..."
cp -r "$SCRIPT_DIR"/* "$RESOURCES/" 2>/dev/null || true

# Create a simple icon placeholder
echo "🎨 Creating app icon..."
cat > "$RESOURCES/icon.png" << 'EOF'
iVBORw0KGgoAAAANSUhEUgAAAIAAAAACAYAAAADb/1H+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAG3RBTNUAAB8g
l5IJfwMABwUQwAMQzEABw1zABw2jABw3DABw4EABw5DABw6TABw7UABw8jABw9TABw+TABw/UAB
xCjABxDkABxETABxFUABxGTABxHUABxJTABxKUABxLTABxMUABxNUABxOVABxPUABxQTABxRTABxSUAB
xTTABxVTABxWUABxXUABxYUABxZUABxaTABxbTABx/TABxcUABxdTABxeTABxfTABxgUABxhTAB
ABwAAADsAAAAABAAEAAEABAAEAAABACAAAEAAQABAAEAAQACAAABAAEAAgABAAEAAQABAAEAAQ
ACAAABAAEAAgABAAEAAQABAAEAAQA...
EOF

# Set proper permissions
echo "🔒 Setting permissions..."
xattr -cr "$APP_BUNDLE" 2>/dev/null || true

echo "✅ App bundle created: $APP_BUNDLE"
echo ""
echo "📦 Moving to Applications folder..."
mv "$APP_BUNDLE" "/Applications/$APP_NAME.app"

echo "✅ Upwork DNA.app installed to /Applications/"
echo ""
echo "🚀 You can now launch Upwork DNA from:"
echo "   1. Applications folder (Cmd+Shift+A)"
echo "   2. Spotlight search (Cmd+Space, type 'Upwork DNA')"
echo "   3. Dock (if you drag it there)"
EOF
chmod +x /Users/dev/Documents/upworkextension/electron-app/install_macos.sh
