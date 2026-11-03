@echo off
setlocal
set PORT=8743
set DIR=%~dp0

rem Clear out anything already on this port first — otherwise running this
rem twice (or a server started some other way, e.g. directly via `python
rem tools/dev_server.py`) leaves two servers answering the same port at
rem once, with requests routing unpredictably between an old and a new one.
call "%DIR%stop.bat"

echo Starting Panel Builder server on port %PORT% ...
start "Panel Builder Server" /min cmd /c "python "%DIR%tools\dev_server.py" %PORT%"

timeout /t 1 /nobreak >nul

start "" "http://localhost:%PORT%/modules-hub/index.html"

echo.
echo Server is running in a minimized window titled "Panel Builder Server".
echo Close that window (or run stop.bat) to shut it down.
