"""Persistent content separation using independent studio processes and data roots.

This is organization, not an authentication or filesystem security sandbox.
Only application code, default UI assets and tool binaries are shared.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get('GIMMESTUDIO_INSTALL_ROOT', str(ROOT))).resolve()
PRIVATE = INSTALL / 'Incognito'
LOCK = threading.Lock()


def is_incognito():
    return ROOT.resolve() == PRIVATE.resolve()


def state():
    return dict(mode='incognito' if is_incognito() else 'sfw', persistent=True,
                message='Separate content, not encryption. Files remain until you delete them.',
                models='Incognito/Models' if is_incognito() else 'Models',
                shared_models='Models (SFW; reused without copying)' if is_incognito() else None)


def request(port, endpoint):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/'+endpoint, timeout=2) as response:
        return json.load(response)


def guard_other_workers():
    port = 8190 if is_incognito() else 8290
    try:
        s = request(port, 'api/studio/services')
    except urllib.error.URLError:
        return
    if (s['comfy']['running'] or s.get('planner_running') or s.get('agent_busy') or
        s['production']['busy'] or s['ai']['busy'] or s['studio_finishing'] or s['advanced_busy']):
        raise ValueError('Unload or finish workers in the other workspace before starting this worker.')


def link_directory(source, target):
    """Junctions need no Windows developer mode. Never replace an existing directory."""
    if target.exists():
        if target.resolve() != source.resolve():
            raise ValueError('Refusing to replace existing shared-tool path: '+str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        env = dict(os.environ, GIMME_LINK_SOURCE=str(source), GIMME_LINK_TARGET=str(target))
        subprocess.run(['powershell.exe', '-NoProfile', '-Command',
            'New-Item -ItemType Junction -Path $env:GIMME_LINK_TARGET -Target $env:GIMME_LINK_SOURCE | Out-Null'],
            env=env, check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    else:
        target.symlink_to(source, target_is_directory=True)


def prepare():
    PRIVATE.mkdir(exist_ok=True)
    # Keep a small application snapshot; never copy Studio, Projects, models or user state.
    for folder in ('Harness', 'Docs', 'Config'):
        for source in (INSTALL / folder).rglob('*'):
            if not source.is_file() or '__pycache__' in source.parts or source.suffix not in ('.py','.js','.css','.html','.json','.md','.txt','.png'):
                continue
            if folder == 'Harness' and source.suffix not in ('.py','.js','.html','.css'):
                continue
            if folder == 'Harness' and (source.name.startswith(('test_', 'verify_')) or source.name in ('series-bible.json', 'staged-workflow.json')):
                continue
            target = PRIVATE / source.relative_to(INSTALL)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix in ('.py','.js','.html','.css'):
                body = source.read_text(encoding='utf-8')
                if source.name == 'studio.css' and not (PRIVATE/'Studio/brand/wallpaper.jpeg').exists():
                    body = body.replace(",url('/studio-file/Studio/brand/wallpaper.jpeg') center/cover", '')
                # Fixed alternate origins also isolate browser localStorage and Comfy histories.
                # Do not transform the coordinator: it must know both original ports.
                if source.name != 'workspaces.py':
                    body = re.sub(r'\b(8188|8189|8190)\b', lambda m:str(int(m[0])+100), body)
                target.write_text(body, encoding='utf-8')
            else:
                shutil.copy2(source, target)
    for name in ('Studio','Projects','Input','Output','User','Logs','Cache/temp','Models'):
        (PRIVATE / name).mkdir(parents=True, exist_ok=True)
    for name in ('Tools','ComfyUI_windows_portable'):
        if (INSTALL / name).is_dir():
            link_directory(INSTALL / name, PRIVATE / name)
    link_directory(INSTALL / 'Models', PRIVATE / 'Models/Shared-SFW')
    # Default UI files contain no personal productions, chat history or credentials.
    defaults = INSTALL / 'Config/defaults'
    for source in defaults.rglob('*'):
        if source.is_file():
            target = PRIVATE / source.relative_to(defaults)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
    help_zip = INSTALL / 'Studio/help/GimmeStudio-wiki.zip'
    if help_zip.exists():
        (PRIVATE / 'Studio/help').mkdir(exist_ok=True)
        shutil.copy2(help_zip, PRIVATE / 'Studio/help'/help_zip.name)
    runtime = INSTALL / 'Studio/runtime.json'
    if runtime.exists() and not (PRIVATE / 'Studio/runtime.json').exists():
        shutil.copy2(runtime, PRIVATE / 'Studio/runtime.json')
    categories = ('checkpoints','diffusion_models','unet','clip','text_encoders','clip_vision','vae','loras','controlnet','upscale_models','embeddings','configs','hypernetworks','audio_encoders','model_patches')
    lines = ['shared_sfw:', '  base_path: '+json.dumps(str(INSTALL/'Models'))]
    for category in categories:
        (PRIVATE/'Models'/category).mkdir(exist_ok=True)
        lines.append('  '+category+': '+category)
    (PRIVATE/'Studio/shared-model-paths.yaml').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def private_process():
    pidfile = PRIVATE/'Logs/harness.pid'
    if not pidfile.exists():
        return None
    try:
        p = psutil.Process(int(pidfile.read_text().strip()))
        if str(PRIVATE/'Harness/server.py') not in p.cmdline():
            raise ValueError('Incognito PID belongs to another process')
        return p
    except psutil.NoSuchProcess:
        return None


def open_workspace(data):
    mode = data.get('mode')
    if mode not in ('sfw','incognito'):
        raise ValueError('Unknown workspace')
    import local_ai, comfy_service, production, studio_api, advanced_studio, local_agent
    if any((local_ai.JOB['busy'], production.JOB['busy'], studio_api.WORK.locked(), advanced_studio.LOCK.locked(), local_agent.busy())):
        raise ValueError('Finish or pause current jobs before switching workspaces.')
    if comfy_service.status()['busy']:
        raise ValueError('Finish or cancel the ComfyUI queue before switching workspaces.')
    with LOCK:
        comfy_service.stop({}); local_ai.stop()
        if mode == 'sfw':
            return dict(url='http://127.0.0.1:8190/#overview', **dict(message='Returning to SFW workspace'))
        if private_process() is None:
            import socket, runtime_paths
            with socket.socket() as probe:
                if probe.connect_ex(('127.0.0.1',8290)) == 0:
                    raise ValueError('Incognito port 8290 is occupied by another service.')
            prepare()
            env = dict(os.environ, GIMMESTUDIO_INSTALL_ROOT=str(INSTALL), GIMMESTUDIO_WORKSPACE_ROOT=str(PRIVATE))
            for key,value in list(env.items()):
                for folder in ('Cache','User','Input','Output','Logs'):
                    old = str(INSTALL/folder)
                    if value.startswith(old):
                        env[key] = str(PRIVATE/folder)+value[len(old):]
            env['LLAMA_ARG_CORS_ORIGINS']='http://127.0.0.1:8290'
            with (PRIVATE/'Logs/harness.out.log').open('w') as out, (PRIVATE/'Logs/harness.err.log').open('w') as err:
                p=subprocess.Popen([str(runtime_paths.path('python', INSTALL)), '-s', str(PRIVATE/'Harness/server.py')], cwd=PRIVATE,
                    env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (PRIVATE/'Logs/harness.pid').write_text(str(p.pid))
        for _ in range(40):
            try:
                if request(8290,'api/workspace')['mode']=='incognito':
                    return dict(url='http://127.0.0.1:8290/#overview',message='Incognito workspace ready')
            except urllib.error.URLError:
                time.sleep(.25)
        raise ValueError('Incognito startup failed. Inspect Incognito/Logs/harness.err.log')
