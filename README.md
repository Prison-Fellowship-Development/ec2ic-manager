# AWS Connect

A cross-platform GUI application for managing AWS EC2 and RDS connections with support for RDP, SSH, and SSM tunneling.

## Features

- 🖥️ **EC2 Connections** - RDP for Windows instances, SSH for Linux instances
- 🗄️ **RDS Tunneling** - Connect to RDS databases through bastion hosts
- 🔧 **SSM Tunneling** - Create custom port tunnels to EC2-hosted databases
- 🌍 **Multi-Region** - Supports us-east-1 and us-east-2
- 🔐 **AWS SSO** - Integrated SSO login with automatic resource loading
- 📋 **Resource Discovery** - Automatically lists and categorizes EC2 and RDS instances
- 🎯 **Smart Actions** - Right-click context menu for quick connections
- 🔄 **Auto-Detection** - Automatically detects Windows vs Linux platforms
- 💻 **Cross-Platform** - Works on macOS and Windows

## Quick Start

### For Users

**macOS:**
1. Download `AWSConnect-Installer.dmg` from Releases
2. Open the DMG and drag AWS Connect to Applications
3. Launch from Applications folder

**Windows:**
1. Download `AWSConnect-Setup.exe` from Releases
2. Run the installer
3. Launch from Start Menu or Desktop

### For Developers

Run directly:
```bash
python3 AWSConnect.py
```

Build for your platform:

**macOS:**
```bash
./build_macos.sh
```

**Windows:**
```batch
build_windows.bat
```

See [BUILD.md](BUILD.md) or [BUILD_WINDOWS.md](BUILD_WINDOWS.md) for detailed instructions.

## Requirements

### Runtime Requirements
- **macOS** 10.13+ or **Windows** 10+
- **AWS CLI v2** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS SSO** configured with your profiles
- **SSM Session Manager Plugin** - [Installation Guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

### Additional Requirements for RDP (Windows EC2)
- **macOS**: Microsoft Remote Desktop app
- **Windows**: Built-in Remote Desktop Connection (mstsc)

## Usage

### Getting Started

1. **Select Profile** - Choose your AWS profile from the dropdown
2. **Login** - Click "Login" to authenticate via AWS SSO
3. **Auto-Load** - Resources automatically load after successful login
4. **Connect** - Right-click any resource to see connection options
5. **Double-Click** - Quick connect with auto-detected method

### Connection Methods

| Resource Type | Platform | Method | Action |
|--------------|----------|--------|--------|
| EC2 | Windows | RDP | Opens Remote Desktop connection |
| EC2 | Linux | SSH | Opens SSH session in new terminal |
| RDS | Any | Tunnel | Creates SSM tunnel via bastion host |
| EC2 | Any | Custom Tunnel | Creates SSM tunnel with custom port |

### Right-Click Menu Options

**For EC2 Instances:**
- Connect via RDP (Windows only)
- Connect via SSH (Linux only)
- Create SSM Tunnel (Custom Port) - For EC2-hosted databases

**For RDS Instances:**
- Create Database Tunnel - Automatically uses correct port for engine type

### Tunneling

When creating tunnels, the app:
- Automatically finds bastion hosts (instances with "bastion" in name)
- Opens a persistent terminal session
- Assigns a random local port (default range: 9800-9900)
- Shows connection details (localhost:port)

Connect your database client to `localhost:<assigned-port>` while the tunnel is active.

## Building

### macOS
```bash
chmod +x build_macos.sh
./build_macos.sh
```

Outputs:
- `dist/AWSConnect.app` - Application bundle
- `AWSConnect-Installer.dmg` - Installer for distribution

### Windows
```batch
build_windows.bat
build_windows_installer.bat
```

Outputs:
- `dist\AWSConnect.exe` - Standalone executable
- `AWSConnect-Setup.exe` - Installer for distribution

See [BUILD.md](BUILD.md) for macOS or [BUILD_WINDOWS.md](BUILD_WINDOWS.md) for detailed instructions.

## Configuration

Settings can be configured via the Settings button:
- **RDP Client Path** - Path to your RDP client (auto-detected)
- **SSH Client Path** - Path to SSH client (auto-detected)
- **Default Profile** - Profile to select on startup
- **Local Port Range** - Range for tunnel port assignment

## Troubleshooting

### macOS: "App is damaged and can't be opened"
The app isn't code-signed. To bypass:
```bash
xattr -cr /Applications/AWSConnect.app
```

Or: System Preferences > Security & Privacy > Click "Open Anyway"

### Windows: Security Warning
The app isn't code-signed. Click "More info" then "Run anyway"

### "AWS CLI not found"
Ensure AWS CLI v2 is installed and in your PATH. Test with:
```bash
aws --version
```

### "Could not find bastion host"
For RDS tunneling, ensure you have a running EC2 instance with "bastion" in its Name tag.

### Tunnel Connection Fails
- Verify SSM Session Manager plugin is installed
- Check that your IAM role has SSM permissions
- Ensure the target instance has SSM agent running

## Notes

- Uses AWS CLI v2 (Homebrew version may not work correctly)
- Auto-detects Windows vs Linux for EC2 instances using platform metadata
- Automatically finds bastion hosts by searching for "bastion" in Name tags
- Supports multiple AWS profiles with per-profile saved instances
- Tunnels remain active in terminal windows - close terminal to end tunnel
- No Python installation required for end users (bundled in app)
