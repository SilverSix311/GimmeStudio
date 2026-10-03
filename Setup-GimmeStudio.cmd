@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-GimmeStudio.ps1" %*
if errorlevel 1 (echo Setup failed. See the message above. & pause & exit /b 1)
pause
