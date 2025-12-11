@echo off
REM Build Windows installer using Inno Setup

echo ==========================================
echo Creating AWS Connect Installer
echo ==========================================
echo.

REM Check if executable exists
if not exist "dist\AWSConnect.exe" (
    echo Error: AWSConnect.exe not found!
    echo Please run build_windows.bat first.
    exit /b 1
)

REM Check if Inno Setup is installed
set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%INNO_PATH%" (
    echo.
    echo Inno Setup not found!
    echo.
    echo Please install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, run this script again.
    exit /b 1
)

REM Build the installer
echo Building installer...
"%INNO_PATH%" installer.iss

if exist "AWSConnect-Setup.exe" (
    echo.
    echo ==========================================
    echo Installer Created Successfully!
    echo ==========================================
    echo.
    echo Installer: AWSConnect-Setup.exe
    echo.
    echo To test:
    echo   Run AWSConnect-Setup.exe
    echo.
    echo To distribute:
    echo   Share AWSConnect-Setup.exe with users
    echo.
) else (
    echo.
    echo Installer creation failed!
    exit /b 1
)
