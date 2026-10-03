param([switch]$NoBrowser)
. "$PSScriptRoot\Environment.ps1"
$python = Join-Path $PSScriptRoot 'ComfyUI_windows_portable/python_embeded/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Setup-GimmeStudio.cmd first to install the portable runtime.' }
New-Item -ItemType Directory -Force -Path "$PSScriptRoot/Logs" | Out-Null
$pidFile = Join-Path $PSScriptRoot 'Logs/harness.pid'
$running = $false
if (Test-Path -LiteralPath $pidFile) {
 $service = Get-Process -Id ([int](Get-Content -LiteralPath $pidFile)) -ErrorAction SilentlyContinue
 $running = $service -and $service.Path -eq $python
}
if (-not $running) {
 $service = Start-Process -FilePath $python -ArgumentList @('-s', ('"'+$PSScriptRoot+'/Harness/server.py"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "$PSScriptRoot/Logs/harness.out.log" -RedirectStandardError "$PSScriptRoot/Logs/harness.err.log"
 $service.Id | Set-Content -LiteralPath $pidFile
}
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
 try {
  $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8190/api/studio' -TimeoutSec 2
  if ($response.mode -eq 'local') { $ready = $true; break }
 } catch { Start-Sleep -Milliseconds 200 }
}
if (-not $ready) { throw 'GimmeStudio did not become ready. Check Logs/harness.err.log.' }
if (-not $NoBrowser) {
 Start-Process -FilePath $python -ArgumentList @('-s', ('"'+$PSScriptRoot+'/Harness/portable_browser.py"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
}
Write-Host 'GimmeStudio: http://127.0.0.1:8190 — start AI or ComfyUI from the dashboard.'
