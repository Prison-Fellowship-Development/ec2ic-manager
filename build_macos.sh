#!/bin/bash

# Build script for AWS Connect macOS app and DMG installer

APP_NAME="AWSConnect"
DMG_NAME="AWSConnect-Installer"

echo "=========================================="
echo "Building AWS Connect"
echo "=========================================="
echo ""

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo "create-dmg not found. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Error: Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install create-dmg
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist dmg_temp
rm -f "${DMG_NAME}.dmg"

# Build the app using PyInstaller
echo ""
echo "Step 1/2: Building app with PyInstaller..."
echo "----------------------------------------"
pyinstaller --clean --noconfirm AWSConnect.spec

# Check if build was successful
if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo ""
    echo "❌ App build failed. Check the output above for errors."
    exit 1
fi

echo ""
echo "✅ App built successfully!"
echo ""

# Create DMG installer
echo "Step 2/2: Creating DMG installer..."
echo "----------------------------------------"

# Create a clean temporary directory with only the .app
mkdir -p dmg_temp
cp -r "dist/${APP_NAME}.app" dmg_temp/

# Create the DMG with drag-and-drop interface
create-dmg \
  --volname "${APP_NAME}" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 175 190 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 425 190 \
  "${DMG_NAME}.dmg" \
  "dmg_temp/" 2>/dev/null

# Clean up temp directory
rm -rf dmg_temp

# Check if DMG was created successfully
if [ ! -f "${DMG_NAME}.dmg" ]; then
    echo ""
    echo "❌ DMG creation failed!"
    exit 1
fi

echo ""
echo "✅ DMG created successfully!"
echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "📦 App:       dist/${APP_NAME}.app"
echo "💿 Installer: ${DMG_NAME}.dmg"
echo ""

# Get file size
DMG_SIZE=$(du -h "${DMG_NAME}.dmg" | cut -f1)
echo "DMG size: ${DMG_SIZE}"
echo ""
echo "To test the app:"
echo "  open dist/${APP_NAME}.app"
echo ""
echo "To test the installer:"
echo "  open ${DMG_NAME}.dmg"
echo ""
echo "To distribute:"
echo "  Share ${DMG_NAME}.dmg with users"
echo ""
