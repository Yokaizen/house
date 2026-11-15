@echo off
rem Double-cliquez sur ce fichier pour installer (ou mettre a jour) la collecte sante.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\install.ps1" %*
echo.
pause
