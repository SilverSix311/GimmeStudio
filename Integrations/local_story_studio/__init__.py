"""Serve the explicitly staged local studio graph to the ComfyUI frontend."""
import json
from pathlib import Path
from aiohttp import web
from server import PromptServer

ROOT=Path(__file__).resolve().parents[4]

@PromptServer.instance.routes.get('/local-story-studio/staged')
async def staged(request):
    path=ROOT/'Harness/staged-workflow.json'
    if not path.exists():
        return web.json_response({'error':'Stage a shot from Local Story Studio first.'},status=404)
    return web.json_response(json.loads(path.read_text(encoding='utf-8')))

NODE_CLASS_MAPPINGS={}
WEB_DIRECTORY='./web'

@PromptServer.instance.routes.get('/local-story-studio/lab-progress')
async def lab_progress(request):
    path=ROOT/'Workflows/krea-h3-lab/progress.json'
    return web.json_response(json.loads(path.read_text(encoding='utf-8')) if path.exists() else {})

@PromptServer.instance.routes.post('/local-story-studio/backup')
async def backup(request):
    import uuid
    body = await request.json()
    if not isinstance(body, dict) or not isinstance(body.get('nodes'), list):
        return web.json_response({'error': 'Invalid canvas'}, status=400)
    folder = ROOT / 'Studio/canvas-backups'
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + '.json'
    (folder / name).write_text(json.dumps(body), encoding='utf-8')
    return web.json_response({'file': 'Studio/canvas-backups/' + name})
