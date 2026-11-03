@echo off
rem Kills whatever is actually listening on port 8743, rather than matching
rem on the "Panel Builder Server" window title — a server started any other
rem way (directly via `python tools/dev_server.py`, from an AI assistant's
rem shell, etc.) has no such title and was never stopped by the old version
rem of this script, silently leaving stray/duplicate servers behind.
echo Stopping whatever is listening on port 8743...
setlocal enabledelayedexpansion
set found=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8743 " ^| findstr "LISTENING"') do (
    echo   killing PID %%p
    taskkill /PID %%p /F >nul 2>&1
    set found=1
)
if "!found!"=="0" (
    echo Nothing was listening on port 8743.
) else (
    echo Done.
)
