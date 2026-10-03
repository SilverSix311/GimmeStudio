"""Workspace-local configuration for the optional upstream LoRA Manager."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'f8aba393fee1ee57db16a19b7995e2a56eeb1411'


def environment(root=ROOT):
    home = root / 'User/lora-manager'
    home.mkdir(parents=True, exist_ok=True)
    path = home / 'settings.json'
    settings = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    # Keep generated previews and metadata out of shared model directories.
    settings.update(sidecar_storage_mode='centralized',
                    sidecar_storage_path=str(home / 'sidecars'),
                    recipes_path=str(home / 'recipes'),
                    example_images_path=str(home / 'examples'))
    settings.setdefault('show_only_sfw', root.name != 'Incognito')
    settings.setdefault('auto_download_example_images', False)
    settings.setdefault('enable_civarchive_api', False)
    libraries = settings.setdefault('libraries', {})
    libraries.setdefault('comfyui', {})
    for library in libraries.values():
        library['recipes_path'] = str(home / 'recipes')
    path.write_text(json.dumps(settings, indent=2), encoding='utf-8')
    env = dict(os.environ, LORA_MANAGER_SETTINGS_DIR=str(home))
    git = root / 'Tools/git/cmd/git.exe'
    if git.exists():
        env['GIT_PYTHON_GIT_EXECUTABLE'] = str(git)
    else:
        env['GIT_PYTHON_REFRESH'] = 'quiet'
    return env
