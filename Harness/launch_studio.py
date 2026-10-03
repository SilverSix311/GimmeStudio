"""Portable launcher, with process identity checks and no installed browser dependency."""
import argparse
import json
import socket
import subprocess
import time
import urllib.request
import psutil
from runtime_paths import ROOT, path


def owned_dashboard():
    pidfile = ROOT / 'Logs/harness.pid'
    if not pidfile.exists():
        return None
    try:
        process = psutil.Process(int(pidfile.read_text().strip()))
        if Path(process.exe()).resolve() != path('python').resolve() or not any(Path(arg).is_absolute() and Path(arg).resolve() == (ROOT / 'Harness/server.py').resolve() for arg in process.cmdline()[1:] if not arg.startswith('-')):
            raise ValueError('Tracked PID is not this studio dashboard')
        return process
    except psutil.NoSuchProcess:
        return None


from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args()
    (ROOT / 'Logs').mkdir(exist_ok=True)
    process = owned_dashboard()
    if args.stop:
        if process is None:
            print('Dashboard already stopped.'); return
        with urllib.request.urlopen('http://127.0.0.1:8190/api/studio/services', timeout=3) as response:
            state = json.load(response)
        if any((state['production']['busy'], state['ai']['busy'], state['studio_finishing'], state['advanced_busy'])):
            raise ValueError('Finish active studio jobs before stopping.')
        import comfy_service, local_ai, studio_store
        for project in studio_store.listing():
            with urllib.request.urlopen('http://127.0.0.1:8190/api/agent/state/' + project['id'], timeout=3) as response:
                if json.load(response).get('busy'):
                    raise ValueError('Pause or stop the local agent first.')
        comfy_service.stop({}); local_ai.stop()
        current = owned_dashboard()
        if current is None or current.create_time() != process.create_time():
            raise ValueError('Dashboard process changed; retry.')
        current.terminate(); current.wait(timeout=15)
        (ROOT / 'Logs/harness.pid').unlink(missing_ok=True)
        print('Studio stopped.'); return
    if process is None:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', 8190)) == 0:
                raise ValueError('Port 8190 is already occupied by another application or studio folder.')
        with (ROOT / 'Logs/harness.out.log').open('w') as out, (ROOT / 'Logs/harness.err.log').open('w') as err:
            process = subprocess.Popen([str(path('python')), '-s', str(ROOT / 'Harness/server.py')],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
        (ROOT / 'Logs/harness.pid').write_text(str(process.pid))
    for _ in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8190/api/studio', timeout=1) as response:
                if json.load(response).get('mode') == 'local':
                    break
        except OSError:
            time.sleep(.25)
    else:
        raise RuntimeError('Dashboard startup failed. Inspect Logs/harness.err.log.')
    print('GimmeStudio: http://127.0.0.1:8190', flush=True)
    if not args.no_browser:
        subprocess.run([str(path('python')), '-s', str(ROOT / 'Harness/portable_browser.py')], check=True)


if __name__ == '__main__':
    main()
