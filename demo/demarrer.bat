@echo off
chcp 65001 >nul
title Badgeage Proximy - démonstration
cd /d "%~dp0.."

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker ne répond pas. Lancez Docker Desktop ^(ou Rancher Desktop^), attendez qu'il soit prêt, puis relancez ce fichier.
  pause
  exit /b 1
)

echo Démarrage de la démonstration. La première fois, comptez quelques minutes...
docker compose -f docker-compose.demo.yml up -d --build
if errorlevel 1 (
  echo Le démarrage a échoué. Copiez le message ci-dessus pour le transmettre.
  pause
  exit /b 1
)

echo Attente de l'application...
set /a essais=0
:attente
set /a essais+=1
if %essais% gtr 60 (
  echo L'application ne répond pas. Consultez les journaux : docker compose -f docker-compose.demo.yml logs app
  pause
  exit /b 1
)
timeout /t 3 /nobreak >nul
curl -s -o nul -f http://localhost:8080/sante
if errorlevel 1 goto attente

start "" http://localhost:8080
echo.
echo L'application est ouverte dans votre navigateur : http://localhost:8080
echo.
echo   Administrateur : ADMIN
echo   RH             : RH01
echo   Manager        : M001  (Sophie Lefèvre)
echo   Salariés       : S001 à S004
echo   Mot de passe   : Proximy2026 (le même pour tous)
echo.
pause
