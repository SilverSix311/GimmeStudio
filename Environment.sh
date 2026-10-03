#!/usr/bin/env bash
# Source after setting STUDIO_ROOT; no user profile or global application paths.
export HF_HOME="$STUDIO_ROOT/Cache/huggingface"
export TORCH_HOME="$STUDIO_ROOT/Cache/torch"
export PIP_CACHE_DIR="$STUDIO_ROOT/Cache/pip"
export XDG_CACHE_HOME="$STUDIO_ROOT/Cache"
export XDG_CONFIG_HOME="$STUDIO_ROOT/User/config"
export XDG_DATA_HOME="$STUDIO_ROOT/User/data"
export TMPDIR="$STUDIO_ROOT/Cache/temp"
export TEMP="$TMPDIR" TMP="$TMPDIR"
export UV_CACHE_DIR="$STUDIO_ROOT/Cache/uv"
export UV_PYTHON_INSTALL_DIR="$STUDIO_ROOT/Tools/python"
export UV_PYTHON_BIN_DIR="$STUDIO_ROOT/Tools/python-bin"
export UV_TOOL_DIR="$STUDIO_ROOT/Tools/uv-tools"
export UV_NO_CONFIG=1 UV_PYTHON_PREFERENCE=only-managed
export PLAYWRIGHT_BROWSERS_PATH="$STUDIO_ROOT/Tools/browsers"
export PYTHONNOUSERSITE=1 HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1
export HF_HUB_OFFLINE=1 LLAMA_ARG_CORS_ORIGINS=http://127.0.0.1:8190
export CUDA_CACHE_PATH="$STUDIO_ROOT/Cache/cuda" TRITON_CACHE_DIR="$STUDIO_ROOT/Cache/triton"
export MPLCONFIGDIR="$STUDIO_ROOT/Cache/matplotlib" PYTHONUSERBASE="$STUDIO_ROOT/Cache/python-user"
mkdir -p "$TMPDIR" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$UV_PYTHON_BIN_DIR"
