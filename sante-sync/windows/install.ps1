# Installation de la collecte quotidienne des données santé (Windows).
# Sans droits administrateur. Relançable sans risque : met à jour l'installation.
param(
    [string]$DataDir = "",
    [string]$RunAt = "08:30",
    [switch]$SansCollecte
)
$ErrorActionPreference = 'Stop'
$TaskName = 'SanteSync - collecte quotidienne'
$Src      = Split-Path -Parent $PSScriptRoot
$AppDir   = Join-Path $env:LOCALAPPDATA 'SanteSync'
$ICloud   = Join-Path $env:USERPROFILE 'iCloudDrive'

function Etape($t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Stop-Avec($t) { Write-Host ""; Write-Host "ARRÊT : $t" -ForegroundColor Red; exit 1 }

Etape "Vérification d'iCloud Drive"
if (-not $DataDir) {
    if (-not (Test-Path $ICloud)) {
        Stop-Avec "Le dossier iCloud Drive est introuvable ($ICloud).`n  Installez « iCloud pour Windows » depuis le Microsoft Store, connectez-vous avec votre identifiant Apple,`n  cochez « iCloud Drive », puis relancez INSTALLER.cmd."
    }
    $DataDir = Join-Path $ICloud 'Sante'
}
Write-Host "  Données : $DataDir"
Write-Host "  Code    : $AppDir"

Etape "Copie du programme (hors du dossier synchronisé)"
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
$AppCode = Join-Path $AppDir 'app'
if (Test-Path $AppCode) { Remove-Item -Recurse -Force $AppCode }
New-Item -ItemType Directory -Force -Path $AppCode | Out-Null
foreach ($item in @('sante_sync', 'windows', 'pyproject.toml')) {
    Copy-Item -Recurse -Force (Join-Path $Src $item) $AppCode
}
Get-ChildItem -Recurse $AppCode | Unblock-File -ErrorAction SilentlyContinue

Etape "Installation de Python (outil uv, dans votre profil, sans droits administrateur)"
$uv = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
if (-not (Test-Path $uv)) {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { $uv = $cmd.Source }
    else {
        powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
        if (-not (Test-Path $uv)) { Stop-Avec "L'installation de uv a échoué (connexion Internet ?)." }
    }
}
$Venv = Join-Path $AppDir 'venv'
& $uv venv --allow-existing --python 3.12 $Venv
if ($LASTEXITCODE -ne 0) { Stop-Avec "Création de l'environnement Python impossible." }
$Py  = Join-Path $Venv 'Scripts\python.exe'
$Pyw = Join-Path $Venv 'Scripts\pythonw.exe'
& $uv pip install --python $Py --reinstall-package sante-sync $AppCode
if ($LASTEXITCODE -ne 0) { Stop-Avec "Installation du programme impossible." }

Etape "Configuration"
& $Py -m sante_sync configurer --data-dir $DataDir --heure $RunAt
& $Py -m sante_sync docs

Etape "Raccourcis de maintenance"
$cmds = @{
    'Collecter maintenant.cmd' = "@echo off`r`n`"$Py`" -m sante_sync collecte --force -v`r`n`"$Py`" -m sante_sync statut`r`npause`r`n";
    'Historique complet.cmd'   = "@echo off`r`necho Deposez d'abord export.zip (Apple Sante) dans le dossier import_manuel.`r`n`"$Py`" -m sante_sync historique -v`r`npause`r`n";
    'Statut.cmd'               = "@echo off`r`n`"$Py`" -m sante_sync statut`r`n`"$Py`" -m sante_sync diagnostic`r`npause`r`n";
}
foreach ($k in $cmds.Keys) {
    [IO.File]::WriteAllText((Join-Path $AppDir $k), $cmds[$k], [Text.Encoding]::Default)
}

Etape "Tâche planifiée (chaque jour à $RunAt, au réveil et à l'ouverture de session)"
$user  = "$env:USERDOMAIN\$env:USERNAME"
$start = (Get-Date).ToString('yyyy-MM-dd') + "T$($RunAt):00"
$h, $m = $RunAt.Split(':')
$minutesTo22h = [int][Math]::Max(60, (22 * 60) - ([int]$h * 60 + [int]$m))
$repDuration = 'PT{0}H{1}M' -f [int][Math]::Floor($minutesTo22h / 60), ($minutesTo22h % 60)
$esc = [Security.SecurityElement]
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Collecte des données santé (Apple Santé via Health Auto Export) vers $($esc::Escape($DataDir)). Un seul passage réussi par jour.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$start</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
      <Repetition><Interval>PT1H</Interval><Duration>$repDuration</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
    </CalendarTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$($esc::Escape($user))</UserId>
      <Delay>PT3M</Delay>
    </LogonTrigger>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled>
      <StateChange>SessionUnlock</StateChange>
      <UserId>$($esc::Escape($user))</UserId>
      <Delay>PT2M</Delay>
    </SessionStateChangeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$($esc::Escape($user))</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$($esc::Escape($Pyw))</Command>
      <Arguments>-m sante_sync collecte</Arguments>
      <WorkingDirectory>$($esc::Escape($AppDir))</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@
Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null
$t = Get-ScheduledTask -TaskName $TaskName
Write-Host "  Tâche installée : $($t.TaskName) ($($t.State))"

Etape "Notification de test"
& $Py -m sante_sync tester-notification
Write-Host "  Une notification « Santé : test de notification » doit apparaître en bas à droite."

if (-not $SansCollecte) {
    Etape "Premier passage forcé"
    Write-Host "  (jusqu'à 3 minutes si une source ne répond pas : 3 essais espacés)"
    $ErrorActionPreference = 'Continue'
    & $Py -m sante_sync collecte --force -v | Out-Null
    & $Py -m sante_sync statut
}

Write-Host ""
Write-Host "Installation terminée." -ForegroundColor Green
Write-Host "  Vérifier demain : ouvrez $DataDir\status.json (derniere_execution = demain matin)."
Write-Host "  Relancer à la main : $AppDir\Collecter maintenant.cmd"
