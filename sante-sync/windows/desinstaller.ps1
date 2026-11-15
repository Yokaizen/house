# Désinstalle la collecte (tâche planifiée + programme). Les données restent.
$ErrorActionPreference = 'Continue'
Unregister-ScheduledTask -TaskName 'SanteSync - collecte quotidienne' -Confirm:$false
$AppDir = Join-Path $env:LOCALAPPDATA 'SanteSync'
Remove-Item -Recurse -Force (Join-Path $AppDir 'venv'), (Join-Path $AppDir 'app') -ErrorAction SilentlyContinue
Write-Host "Collecte désinstallée. Vos données sont intactes. (Journaux et état : $AppDir)"
