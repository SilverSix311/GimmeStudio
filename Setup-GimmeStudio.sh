#!/usr/bin/env bash
set -euo pipefail
STUDIO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export STUDIO_ROOT
source "$STUDIO_ROOT/Environment.sh"
for name in harness planner comfy; do
 if [[ -f "$STUDIO_ROOT/Logs/$name.pid" ]]; then
  read -r tracked < "$STUDIO_ROOT/Logs/$name.pid" || true
  if [[ "$tracked" =~ ^[0-9]+$ ]] && kill -0 "$tracked" 2>/dev/null; then
   echo 'Stop this studio and its workers before running setup.' >&2; exit 1
  fi
 fi
done
mkdir -p "$STUDIO_ROOT/Downloads" "$STUDIO_ROOT/Tools/uv"
key="$(uname -s)-$(uname -m)"
row="$(awk -v key="$key" '{sub(/\r$/, "")} $1==key {print $2 " " $3}' "$STUDIO_ROOT/Config/uv-downloads.txt")"
if [[ -z "$row" ]]; then echo "Unsupported platform: $key" >&2; exit 1; fi
read -r url digest <<< "$row"
archive="$STUDIO_ROOT/Downloads/uv-$key.tar.gz"
if [[ ! -f "$archive" ]]; then
 curl --fail --location --retry 3 "$url" -o "$archive.partial"
 mv "$archive.partial" "$archive"
fi
if command -v sha256sum >/dev/null; then actual="$(sha256sum "$archive" | awk '{print $1}')";
else actual="$(shasum -a 256 "$archive" | awk '{print $1}')"; fi
[[ "$actual" == "$digest" ]] || { echo 'uv checksum mismatch; remove the cached archive and retry.' >&2; exit 1; }
tar -xzf "$archive" -C "$STUDIO_ROOT/Tools/uv" --strip-components=1
uv="$STUDIO_ROOT/Tools/uv/uv"
"$uv" python install 3.13.7 --no-bin
if [[ ! -x "$STUDIO_ROOT/Tools/runtime/bin/python" ]]; then
 "$uv" venv --python 3.13.7 --relocatable "$STUDIO_ROOT/Tools/runtime"
fi
python="$STUDIO_ROOT/Tools/runtime/bin/python"
"$python" "$STUDIO_ROOT/Harness/setup_unix.py" "$@"
