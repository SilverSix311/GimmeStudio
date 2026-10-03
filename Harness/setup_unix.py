"""Provision local Unix runtimes. GPU model validation remains workflow-specific."""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--core-only', action='store_true', help='Dashboard and browser, without ComfyUI/PyTorch')
    parser.add_argument('--skip-browser', action='store_true')
    parser.add_argument('--backend', choices=['cpu', 'cuda', 'mps'], default=None)
    args = parser.parse_args()
    backend = args.backend or ('mps' if platform.system() == 'Darwin' and platform.machine() == 'arm64' else 'cpu')
    if backend == 'cuda' and platform.system() != 'Linux':
        parser.error('CUDA setup is available on Linux; use MPS for Apple Silicon')
    if backend == 'mps' and (platform.system() != 'Darwin' or platform.machine() != 'arm64'):
        parser.error('MPS setup requires an Apple Silicon Mac')
    for name in ('Logs', 'Studio', 'Projects', 'Input', 'Output'):
        (ROOT / name).mkdir(exist_ok=True)
    uv = ROOT / 'Tools/uv/uv'
    def pip(*args):
        subprocess.run([str(uv), 'pip', 'install', '--python', sys.executable, *args], check=True)
    pip('-r', str(ROOT / 'Config/requirements.txt'))
    if not args.core_only:
        manifest = json.loads((ROOT / 'Config/comfy-source.json').read_text())
        archive = ROOT / 'Downloads' / manifest['filename']
        if not archive.exists():
            partial = archive.with_suffix('.partial')
            urllib.request.urlretrieve(manifest['url'], partial)
            partial.replace(archive)
        with archive.open('rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != manifest['sha256']:
                raise ValueError('ComfyUI archive checksum mismatch')
        target = ROOT / 'ComfyUI_windows_portable/ComfyUI'
        if not (target / 'main.py').exists():
            staging = ROOT / 'Cache/comfy-source'
            staging.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as z:
                z.extractall(staging)
            target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(staging / manifest['directory'], target, dirs_exist_ok=True)
        torch_args = ['torch==2.14.0', 'torchvision==0.29.0']
        if platform.system() == 'Linux':
            torch_args += ['--index-url', 'https://download.pytorch.org/whl/' + ('cu130' if backend == 'cuda' else 'cpu')]
        pip(*torch_args)
        pip('-r', str(target / 'requirements.txt'), '-r', str(ROOT / 'Config/requirements.txt'))
    if not args.skip_browser:
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    config = ROOT / 'Studio/runtime.json'
    current = json.loads(config.read_text()) if config.exists() else {}
    current.update(backend=backend, python='Tools/runtime/bin/python', core_only=args.core_only)
    config.write_text(json.dumps(current, indent=2))
    from initialize_portable import initialize
    initialize()
    subprocess.run([sys.executable, str(ROOT / 'Harness/build_help.py')], check=True)
    subprocess.run([sys.executable, str(ROOT / 'Harness/doctor.py')], check=True)
    print('Setup complete. Run bash GimmeStudio.sh. Model weights and optional tools are separate.')


if __name__ == '__main__':
    main()
