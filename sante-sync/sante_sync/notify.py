"""Notification système, sans dépendance externe.

- Windows : notification « toast » native via PowerShell (sans fenêtre),
  avec repli sur une bulle de la zone de notification.
- macOS : osascript.  Linux : notify-send.
Toute notification est aussi écrite dans le journal, et dans le fichier
désigné par SANTE_SYNC_NOTIFY_LOG s'il est défini (utilisé par les tests).
"""
from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime

log = logging.getLogger("sante_sync")

_PS_TOAST = r"""
$ErrorActionPreference = 'Stop'
$title = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{title}'))
$body  = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{body}'))
try {{
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
  $esc = [Security.SecurityElement]
  $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
  $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$($esc::Escape($title))</text><text>$($esc::Escape($body))</text></binding></visual></toast>")
  $appId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\WindowsPowerShell\v1.0\powershell.exe'
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show([Windows.UI.Notifications.ToastNotification]::new($xml))
}} catch {{
  Add-Type -AssemblyName System.Windows.Forms
  $n = New-Object System.Windows.Forms.NotifyIcon
  $n.Icon = [System.Drawing.SystemIcons]::Warning
  $n.Visible = $true
  $n.ShowBalloonTip(15000, $title, $body, 'Warning')
  Start-Sleep -Seconds 16
  $n.Dispose()
}}
"""


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode()


def windows_script(title: str, body: str) -> str:
    return _PS_TOAST.format(title=_b64(title), body=_b64(body))


def notify(title: str, body: str) -> bool:
    log.warning("NOTIFICATION : %s — %s", title, body)
    test_log = os.environ.get("SANTE_SYNC_NOTIFY_LOG")
    if test_log:
        with open(test_log, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{title}\t{body}\n")
    try:
        if sys.platform == "win32":
            script = windows_script(title, body)
            enc = base64.b64encode(script.encode("utf-16-le")).decode()
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                 "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            )
            return True
        if sys.platform == "darwin":
            t = title.replace('"', "'")
            b = body.replace('"', "'")
            subprocess.run(["osascript", "-e", f'display notification "{b}" with title "{t}"'], timeout=10)
            return True
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", "-u", "critical", title, body], timeout=10)
            return True
    except Exception as exc:  # une notification ratée ne doit jamais faire échouer la collecte
        log.error("Notification impossible : %s", exc)
    return bool(test_log)
