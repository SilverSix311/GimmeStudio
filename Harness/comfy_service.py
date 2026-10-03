import runtime_paths
"""Control only the ComfyUI process owned by this portable studio."""
import json
import subprocess
import time
import urllib.request
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[1]


def owned_process():
    pidfile = ROOT / 'Logs/comfy.pid'
    if not pidfile.exists():
        return None
    try:
        process = psutil.Process(int(pidfile.read_text().strip()))
        expected = (runtime_paths.path('python', ROOT)).resolve()
        main = (runtime_paths.path('comfy', ROOT) / 'main.py').resolve()
        if Path(process.exe()).resolve() != expected or not any(Path(a).resolve() == main for a in process.cmdline()[1:] if a.endswith('main.py')):
            raise ValueError('Tracked PID is not this studioâ€™s ComfyUI server')
        return process
    except psutil.NoSuchProcess:
        return None


def status():
    try:
        process = owned_process()
        if process is None:
            return {'running': False, 'busy': False, 'message': 'ComfyUI stopped'}
        with urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=1) as response:
            queue = json.load(response)
        busy = bool(queue.get('queue_running') or queue.get('queue_pending'))
        return {'running': True, 'busy': busy, 'message': 'ComfyUI rendering / queued' if busy else 'ComfyUI running Â· idle'}
    except Exception as e:
        return {'running': True, 'busy': True, 'message': 'ComfyUI unavailable: ' + str(e)}


def stop(_data):
    process = owned_process()
    if process is None:
        return {'message': 'ComfyUI is already stopped. The dashboard stays open.'}
    state = status()
    if state['busy']:
        raise ValueError('Finish or cancel queued renders in ComfyUI before shutting it down.')
    # Recheck identity immediately before terminating; never target the dashboard's Python process.
    current = owned_process()
    if current is None or current.create_time() != process.create_time():
        raise ValueError('ComfyUI process changed; refresh and try again')
    current.terminate()
    current.wait(timeout=15)
    (ROOT / 'Logs/comfy.pid').unlink(missing_ok=True)
    return {'message': 'ComfyUI shut down. Its RAM and GPU allocations are released; the dashboard remains available.'}


def start(_data):
    import workspaces
    workspaces.guard_other_workers()
    if owned_process() is None:
        command = [str(runtime_paths.path('python', ROOT)), '-s',
                   str(runtime_paths.path('comfy', ROOT) / 'main.py'), '--listen', '127.0.0.1',
                   '--port', '8188', '--disable-auto-launch', '--disable-api-nodes', '--reserve-vram', '2']
        for option, folder in [('models', 'Models'), ('output', 'Output'), ('input', 'Input'),
                               ('user', 'User'), ('temp', 'Cache/temp')]:
            command += ['--' + option + '-directory', str(ROOT / folder)]
        command += runtime_paths.comfy_args(ROOT)
        shared_config = ROOT / 'Studio/shared-model-paths.yaml'
        if workspaces.is_incognito() and shared_config.exists():
            command += ['--extra-model-paths-config', str(shared_config)]
        # Inherit the dashboard's workspace-scoped caches, and detach console/log handles.
        with (ROOT / 'Logs/comfy.out.log').open('w') as out, (ROOT / 'Logs/comfy.err.log').open('w') as err:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (ROOT / 'Logs/comfy.pid').write_text(str(process.pid), encoding='utf-8')
    for _ in range(60):
        state = status()
        if state['running'] and 'unavailable' not in state['message']:
            return {'message': 'ComfyUI is ready. Reconnect or refresh its browser tab.'}
        time.sleep(1)
    raise ValueError('ComfyUI has not become ready yet. Check Logs/comfy.err.log.')
