"""Offline checks; never downloads or starts model workers."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    required = ['Harness/studio.html', 'Harness/server.py', 'Docs/help.json',
                'ComfyUI_windows_portable/python_embeded/python.exe', 'ComfyUI_windows_portable/ComfyUI/main.py']
    missing = [p for p in required if not (root / p).is_file()]
    missing += ['Python package: ' + name for name in ('psutil', 'PIL', 'playwright', 'imageio_ffmpeg')
                if importlib.util.find_spec(name) is None]
    optional = {name: (root / path).exists() for name, path in {
        'Local AI runtime': 'Tools/llama/llama-server.exe',
        'Blender': 'Tools/blender-4.5.14-windows-x64/blender.exe',
        'Portable browser': 'Tools/browsers',
    }.items()}
    result = dict(ok=not missing, missing=missing, optional=optional,
                  note='Model weights, custom nodes and GPU compatibility require separate workflow validation.')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    sys.exit(0 if check()['ok'] else 1)
