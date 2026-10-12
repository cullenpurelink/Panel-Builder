@echo off
echo Stopping the "Panel Builder Server" window...
taskkill /FI "WINDOWTITLE eq Panel Builder Server*" /T /F >nul 2>&1
echo Done.
