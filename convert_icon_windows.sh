#!/bin/bash

# Convert PNG to ICO for Windows app icon

PNG_FILE="aws_icon.png"
ICO_FILE="icon.ico"

echo "Converting ${PNG_FILE} to ${ICO_FILE}..."

# Check if PNG exists
if [ ! -f "${PNG_FILE}" ]; then
    echo "❌ Error: ${PNG_FILE} not found!"
    exit 1
fi

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo "ImageMagick not found. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Error: Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install imagemagick
fi

# Create ICO file with multiple sizes
# Windows ICO format supports multiple resolutions in one file
echo "Creating multi-resolution ICO file..."
convert "${PNG_FILE}" -define icon:auto-resize=256,128,64,48,32,16 "${ICO_FILE}"

if [ -f "${ICO_FILE}" ]; then
    echo "✅ Icon converted successfully!"
    echo "📦 Output: ${ICO_FILE}"
    
    # Show file size
    SIZE=$(du -h "${ICO_FILE}" | cut -f1)
    echo "Size: ${SIZE}"
    
    # Show included sizes
    echo ""
    echo "Included icon sizes:"
    identify "${ICO_FILE}" 2>/dev/null | awk '{print "  - " $3}'
else
    echo "❌ Icon conversion failed!"
    exit 1
fi
