@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\create_shortcut.ps1"
echo.
echo ==========================================================
echo Done! Icon Desktop has been created/updated with ios_optimize_icont.png.
echo ==========================================================
pause
