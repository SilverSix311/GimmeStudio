"""Resolve project-owned runtimes on Windows, Linux and macOS. Never search PATH."""
import json
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def settings(root=ROOT):
    path = root / 'Studio/runtime.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def owned(root, value):
    path = root / value
    install = Path(os.environ.get('GIMMESTUDIO_INSTALL_ROOT', str(root))).resolve()
    resolved = path.resolve()
    local = resolved.is_relative_to(root.resolve())
    shared_tool = root.resolve() == install / 'Incognito' and any(
        resolved.is_relative_to(install / folder) for folder in ('Tools','ComfyUI_windows_portable'))
    if not local and not shared_tool:
        raise ValueError('Runtime must remain inside the studio folder')
    return path


def path(kind, root=ROOT, system=None):
    system = system or platform.system()
    windows = system == 'Windows'
    defaults = {
        'python': 'ComfyUI_windows_portable/python_embeded/python.exe' if windows else 'Tools/runtime/bin/python',
        'comfy': 'ComfyUI_windows_portable/ComfyUI',
        'llama': 'Tools/llama/llama-server.exe' if windows else 'Tools/llama/llama-server',
        'blender': ('Tools/blender-4.5.14-windows-x64/blender.exe' if windows else
                    'Tools/blender/Blender.app/Contents/MacOS/Blender' if system == 'Darwin' else 'Tools/blender/blender'),
    }
    return owned(root, settings(root).get(kind, defaults[kind]))


def backend(root=ROOT):
    value = settings(root).get('backend', 'cuda' if platform.system() == 'Windows' else 'cpu')
    if value not in ('cpu', 'cuda', 'mps'):
        raise ValueError('Choose cpu, cuda or mps backend')
    return value


def comfy_args(root=ROOT):
    return ['--cpu'] if backend(root) == 'cpu' else []
