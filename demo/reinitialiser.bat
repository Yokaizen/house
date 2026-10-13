@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Toutes les données de la démonstration vont être effacées et rechargées.
choice /m "Continuer"
if errorlevel 2 exit /b 0
docker compose -f docker-compose.demo.yml exec app python -m app.demo --forcer
echo Terminé. Reconnectez-vous dans le navigateur.
pause
