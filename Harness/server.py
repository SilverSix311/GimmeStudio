"""Local-only episode workbench. Uses only the two localhost inference services."""
import hashlib, html, io, json, mimetypes, re, shutil, threading, time, urllib.request, uuid, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from visible_workflow import canvas
import production
import local_ai
import studio_api
import studio_store
ROOT=Path(__file__).resolve().parents[1]
PROJECTS=ROOT/'Projects'
COMFY='http://127.0.0.1:8188'
LLM='http://127.0.0.1:8189'
LOCK=threading.Lock()
STATE={'busy':False,'message':'Ready','error':None}
def request(url, data=None, timeout=180):
    raw=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(url,raw,{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)
def project_dir(key):
    if not re.fullmatch(r'[a-f0-9]{12}',key): raise ValueError('Invalid project ID')
    return PROJECTS/key
def read(key): return json.loads((project_dir(key)/'episode.json').read_text())
def fingerprint(p):
    return hashlib.sha256(json.dumps({k:p[k] for k in ('title','style','characters','shots')},sort_keys=True).encode()).hexdigest()
def persist(p):
    d=project_dir(p['id']); d.mkdir(parents=True,exist_ok=True)
    f=d/'episode.json'
    if f.exists():
        revisions=d/'revisions'; revisions.mkdir(exist_ok=True)
        shutil.copy2(f,revisions/(str(time.time_ns())+'.json'))
    temp=d/'episode.tmp'; temp.write_text(json.dumps(p,indent=2),encoding='utf-8'); temp.replace(f)
def validate(p):
    for key in ('title','style','characters'):
        if not isinstance(p.get(key),str) or not p[key].strip(): raise ValueError(key+' is required')
    shots=p.get('shots')
    if not isinstance(shots,list) or not 1<=len(shots)<=24: raise ValueError('Use 1–24 shots')
    ids=set()
    for s in shots:
        if not isinstance(s.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',s['id']) or s['id'] in ids: raise ValueError('Shot IDs must be unique simple names')
        ids.add(s['id'])
        if not isinstance(s.get('prompt'),str) or not s['prompt'].strip(): raise ValueError('Each shot needs a prompt')
        if not isinstance(s.get('duration'),(int,float)) or not 1<=s['duration']<=30: raise ValueError('Shot duration must be 1–30 seconds')
        s.setdefault('dialogue',''); s.setdefault('camera',''); s.setdefault('seed',42)
        if not isinstance(s['seed'],int) or not 0<=s['seed']<2**63: raise ValueError('Invalid seed')
    return p
def plan(data):
    bible=json.loads((ROOT/'Harness/series-bible.json').read_text(encoding='utf-8'))
    schema={'title':'Episode title','style':'visual style','characters':'fixed character descriptions and continuity rules','shots':[{'id':'shot-01','duration':8,'prompt':'one clear visual action and composition','dialogue':'spoken words','camera':'camera direction','seed':42}]}
    system='You are a storyboard planner for original children’s cartoons ages 6–9. Return ONLY a JSON object matching this example: '+json.dumps(schema)+'. Produce 6 concise shots, a beginning, problem, attempts, payoff, and warm ending. Use the requested characters faithfully. Keep neurodivergence subtle and avoid stereotypes. No promises of virality. Separate dialogue from image prompts. Each image prompt must describe a single still composition, not a montage. Do not name existing studios or franchises. /no_think'
    system+=' Canonical series bible: '+json.dumps(bible)+'. Never redefine these characters. Use character names instead of third-person pronouns in visual prompts. Maxi is not a boy or a girl; do not gender Maxi. Rush is a boy and Taski is male.'
    result=request(LLM+'/v1/chat/completions',{'model':'local','messages':[{'role':'system','content':system},{'role':'user','content':data['brief']}],'temperature':0.5,'max_tokens':2600,'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}})
    text=result['choices'][0]['message']['content']
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S).strip()
    if text.startswith('```'): text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    p=json.loads(text); p['characters']=bible['characters']; p['style']=bible['style']
    p=validate(p); p.update(id=uuid.uuid4().hex[:12],brief=data['brief'],approved=None,renders={},created=time.time(),series_rules=bible['rules'])
    persist(p); STATE['project']=p['id']; STATE['message']='Local draft ready to edit'
def graph(p,s,checkpoint,lora=None):
    # Put the shot's action before the longer character bible; SDXL weights early tokens strongly.
    positive='Single cinematic image from a 3D animated movie. '+s['prompt']+'. '+s['camera']+'. '+p['style']+'. '+p['characters']
    g={'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':checkpoint}},
       '2':{'class_type':'CLIPTextEncode','inputs':{'text':positive,'clip':['1',1]}},
       '3':{'class_type':'CLIPTextEncode','inputs':{'text':'collage, panels, comic strip, character sheet, multiple views, text, watermark, logo, blurry, malformed hands, extra limbs, photorealistic','clip':['1',1]}},
       '4':{'class_type':'EmptyLatentImage','inputs':{'width':1024,'height':576,'batch_size':1}},
       '5':{'class_type':'KSampler','inputs':{'seed':s['seed'],'steps':20,'cfg':6,'sampler_name':'euler','scheduler':'normal','denoise':1,'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0]}},
       '6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
       '7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'local-drafts/'+p['id']+'/'+s['id']}}}
    if lora:
        g['8']={'class_type':'LoraLoader','inputs':{'model':['1',0],'clip':['1',1],'lora_name':lora,'strength_model':0.65,'strength_clip':0.65}}
        g['2']['inputs']['clip']=['8',1];g['3']['inputs']['clip']=['8',1];g['5']['inputs']['model']=['8',0]
    return g
def render(data):
    p=read(data['id']); version=fingerprint(p)
    models=request(COMFY+'/object_info/CheckpointLoaderSimple')['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
    ckpt=data.get('checkpoint') or 'sd_xl_base_1.0.safetensors'
    if ckpt not in models: raise ValueError('Selected checkpoint not found in Models/checkpoints')
    lora=data.get('lora') or None
    if lora and lora not in request(COMFY+'/object_info/LoraLoader')['LoraLoader']['input']['required']['lora_name'][0]: raise ValueError('LoRA not found')
    shots=p['shots'] if not data.get('shot') else [s for s in p['shots'] if s['id']==data['shot']]
    if not shots: raise ValueError('Shot not found')
    for s in shots:
        STATE['message']='Rendering '+s['id']
        workflow=graph(p,s,ckpt,lora)
        result=request(COMFY+'/prompt',{'prompt':workflow,'client_id':'local-studio'})
        job=result['prompt_id']; deadline=time.time()+600
        while time.time()<deadline:
            history=request(COMFY+'/history/'+job)
            if job in history:
                h=history[job]
                if h.get('status',{}).get('status_str')=='error': raise RuntimeError(json.dumps(h['status']))
                outputs=h.get('outputs',{}).get('7',{}).get('images',[])
                if outputs: break
            time.sleep(1)
        else: raise TimeoutError('ComfyUI render timed out; inspect its queue before retrying')
        out=outputs[0]
        source=(ROOT/'Output'/out['subfolder']/out['filename']).resolve()
        if not source.is_relative_to((ROOT/'Output').resolve()): raise ValueError('Output path escaped workspace')
        folder=project_dir(p['id'])/'boards';folder.mkdir(exist_ok=True)
        filename=s['id']+'-'+uuid.uuid4().hex[:8]+'.png'
        shutil.copy2(source,folder/filename)
        (folder/(filename+'.workflow.json')).write_text(json.dumps(workflow,indent=2))
        p['renders'][s['id']]={'file':'boards/'+filename,'fingerprint':version,'checkpoint':ckpt,'lora':lora,'seed':s['seed'],'job_id':job}
        p['approved']=None;persist(p)
    STATE['message']='Storyboard render complete'

def stage(data):
    p=read(data['id'])
    shot=next((s for s in p['shots'] if s['id']==data.get('shot')),p['shots'][0])
    workflow=graph(p,shot,data.get('checkpoint') or 'sd_xl_base_1.0.safetensors',data.get('lora') or None)
    catalog={kind:request(COMFY+'/object_info/'+kind)[kind] for kind in {n['class_type'] for n in workflow.values()}}
    ui=canvas(workflow,catalog,p['title']+' / '+shot['id'])
    ui['extra']['local_story_studio'].update(project=p['id'],shot=shot['id'],fingerprint=fingerprint(p))
    folder=project_dir(p['id'])/'workflows';folder.mkdir(exist_ok=True)
    name=shot['id']+'-'+uuid.uuid4().hex[:8]+'.json'
    (folder/name).write_text(json.dumps(ui,indent=2),encoding='utf-8')
    pending=ROOT/'Harness/staged-workflow.json'
    temp=pending.with_suffix('.tmp')
    temp.write_text(json.dumps({'title':p['title']+' / '+shot['id'],'workflow':ui}),encoding='utf-8');temp.replace(pending)
    STATE['workflow_download']='/files/'+p['id']+'/workflows/'+name
    STATE['message']='Shot staged. In ComfyUI click Load studio shot, edit the canvas, then click Run. Save your current canvas before loading another shot.'

def stage_lab(data):
    kind=data.get('kind')
    if kind not in ('krea','h3'): raise ValueError('Unknown lab workflow')
    ui=json.loads((ROOT/'Workflows/krea-h3-lab'/(kind+'.json')).read_text(encoding='utf-8'))
    title='Maxi and Taski - '+('Krea 2 keyframe' if kind=='krea' else 'H3 motion study')
    target=ROOT/'Harness/staged-workflow.json';temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps({'title':title,'stage_id':uuid.uuid4().hex,'workflow':ui}),encoding='utf-8');temp.replace(target)
    STATE['message']=title+' staged. Open ComfyUI and click Load studio shot.'

def lab_status():
    folder=ROOT/'Workflows/krea-h3-lab';result={'downloads':[],'runs':{},'image':(folder/'maxi-krea-start.png').exists(),'video':(folder/'maxi-h3.mp4').exists()}
    plan=ROOT/'Models/krea-h3-download-plan.json'
    if plan.exists():
        for item in json.loads(plan.read_text()):
            target=ROOT/'Models'/item['file'];partial=target.with_suffix('.safetensors.partial')
            result['downloads'].append({'name':target.name,'total':item['size'],'bytes':target.stat().st_size if target.exists() else partial.stat().st_size if partial.exists() else 0,'verified':target.exists() and target.stat().st_size==item['size']})
    for kind in ('krea','h3'):
        path=folder/(kind+'-history.json')
        if path.exists():
            history=json.loads(path.read_text());result['runs'][kind]=history.get('status',{})
    return result

def collect(data):
    p=read(data['id']);fp=fingerprint(p);count=0;seen=set()
    history=request(COMFY+'/history?max_items=100')
    for job,h in sorted(history.items(),key=lambda item:item[1]['prompt'][0],reverse=True):
        prompt=h.get('prompt',[])
        if len(prompt)<4: continue
        ui=prompt[3].get('extra_pnginfo',{}).get('workflow',{})
        tag=ui.get('extra',{}).get('local_story_studio',{})
        if tag.get('project')!=p['id'] or tag.get('fingerprint')!=fp: continue
        shot=tag.get('shot')
        if shot not in {s['id'] for s in p['shots']}: continue
        outputs=h.get('outputs',{}).get('7',{}).get('images',[])
        if h.get('status',{}).get('status_str')!='success' or not outputs: continue
        if shot in seen: continue
        seen.add(shot)
        if p.get('renders',{}).get(shot,{}).get('job_id')==job: continue
        out=outputs[0]
        if out.get('type')!='output': continue
        source=(ROOT/'Output'/out['subfolder']/out['filename']).resolve()
        if not source.is_relative_to((ROOT/'Output').resolve()): raise ValueError('Output path escaped workspace')
        folder=project_dir(p['id'])/'boards';folder.mkdir(exist_ok=True)
        name=shot+'-'+uuid.uuid4().hex[:8]+'.png';shutil.copy2(source,folder/name)
        (folder/(name+'.workflow.json')).write_text(json.dumps(prompt[2],indent=2),encoding='utf-8')
        (folder/(name+'.canvas.json')).write_text(json.dumps(ui,indent=2),encoding='utf-8')
        p.setdefault('renders',{})[shot]={'file':'boards/'+name,'fingerprint':fp,'job_id':job,'source':'ComfyUI canvas','canvas':'boards/'+name+'.canvas.json'}
        count+=1
    if count: p['approved']=None;persist(p)
    STATE['message']=f'Collected {count} canvas render(s). Only completed shots from this saved revision are imported.'
def approve(data):
    p=read(data['id']);fp=fingerprint(p)
    if any(p.get('renders',{}).get(s['id'],{}).get('fingerprint')!=fp for s in p['shots']): raise ValueError('Render every current shot before locking VISION')
    p['approved']={'fingerprint':fp,'at':time.time()};persist(p);STATE['message']='VISION locked; ready to export'
def export(data):
    p=read(data['id']);fp=fingerprint(p)
    if not p.get('approved') or p['approved']['fingerprint']!=fp: raise ValueError('Lock the current VISION before export')
    d=project_dir(p['id']);folder=d/'handoff'/fp[:10];folder.mkdir(parents=True,exist_ok=True)
    (folder/'VISION.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
    lines=['# '+p['title'],'','Audience: children ages 6–9','',p['style'],'',p['characters'],'','Draft images are composition references; final identity consistency needs review.','No Higgsfield jobs have been submitted.','']
    for s in p['shots']:
        lines+=['## '+s['id']+' — '+str(s['duration'])+' seconds',s['prompt'],'Camera: '+s['camera'],'Dialogue: '+s['dialogue'],'Seed: '+str(s['seed']),'Reference: '+p['renders'][s['id']]['file'],'']
    (folder/'HIGGSFIELD-SHOT-PACKET.md').write_text('\n'.join(lines),encoding='utf-8')
    archive='VISION-'+fp[:10]+'-handoff.zip'
    with zipfile.ZipFile(d/archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in folder.iterdir(): z.write(f,f.name)
        for s in p['shots']:
            f=d/p['renders'][s['id']]['file']; z.write(f,p['renders'][s['id']]['file']);z.write(Path(str(f)+'.workflow.json'),p['renders'][s['id']]['file']+'.workflow.json')
            if p['renders'][s['id']].get('canvas'): z.write(d/p['renders'][s['id']]['canvas'],p['renders'][s['id']]['canvas'])
    STATE['message']='Handoff ZIP exported locally';STATE['download']='/files/'+p['id']+'/'+archive
def status():
    result=dict(STATE)
    result['projects']=[{'id':f.parent.name,'title':json.loads(f.read_text())['title']} for f in sorted(PROJECTS.glob('*/episode.json'),key=lambda f:f.stat().st_mtime,reverse=True)]
    result['services']={}
    for name,url in [('comfy',COMFY+'/system_stats'),('planner',LLM+'/health')]:
        try: request(url,timeout=1);result['services'][name]=True
        except Exception: result['services'][name]=False
    result['checkpoints']=[str(f.relative_to(ROOT/'Models/checkpoints')).replace('\\','/') for f in (ROOT/'Models/checkpoints').rglob('*.safetensors')]
    family_file=ROOT/'Models/model-families.json'
    families=json.loads(family_file.read_text()).get('loras',{}) if family_file.exists() else {}
    result['loras']=[str(f.relative_to(ROOT/'Models/loras')).replace('\\','/') for f in (ROOT/'Models/loras').rglob('*.safetensors') if families.get(f.name,'sdxl')=='sdxl']
    return result
def run_action(action,data):
    try:
        {'plan':plan,'render':render,'stage':stage,'stage_lab':stage_lab,'collect':collect,'approve':approve,'export':export}[action](data)
    except Exception as e: STATE.update(error=str(e),message='Action failed')
    finally: STATE['busy']=False;LOCK.release()
class Handler(BaseHTTPRequestHandler):
    def send_file(self, path):
        size = path.stat().st_size
        start, end, partial = 0, size - 1, False
        requested = self.headers.get('Range')
        if requested:
            import re
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
            if not match or not any(match.groups()):
                return self.send({'error':'Unsupported byte range'},416)
            a, b = match.groups()
            start = int(a) if a else max(0,size-int(b))
            end = min(int(b),size-1) if a and b else size-1
            if start > end or start >= size:
                return self.send({'error':'Byte range outside file'},416)
            partial = True
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Cache-Control','no-store')
        if partial:
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as f:
                f.seek(start)
                remaining=end-start+1
                while remaining>0:
                    chunk=f.read(min(1024*1024,remaining))
                    if not chunk: break
                    self.wfile.write(chunk)
                    remaining-=len(chunk)
        except (ConnectionError, BrokenPipeError):
            pass

    def send(self,data,code=200,kind='application/json'):
        # Files already contain serialized bytes, including application/json downloads.
        body=data if isinstance(data,bytes) else json.dumps(data).encode() if kind=='application/json' else data
        try:
            self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        except (ConnectionError, BrokenPipeError):
            pass  # A browser navigating away can close an in-flight status request.
    def do_GET(self):
        try:
            path=self.path.split('?')[0]
            if path=='/api/workspace':
                import workspaces
                return self.send(workspaces.state())
            if path=='/help.json': return self.send((ROOT/'Docs/help.json').read_bytes())
            if path=='/help-download': return self.send((ROOT/'Studio/help/GimmeStudio-wiki.zip').read_bytes(),kind='application/zip')
            if path.startswith('/api/agent/state/'):
                import local_agent
                return self.send(local_agent.public(path.rsplit('/',1)[1]))
            if path=='/api/studio': return self.send(studio_api.status())
            if path=='/api/studio/loras':
                import shot_controls
                return self.send({'items':shot_controls.inventory(ROOT)})
            if path=='/api/studio/services':
                import advanced_studio, local_agent
                return self.send({'planner_running': bool(local_ai.owned_process()), 'agent_busy':local_agent.busy(), 'comfy':production.comfy_service.status(), 'production':dict(production.JOB),
                                  'ai':dict(local_ai.JOB), 'studio_finishing':studio_api.WORK.locked(), 'advanced_busy':advanced_studio.LOCK.locked()})
            if path.startswith('/api/studio/project/'): return self.send(studio_store.get(path.rsplit('/',1)[1]))
            if path.startswith('/api/studio/history/'): return self.send(studio_store.history(path.rsplit('/',1)[1]))
            if path in ('/studio.js','/studio.css','/advanced.js','/help.js','/agent.js','/creative_tools.js'):
                return self.send((ROOT/'Harness'/path[1:]).read_bytes(),kind='text/javascript' if path.endswith('.js') else 'text/css')
            if path=='/legacy': return self.send((ROOT/'Harness/dashboard.html').read_bytes(),kind='text/html; charset=utf-8')
            if path=='/api/ai': return self.send(local_ai.state())
            if path.startswith('/api/ai/chat/'): return self.send(local_ai.read_chat(path.rsplit('/',1)[1]))
            if path=='/api/production': return self.send(production.state())
            if path=='/': return self.send((ROOT/'Harness/studio.html').read_bytes(),kind='text/html; charset=utf-8')
            if path.startswith('/studio-file/'):
                from urllib.parse import unquote
                f=production.local_file(unquote(path[len('/studio-file/'):]))
                return self.send_file(f)
            if path=='/api/status': return self.send(status())
            if path=='/api/lab': return self.send(lab_status())
            if path=='/lab': return self.send((ROOT/'Harness/lab.html').read_bytes(),kind='text/html; charset=utf-8')
            if path.startswith('/lab-files/'):
                from urllib.parse import unquote
                base=(ROOT/'Workflows/krea-h3-lab').resolve();f=(base/unquote(path[11:])).resolve()
                if not f.is_relative_to(base) or not f.is_file(): raise ValueError('File not found')
                return self.send(f.read_bytes(),kind=mimetypes.guess_type(f.name)[0] or 'application/octet-stream')
            if path.startswith('/api/project/'): return self.send(read(path.rsplit('/',1)[1]))
            if path=='/story': return self.send((ROOT/'Harness/index.html').read_bytes(),kind='text/html; charset=utf-8')
            if path.startswith('/library/'):
                from urllib.parse import unquote
                base=(ROOT/'Workflows/model-library').resolve();f=(base/unquote(path[9:])).resolve()
                if not f.is_relative_to(base) or not f.is_file(): raise ValueError('File not found')
                return self.send(f.read_bytes(),kind=mimetypes.guess_type(f.name)[0] or 'application/octet-stream')
            if path.startswith('/files/'):
                from urllib.parse import unquote
                f=(PROJECTS/unquote(path[7:])).resolve()
                if not f.is_relative_to(PROJECTS.resolve()) or not f.is_file(): raise ValueError('File not found')
                return self.send(f.read_bytes(),kind=mimetypes.guess_type(f.name)[0] or 'application/octet-stream')
            self.send({'error':'Not found'},404)
        except Exception as e: self.send({'error':str(e)},400)
    def do_POST(self):
        try:
            if self.headers.get('Origin') not in (None,'http://127.0.0.1:8190','http://localhost:8190'): return self.send({'error':'Foreign origin'},403)
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=(90000000 if self.path=='/api/studio/command' else 1000000): raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(length));action=self.path.removeprefix('/api/')
            import local_agent
            if action.startswith('agent/'):
                return self.send(local_agent.dispatch(action.removeprefix('agent/'),data))
            if local_agent.busy(): raise ValueError('Local agent is working. Pause or stop it before manual changes or model controls.')
            import advanced_studio
            if advanced_studio.LOCK.locked() and (action in ('ai/start','production/comfy-start','render') or (action=='studio/command' and data.get('action') in ('render','transcribe'))): raise ValueError('Wait for the local 3D or media worker')
            if action=='workspace/open':
                import workspaces
                return self.send(workspaces.open_workspace(data))
            if action=='studio/command': return self.send(studio_api.command(data))
            if action.startswith('ai') and action=='ai/start' and studio_api.WORK.locked(): raise ValueError('Wait for studio finishing work')
            if action.startswith('ai/'):
                if STATE['busy']: raise ValueError('Episode workbench is busy; wait before using the local AI controls')
                if action=='ai/start' and production.JOB['busy']: raise ValueError('Wait for the current production operation before loading a model')
                return self.send(local_ai.dispatch(action.removeprefix('ai/'),data))
            if action.startswith('production/'):
                if action=='production/comfy-start' and (local_ai.JOB['busy'] or local_ai.owned_process()):
                    raise ValueError('Unload the local AI model before starting ComfyUI')
                return self.send(production.dispatch(action.removeprefix('production/'),data))
            if action not in ('plan','render','stage','stage_lab','collect','save','approve','export'): return self.send({'error':'Unknown action'},404)
            if action=='plan' and local_ai.JOB['busy']: raise ValueError('Local AI is busy')
            if not LOCK.acquire(False): return self.send({'error':'Another operation is running'},409)
            if action=='save':
                try:
                    p=validate(data); old=read(p['id'])
                    p['renders']=old.get('renders',{});p['approved']=None;persist(p);STATE.update(download=None,error=None,message='Revision saved');self.send({'ok':True})
                finally: LOCK.release()
                return
            STATE.update(busy=True,error=None,download=None,project=data.get('id'),message='Starting '+action)
            threading.Thread(target=run_action,args=(action,data),daemon=True).start()
            self.send({'ok':True})
        except Exception as e: self.send({'error':str(e)},400)
if __name__=='__main__':
    PROJECTS.mkdir(exist_ok=True)
    studio_store.migrate()
    studio_store.recover_jobs()
    import local_agent
    local_agent.recover()
    studio_api.migrate_assets()
    print('Local Studio: http://127.0.0.1:8190',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8190),Handler).serve_forever()

