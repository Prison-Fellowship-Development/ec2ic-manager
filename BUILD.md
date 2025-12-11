# Building AWS Connect

## Platform-Specific Builds

### macOS
```bash
./build_macos.sh
```

Outputs:
- `dist/AWSConnect.app` - The macOS application
- `AWSConnect-Installer.dmg` - The installer for distribution

### Windows
```batch
build_windows.bat
```

Outputs:
- `dist\AWSConnect.exe` - The Windows executable

See [BUILD_WINDOWS.md](BUILD_WINDOWS.md) for detailed Windows instructions.

---

## First Time Setup

1. **Make the script executable:**
   ```bash
   chmod +x build_macos.sh
   ```

2. **Ensure you have Homebrew installed:**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

The build script will automatically install PyInstaller and create-dmg if needed.

---

## Testing

### Test the app directly:
```bash
open dist/AWSConnect.app
```

### Test the installer:
```bash
open AWSConnect-Installer.dmg
```

---

## Distribution

Share `AWSConnect-Installer.dmg` with users. They simply:
1. Download the DMG
2. Open it
3. Drag the app to Applications folder
4. Launch from Applications

---

## Troubleshooting

### "App is damaged and can't be opened"
This happens because the app isn't signed. To bypass:
```bash
xattr -cr dist/AWSConnect.app
```

Or users can:
1. Go to System Preferences > Security & Privacy
2. Click "Open Anyway" for AWSConnect

### Build fails
Ensure you have:
- Python 3.x installed
- Homebrew installed
- AWS CLI installed

### "create-dmg not found"
The script auto-installs it. If that fails:
```bash
brew install create-dmg
```

---

## What the Build Does

The `build_macos.sh` script:
1. Checks for and installs PyInstaller
2. Checks for and installs create-dmg
3. Cleans previous builds
4. Builds the app using PyInstaller
5. Creates a professional DMG installer with:
   - Drag-and-drop interface
   - Custom app icon
   - Applications folder shortcut
   - Compressed format

---

## Customization

Edit `build_macos.sh` to change:

```bash
APP_NAME="AWSConnect"      # Change app name
DMG_NAME="AWSConnect-Installer"  # Change DMG name
```

---

## Code Signing (Optional)

For wider distribution without security warnings:

1. Get an Apple Developer certificate
2. Sign the app:
   ```bash
   codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/AWSConnect.app
   ```
3. Verify:
   ```bash
   codesign --verify --verbose dist/AWSConnect.app
   ```

---

## File Structure

```
.
├── AWSConnect.py           # Main application
├── AWSConnect.spec         # PyInstaller configuration
├── build_macos.sh          # Build script
├── icon.icns               # macOS icon
├── requirements.txt        # Python dependencies
└── dist/
    └── AWSConnect.app      # Built application
```

---

## Requirements

- **Python 3.x**
- **Homebrew** (for dependencies)
- **AWS CLI** (for the app to function)
- **SSM Session Manager plugin** (for tunneling features)

---

## Notes

- The app includes Python interpreter and all dependencies (~50-100MB)
- First launch may take a few seconds
- Users need AWS CLI installed on their system
- The DMG is compressed (UDZO format) for smaller file size
