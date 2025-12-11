@echo off
REM Build script for AWS Connect Windows executable

echo ==========================================
echo Building AWS Connect for Windows
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.x
    exit /b 1
)

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build the executable using PyInstaller
echo.
echo Building executable with PyInstaller...
echo ----------------------------------------
pyinstaller --clean --noconfirm AWSConnect.spec

REM Check if build was successful
if exist "dist\AWSConnect.exe" (
    echo.
    echo ==========================================
    echo Build Complete!
    echo ==========================================
    echo.
    echo Executable: dist\AWSConnect.exe
    echo.
    echo To test the app:
    echo   dist\AWSConnect.exe
    echo.
    echo To create installer:
    echo   Run build_windows_installer.bat
    echo.
) else (
    echo.
    echo Build failed. Check the output above for errors.
    exit /b 1
)
