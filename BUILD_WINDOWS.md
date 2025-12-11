# Building AWS Connect for Windows

## Quick Start

```batch
build_windows.bat
```

This creates `dist\AWSConnect.exe` - a standalone Windows executable.

## Creating an Installer

```batch
build_windows_installer.bat
```

This creates `AWSConnect-Setup.exe` - a professional Windows installer.

---

## Prerequisites

1. **Python 3.x** for Windows
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **PyInstaller** (auto-installed by build script)

3. **Inno Setup** (for installer creation)
   - Download from: https://jrsoftware.org/isdl.php
   - Only needed if you want to create an installer

---

## Build Steps

### Step 1: Build the Executable

```batch
build_windows.bat
```

This will:
- Install PyInstaller if needed
- Clean previous builds
- Build `AWSConnect.exe`

**Output:** `dist\AWSConnect.exe`

### Step 2: Create Installer (Optional)

```batch
build_windows_installer.bat
```

This will:
- Check for Inno Setup
- Create a professional installer
- Output `AWSConnect-Setup.exe`

---

## Testing

### Test the executable:
```batch
dist\AWSConnect.exe
```

### Test the installer:
```batch
AWSConnect-Setup.exe
```

---

## Distribution

### Option 1: Distribute the Executable
- Share `dist\AWSConnect.exe`
- Users can run it directly (no installation needed)
- ~50-100MB file size

### Option 2: Distribute the Installer (Recommended)
- Share `AWSConnect-Setup.exe`
- Professional installation experience
- Creates Start Menu shortcuts
- Includes uninstaller
- ~50-100MB file size

---

## What Users Need

Users must have installed:
- **AWS CLI** - https://aws.amazon.com/cli/
- **SSM Session Manager Plugin** - For tunneling features
  - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

---

## Troubleshooting

### "Python not found"
Install Python 3.x and make sure it's in your PATH:
```batch
python --version
```

### "PyInstaller not found"
The build script auto-installs it. If that fails:
```batch
pip install pyinstaller
```

### "Inno Setup not found"
Download and install from: https://jrsoftware.org/isdl.php

Default installation path: `C:\Program Files (x86)\Inno Setup 6\`

### Build fails
- Ensure Python 3.x is installed
- Ensure pip is working: `pip --version`
- Try running as Administrator

---

## File Structure

```
dist\
├── AWSConnect.exe          # Main executable
└── _internal\              # Dependencies (auto-created by PyInstaller)
    ├── Python DLLs
    └── Other dependencies
```

---

## Customization

### Change app name:
Edit `AWSConnect.spec`:
```python
name='YourAppName',
```

### Change installer name:
Edit `installer.iss`:
```ini
#define MyAppName "Your App Name"
```

---

## Notes

- The executable includes Python and all dependencies
- No Python installation required on user machines
- First launch may take a few seconds
- Windows Defender may scan the file on first run
- The app is not code-signed (users may see security warnings)

---

## Code Signing (Optional)

To remove security warnings, sign the executable:

1. Get a code signing certificate
2. Use `signtool.exe` (part of Windows SDK):
   ```batch
   signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\AWSConnect.exe
   ```

---

## Comparison: macOS vs Windows

| Feature | macOS | Windows |
|---------|-------|---------|
| Build Script | `build_macos.sh` | `build_windows.bat` |
| Output | `.app` bundle + `.dmg` | `.exe` + installer |
| Icon Format | `.icns` | `.ico` |
| Installer | DMG (drag-drop) | Inno Setup |
| File Size | ~50-100MB | ~50-100MB |
