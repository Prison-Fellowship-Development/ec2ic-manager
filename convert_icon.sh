#!/bin/bash

# Convert PNG to ICNS for macOS app icon

PNG_FILE="aws_icon.png"
ICONSET="icon.iconset"
ICNS_FILE="icon.icns"

echo "Converting ${PNG_FILE} to ${ICNS_FILE}..."

# Check if PNG exists
if [ ! -f "${PNG_FILE}" ]; then
    echo "❌ Error: ${PNG_FILE} not found!"
    exit 1
fi

# Create iconset directory
mkdir -p "${ICONSET}"

# Generate different sizes for the iconset
# macOS requires multiple sizes for different contexts
sips -z 16 16     "${PNG_FILE}" --out "${ICONSET}/icon_16x16.png"
sips -z 32 32     "${PNG_FILE}" --out "${ICONSET}/icon_16x16@2x.png"
sips -z 32 32     "${PNG_FILE}" --out "${ICONSET}/icon_32x32.png"
sips -z 64 64     "${PNG_FILE}" --out "${ICONSET}/icon_32x32@2x.png"
sips -z 128 128   "${PNG_FILE}" --out "${ICONSET}/icon_128x128.png"
sips -z 256 256   "${PNG_FILE}" --out "${ICONSET}/icon_128x128@2x.png"
sips -z 256 256   "${PNG_FILE}" --out "${ICONSET}/icon_256x256.png"
sips -z 512 512   "${PNG_FILE}" --out "${ICONSET}/icon_256x256@2x.png"
sips -z 512 512   "${PNG_FILE}" --out "${ICONSET}/icon_512x512.png"
sips -z 1024 1024 "${PNG_FILE}" --out "${ICONSET}/icon_512x512@2x.png"

# Convert iconset to icns
iconutil -c icns "${ICONSET}" -o "${ICNS_FILE}"

# Clean up
rm -rf "${ICONSET}"

if [ -f "${ICNS_FILE}" ]; then
    echo "✅ Icon converted successfully!"
    echo "📦 Output: ${ICNS_FILE}"
    
    # Show file size
    SIZE=$(du -h "${ICNS_FILE}" | cut -f1)
    echo "Size: ${SIZE}"
else
    echo "❌ Icon conversion failed!"
    exit 1
fi
