"""Offline checks; never downloads or starts model workers."""
import runtime_paths
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    required = ['Harness/studio.html', 'Harness/server.py', 'Docs/help.json',
                str(runtime_paths.path('python', root).relative_to(root))]
    if not runtime_paths.settings(root).get('core_only', False):
        required.append(str((runtime_paths.path('comfy', root) / 'main.py').relative_to(root)))
    missing = [p for p in required if not (root / p).is_file()]
    missing += ['Python package: ' + name for name in ('psutil', 'PIL', 'playwright', 'imageio_ffmpeg')
                if importlib.util.find_spec(name) is None]
    optional = {name: (root / path).exists() for name, path in {
        'Local AI runtime': runtime_paths.path('llama', root),
        'Blender': runtime_paths.path('blender', root),
        'Portable browser': 'Tools/browsers',
    }.items()}
    result = dict(ok=not missing, missing=missing, optional=optional,
                  note='Model weights, custom nodes and GPU compatibility require separate workflow validation.')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    sys.exit(0 if check()['ok'] else 1)
