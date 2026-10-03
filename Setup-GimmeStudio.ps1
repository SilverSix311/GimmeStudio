param([switch]$WithLocalAI, [switch]$WithBlender, [switch]$SkipBrowser)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/Environment.ps1"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
foreach ($name in @('harness','planner','comfy')) {
 $pidFile = Join-Path $PSScriptRoot "Logs/$name.pid"
 if (Test-Path -LiteralPath $pidFile) {
  $tracked = Get-Process -Id ([int](Get-Content -LiteralPath $pidFile)) -ErrorAction SilentlyContinue
  if ($tracked -and $tracked.Path -and $tracked.Path.StartsWith($PSScriptRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
   throw 'Close this studio and stop its workers before running setup. No running service has been stopped.'
  }
 }
}
foreach ($folder in @('Downloads','Logs','Tools','Models','Input','Output','User','Projects','Studio')) {
 New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot $folder) | Out-Null
}
$manifest = Get-Content -Raw -LiteralPath "$PSScriptRoot/Config/downloads.json" | ConvertFrom-Json
function Get-Package($key) {
 $entry = $manifest.$key
 if (-not $entry -or $entry.sha256 -notmatch '^[a-f0-9]{64}$') { throw "Invalid download manifest: $key" }
 $file = Join-Path $PSScriptRoot "Downloads/$($entry.filename)"
 if (-not (Test-Path -LiteralPath $file)) {
  Write-Host "Downloading $key from $($entry.url)"
  Invoke-WebRequest -UseBasicParsing -Uri $entry.url -OutFile "$file.partial"
  if ((Get-FileHash -LiteralPath "$file.partial" -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Checksum mismatch: $key" }
  Move-Item -LiteralPath "$file.partial" -Destination $file
 }
 if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Checksum mismatch: $file. Remove the corrupt download and retry." }
 return $file
}
$python = Join-Path $PSScriptRoot 'ComfyUI_windows_portable/python_embeded/python.exe'
$receipt = Join-Path $PSScriptRoot 'Studio/portable-runtime.json'
if (-not (Test-Path -LiteralPath $python)) {
 $archive = Get-Package 'comfy'
 $extractor = Get-Package 'extractor'
 $staging = Join-Path $PSScriptRoot ('Cache/setup-' + [guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory -Path $staging | Out-Null
 Write-Host 'Extracting portable ComfyUI and Python (several GB)...'
 & $extractor x $archive "-o$staging" -y | Out-Null
 if ($LASTEXITCODE -ne 0) { throw "Extraction failed; retained $staging for inspection." }
 $source = Join-Path $staging 'ComfyUI_windows_portable'
 if (-not (Test-Path -LiteralPath "$source/python_embeded/python.exe")) { throw 'Unexpected portable archive layout.' }
 $destination = Join-Path $PSScriptRoot 'ComfyUI_windows_portable'
 if (Test-Path -LiteralPath $destination) { throw 'Incomplete runtime directory exists. Rename it before retrying; setup will not overwrite it.' }
 Move-Item -LiteralPath $source -Destination $destination
 $manifest.comfy | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath $receipt
} else { Write-Host 'Keeping existing portable runtime.' }
Write-Host 'Installing dashboard dependencies into the portable Python...'
& $python -s -m pip install --disable-pip-version-check -r "$PSScriptRoot/Config/requirements.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dashboard dependencies failed to install.' }
if (-not $SkipBrowser) {
 $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot 'Tools/browsers'
 & $python -s -m playwright install chromium
 if ($LASTEXITCODE -ne 0) { throw 'Portable browser installation failed.' }
}
if ($WithLocalAI) {
 $llama = Join-Path $PSScriptRoot 'Tools/llama'
 if (-not (Test-Path -LiteralPath "$llama/llama-server.exe")) {
  $runtimeArchive = Get-Package 'llama'
  $cudaArchive = Get-Package 'llama_cuda'
  New-Item -ItemType Directory -Force -Path $llama | Out-Null
  Expand-Archive -LiteralPath $cudaArchive -DestinationPath $llama -Force
  Expand-Archive -LiteralPath $runtimeArchive -DestinationPath $llama -Force
 }
}
if ($WithBlender -and -not (Test-Path -LiteralPath "$PSScriptRoot/Tools/blender-4.5.14-windows-x64/blender.exe")) {
 $blenderArchive = Get-Package 'blender'
 Expand-Archive -LiteralPath $blenderArchive -DestinationPath "$PSScriptRoot/Tools" -Force
}
& $python -s "$PSScriptRoot/Harness/initialize_portable.py"
if ($LASTEXITCODE -ne 0) { throw 'Studio initialization failed.' }
& $python -s "$PSScriptRoot/Harness/build_help.py"
if ($LASTEXITCODE -ne 0) { throw 'Help generation failed.' }
& $python -s "$PSScriptRoot/Harness/doctor.py"
if ($LASTEXITCODE -ne 0) { throw 'Portable installation checks failed.' }
Write-Host 'Setup complete. Run GimmeStudio.cmd. Models are separate downloads; see Docs/INSTALL.md.'
