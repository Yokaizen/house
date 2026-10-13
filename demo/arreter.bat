@echo off
chcp 65001 >nul
cd /d "%~dp0.."
docker compose -f docker-compose.demo.yml down
echo Démonstration arrêtée. Les données sont conservées pour la prochaine fois.
pause
