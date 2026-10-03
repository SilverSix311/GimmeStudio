"""Optional, pinned LoRA Manager installation using the studio's own Python."""
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import runtime_paths
from lora_library import REVISION, environment

ROOT = Path(__file__).resolve().parents[1]
SHA256 = '235e4899076e4b0220b058f5fdd2e7b25fe3531ed6d73cd2351a10c0b49ccb08'


def install():
    if Path(sys.executable).resolve() != runtime_paths.path('python',ROOT).resolve():
        raise ValueError('Run this installer with the project-owned Python')
    import comfy_service, workspaces
    workspaces.guard_other_workers()
    if comfy_service.status()['running']:
        raise ValueError('Unload ComfyUI before installing its extension')
    destination = runtime_paths.path('comfy',ROOT)/'custom_nodes/ComfyUI-Lora-Manager'
    if destination.exists():
        raise ValueError('LoRA Manager is already installed; existing files were preserved')
    archive = ROOT/'Downloads'/('lora-manager-'+REVISION+'.zip')
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        urllib.request.urlretrieve('https://github.com/willmiao/ComfyUI-Lora-Manager/archive/'+REVISION+'.zip',archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Upstream archive checksum mismatch')
    staging = ROOT/'Tools/sources'
    staging.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.namelist():
            if not (staging/member).resolve().is_relative_to(staging.resolve()):
                raise ValueError('Unsafe archive member')
        bundle.extractall(staging)
    source = staging/('ComfyUI-Lora-Manager-'+REVISION)
    # Freeze installed distributions so pip cannot silently upgrade the working GPU stack.
    constraints=ROOT/'Downloads/lora-manager-installed-constraints.txt'
    constraints.write_text('\n'.join(d.metadata['Name']+'=='+d.version for d in importlib.metadata.distributions() if d.metadata.get('Name')),encoding='utf-8')
    subprocess.run([sys.executable,'-s','-m','pip','install','-r',str(source/'requirements.txt'),'-c',str(constraints)],check=True)
    shutil.copytree(source,destination)
    environment(ROOT)
    (ROOT/'Studio/lora-manager-install.json').write_text(json.dumps(dict(revision=REVISION,sha256=SHA256),indent=2),encoding='utf-8')
    print('LoRA Manager installed. Start ComfyUI and open its /loras page.')


if __name__=='__main__':install()
