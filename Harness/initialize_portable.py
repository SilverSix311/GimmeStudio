"""Create portable defaults without overwriting a user's studio state."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def initialize(root=ROOT):
    for folder in ('Cache', 'Studio', 'Projects', 'Logs', 'Input', 'Output', 'User', 'Models/llm', 'Models/checkpoints',
                   'Models/diffusion_models', 'Models/text_encoders', 'Models/vae', 'Models/loras'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    defaults = root / 'Config/defaults'
    for source in defaults.rglob('*'):
        if source.is_file():
            target = root / source.relative_to(defaults)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
    bridge = root / 'Integrations/local_story_studio'
    if bridge.is_dir():
        shutil.copytree(bridge, root / 'ComfyUI_windows_portable/ComfyUI/custom_nodes/local_story_studio', dirs_exist_ok=True)
    print('Portable folders and defaults ready; existing project settings preserved.')


if __name__ == '__main__':
    initialize()
