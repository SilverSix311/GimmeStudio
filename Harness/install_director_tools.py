"""Pinned, optional director tools. Uses existing ComfyUI dependencies only."""
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import runtime_paths

ROOT = Path(__file__).resolve().parents[1]


def install():
    import comfy_service, workspaces
    if Path(sys.executable).resolve() != runtime_paths.path('python', ROOT).resolve():
        raise ValueError('Use the project-owned Python')
    workspaces.guard_other_workers()
    if comfy_service.status()['running']:
        raise ValueError('Stop idle ComfyUI before installing extensions')
    specs = json.loads((ROOT/'Config/director-tools.json').read_text(encoding='utf-8'))
    for spec in specs:
        name = spec['repo'].split('/')[1]
        destination = runtime_paths.path('comfy', ROOT)/'custom_nodes'/name
        if destination.exists():
            print(name+' already exists; preserved');continue
        archive = ROOT/'Downloads'/f"{spec['id']}-{spec['revision']}.zip"
        archive.parent.mkdir(parents=True,exist_ok=True)
        if not archive.exists():
            urllib.request.urlretrieve(f"https://github.com/{spec['repo']}/archive/{spec['revision']}.zip",archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError('Archive checksum mismatch')
        staging = ROOT/'Tools/sources'/spec['id']
        staging.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.namelist():
                if not (staging/member).resolve().is_relative_to(staging.resolve()):
                    raise ValueError('Unsafe archive path')
            bundle.extractall(staging)
        shutil.copytree(staging/(name+'-'+spec['revision']),destination)
        print('Installed '+name+' @ '+spec['revision'])
    (ROOT/'Studio/director-tools-install.json').write_text(json.dumps(specs,indent=2),encoding='utf-8')


if __name__ == '__main__':
    install()
