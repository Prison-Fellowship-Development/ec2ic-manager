# -*- mode: python ; coding: utf-8 -*-
# Cross-platform spec file for AWS Connect (macOS and Windows)

import sys

block_cipher = None

a = Analysis(
    ['AWSConnect.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.'), ('icon.icns', '.')],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.font'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Determine icon based on platform
icon_file = 'icon.ico' if sys.platform == 'win32' else 'icon.icns'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AWSConnect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True if sys.platform == 'darwin' else False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

# macOS app bundle (only on macOS)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='AWSConnect.app',
        icon='icon.icns',
        bundle_identifier='com.awstools.awsconnect',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleName': 'AWS Connect',
            'CFBundleDisplayName': 'AWS Connect',
            'CFBundleShortVersionString': '1.2.0',
            'CFBundleVersion': '1.2.0',
            'NSHighResolutionCapable': True,
        },
    )
