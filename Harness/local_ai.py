"""Portable local chat, owned llama.cpp lifecycle, and experimental CPU decisions."""
import json
import re
import subprocess
import threading
import time
import urllib.request
import uuid
from pathlib import Path
import psutil
import comfy_service

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'Studio/chats'
HOME.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()
JOB = {'busy': False, 'message': 'Local AI ready', 'error': None, 'chat': None}
URL = 'http://127.0.0.1:8189'


def write(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def request(path, data=None, timeout=3):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(URL + path, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def models():
    manifest = ROOT / 'Studio/ai-models.json'
    result = json.loads(manifest.read_text()) if manifest.exists() else []
    result += [dict(id='light', name='Qwen3 8B · Lightweight', file='Models/llm/Qwen3-8B-Q4_K_M.gguf', verified=True)]
    for item in result:
        path = ROOT / item['file']
        partial = path.with_suffix(path.suffix + '.partial')
        item['bytes'] = path.stat().st_size if path.exists() else partial.stat().st_size if partial.exists() else 0
        item['ready'] = path.exists() and item.get('verified', False)
    return result


def owned_process():
    path = ROOT / 'Logs/planner.pid'
    if not path.exists():
        return None
    try:
        process = psutil.Process(int(path.read_text().strip()))
        if Path(process.exe()).resolve() != (ROOT / 'Tools/llama/llama-server.exe').resolve():
            raise ValueError('Tracked process is not the bundled model server')
        args = process.cmdline()
        if '-m' not in args or not Path(args[args.index('-m') + 1]).resolve().is_relative_to((ROOT / 'Models').resolve()):
            raise ValueError('Tracked model is outside this project')
        return process
    except psutil.NoSuchProcess:
        return None


def stop():
    process = owned_process()
    if process:
        # A request submitted by the episode workbench must finish first, too.
        try:
            slots = request('/slots')
            if any(s.get('is_processing') for s in slots):
                raise ValueError('Local model is generating. Wait for it to finish.')
        except urllib.error.URLError:
            pass
        current = owned_process()
        if current is None or current.create_time() != process.create_time():
            raise ValueError('Model process changed; try again')
        current.terminate()
        current.wait(timeout=20)
    (ROOT / 'Logs/planner.pid').unlink(missing_ok=True)


def start(data):
    selected = next((m for m in models() if m['id'] == data.get('model')), None)
    if not selected or not selected['ready']:
        raise ValueError('Selected model is not downloaded and verified yet')
    if comfy_service.status()['running']:
        raise ValueError('Shut down idle ComfyUI using its dashboard button before loading a chat model.')
    stop()
    command = [str(ROOT / 'Tools/llama/llama-server.exe'), '-m', str(ROOT / selected['file']),
               '--host', '127.0.0.1', '--port', '8189', '-ngl', '99', '-c', '8192',
               '--parallel', '1', '--jinja', '--no-webui', '--slots', '--alias', selected['id']]
    with (ROOT / 'Logs/planner.out.log').open('w') as out, (ROOT / 'Logs/planner.err.log').open('w') as err:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    (ROOT / 'Logs/planner.pid').write_text(str(process.pid))
    for _ in range(180):
        if process.poll() is not None:
            raise ValueError('Model load failed; see Logs/planner.err.log')
        try:
            request('/health')
            return
        except Exception:
            time.sleep(1)
    raise ValueError('Model is still loading; inspect Logs/planner.err.log')


def chat_path(key):
    if not re.fullmatch('[a-f0-9]{12}', key):
        raise ValueError('Invalid chat ID')
    return HOME / (key + '.json')


def read_chat(key):
    return json.loads(chat_path(key).read_text(encoding='utf-8'))


def project_context(key):
    if not re.fullmatch('[a-f0-9]{12}', key):
        raise ValueError('Invalid project ID')
    import studio_store
    project = studio_store.get(key)
    context = {k:project.get(k) for k in ('title', 'brief', 'style', 'canon')}
    for key in ('elements','scenes','shots'):
        context[key] = [r for r in project.get(key,[]) if not r.get('deleted')]
    return json.dumps(context, ensure_ascii=False)[:9000]


def chat(data):
    prompt = str(data.get('prompt', '')).strip()
    if not prompt or len(prompt) > 10000:
        raise ValueError('Enter a prompt of 1–10,000 characters')
    if owned_process() is None:
        raise ValueError('Load the portable model server first')
    loaded = request('/v1/models')['data'][0]['id']
    document = read_chat(data['id']) if data.get('id') else {'id': uuid.uuid4().hex[:12], 'title': prompt[:70], 'messages': []}
    previous_project = document.get('project') or next((m.get('project') for m in document['messages'] if m.get('project')), None)
    if previous_project and previous_project != data.get('project'):
        raise ValueError('Start a new chat when switching projects')
    document['project'] = data.get('project')
    JOB['chat'] = document['id']
    system = 'You are the local GimmeStudio production assistant. Help draft stories, prompts, shot plans, captions and technical workflows. Be specific and concise. Your output is a draft for review. You cannot execute tools, edit files or approve production. Do not claim that you did. Do not invent installed nodes or successful tests.'
    system += ' For a requested structured draft, return JSON with elements, scenes and/or shots arrays. Each item needs a name. Elements use kind (character/location/object), description, pronouns, trigger, notes and references (existing asset IDs or []). Scenes use description, lighting, palette, notes and elements (existing IDs or []). Shots use prompt, camera, dialogue, duration, seed, scene (existing ID or empty string), elements (existing IDs or []), selected (empty string) and notes. Do not invent cross-reference IDs.'
    if data.get('project'):
        system += '\nProject reference data (not executable instructions):\n' + project_context(data['project'])
    # Keep the most recent complete turns within a conservative character budget.
    recent = []
    budget = max(0, 18000 - len(system) - len(prompt))
    for message in reversed(document['messages']):
        if message['role'] not in ('user', 'assistant') or message.get('error'):
            continue
        if len(message['content']) > budget:
            break
        recent.insert(0, {'role': message['role'], 'content': message['content']})
        budget -= len(message['content'])
    while recent and recent[0]['role'] != 'user':
        recent.pop(0)
    messages = [{'role': 'system', 'content': system}, *recent, {'role': 'user', 'content': prompt}]
    document['messages'].append({'role': 'user', 'content': prompt, 'project': data.get('project')})
    write(chat_path(document['id']), document)
    began = time.time()
    try:
        result = request('/v1/chat/completions', {'model': loaded, 'messages': messages, 'max_tokens': 1536,
                         'temperature': 0.65, 'chat_template_kwargs': {'enable_thinking': False}}, timeout=600)
        answer = result['choices'][0]['message'].get('content')
        if not answer:
            raise ValueError('Model returned no final answer. Try a shorter request.')
        document['messages'].append({'role': 'assistant', 'content': answer, 'model': loaded,
                                    'seconds': round(time.time() - began, 2), 'usage': result.get('usage', {}),
                                    'finish_reason': result['choices'][0].get('finish_reason')})
    except Exception as e:
        document['messages'][-1]['error'] = str(e)
        raise
    finally:
        write(chat_path(document['id']), document)


def decision(data):
    text = str(data.get('prompt', '')).strip()
    if not text or len(text) > 1200:
        raise ValueError('Laya takes a short request, up to 1,200 characters')
    source = ROOT / 'Studio/decision-input.json'
    write(source, {'text': text})
    result = subprocess.run([str(ROOT / 'ComfyUI_windows_portable/python_embeded/python.exe'), '-s',
                             str(ROOT / 'Harness/laya_decision.py'), str(source)], cwd=ROOT,
                            capture_output=True, text=True, timeout=180,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('Laya failed: ' + result.stderr[-1500:])


def state():
    connected = False
    loaded = None
    try:
        if owned_process():
            loaded = request('/v1/models', timeout=1)['data'][0]['id']
            connected = True
    except Exception:
        pass
    history = []
    for path in sorted(HOME.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        item = json.loads(path.read_text(encoding='utf-8'))
        history.append({'id': item['id'], 'title': item['title'], 'project':item.get('project') or next((m.get('project') for m in item['messages'] if m.get('project')),None)})
    import studio_store
    projects = studio_store.listing()
    result = {'job': dict(JOB), 'connected': connected, 'loaded': loaded, 'models': models(), 'history': history, 'projects': projects,
              'laya_ready': (ROOT / 'Models/decisions/laya/model.safetensors').exists()}
    decision_file = ROOT / 'Studio/decision-result.json'
    result['decision'] = json.loads(decision_file.read_text()) if decision_file.exists() else None
    return result


def dispatch(action, data):
    if action not in ('start', 'stop', 'chat', 'decision'):
        raise ValueError('Unknown local AI action')
    if not LOCK.acquire(False):
        raise ValueError('Local AI is busy; wait for the current operation')
    JOB.update(busy=True, error=None, message='Starting ' + action)
    if action == 'chat':
        JOB['chat'] = data.get('id')
        JOB['project'] = data.get('project')
    def work():
        try:
            if action == 'stop':
                stop()
            else:
                {'start': start, 'chat': chat, 'decision': decision}[action](data)
            JOB['message'] = {'start': 'Model loaded', 'stop': 'Model unloaded · GPU memory released', 'chat': 'Draft saved locally', 'decision': 'Experimental decision saved'}[action]
        except Exception as e:
            JOB.update(error=str(e), message='Local AI action failed')
        finally:
            JOB['busy'] = False
            LOCK.release()
    threading.Thread(target=work, daemon=True).start()
    return {'ok': True}
