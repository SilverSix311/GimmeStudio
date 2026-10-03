$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$paths = @{
 HF_HOME='Cache/huggingface'; TORCH_HOME='Cache/torch'; PIP_CACHE_DIR='Cache/pip';
 XDG_CACHE_HOME='Cache'; CUDA_CACHE_PATH='Cache/cuda'; TRITON_CACHE_DIR='Cache/triton';
 MPLCONFIGDIR='Cache/matplotlib'; TEMP='Cache/temp'; TMP='Cache/temp'; PYTHONUSERBASE='Cache/python-user'
}
foreach ($entry in $paths.GetEnumerator()) {
 $value = Join-Path $taskRoot $entry.Value
 New-Item -ItemType Directory -Force -Path $value | Out-Null
 [Environment]::SetEnvironmentVariable($entry.Key, $value, 'Process')
}
$env:PYTHONNOUSERSITE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
$env:DO_NOT_TRACK='1'
$env:LLAMA_ARG_CORS_ORIGINS='http://127.0.0.1:8190'
$env:HF_HUB_OFFLINE='1'

