@echo off
setlocal
set PORT=8743
set DIR=%~dp0

echo Starting Panel Builder server on port %PORT% ...
start "Panel Builder Server" /min cmd /c "cd /d "%DIR%" && python -m http.server %PORT%"

timeout /t 1 /nobreak >nul

start "" "http://localhost:%PORT%/modules-hub/index.html"

echo.
echo Server is running in a minimized window titled "Panel Builder Server".
echo Close that window (or run stop.bat) to shut it down.
