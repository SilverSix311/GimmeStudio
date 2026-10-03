#!/usr/bin/env bash
set -euo pipefail
STUDIO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export STUDIO_ROOT
source "$STUDIO_ROOT/Environment.sh"
python="$STUDIO_ROOT/Tools/runtime/bin/python"
[[ -x "$python" ]] || { echo 'Run bash Setup-GimmeStudio.sh first.' >&2; exit 1; }
exec "$python" "$STUDIO_ROOT/Harness/launch_studio.py" "$@"
