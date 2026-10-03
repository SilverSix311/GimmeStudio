$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
foreach ($name in @('harness','planner','comfy')) {
 $pidFile = Join-Path $taskRoot "Logs/$name.pid"
 if (Test-Path -LiteralPath $pidFile) {
  $process = Get-Process -Id ([int](Get-Content -LiteralPath $pidFile)) -ErrorAction SilentlyContinue
  $expected = if ($name -eq 'planner') { Join-Path $taskRoot 'Tools/llama/llama-server.exe' } else { Join-Path $taskRoot 'ComfyUI_windows_portable/python_embeded/python.exe' }
  if ($process -and $process.Path -eq $expected) { Stop-Process -Id $process.Id }
  Remove-Item -LiteralPath $pidFile
 }
}

