import runtime_paths
"""Isolated, project-scoped 3D, speech and lip-sync jobs."""
import base64,json,math,os,re,subprocess,threading,time
from pathlib import Path
import studio_store as store
import production

ROOT=store.ROOT
LOCK=threading.Lock()
PYTHON=runtime_paths.path('python', ROOT)
BLENDER=runtime_paths.path('blender', ROOT)


def vector(value,limit=1000,positive=False):
 if not isinstance(value,list) or len(value)!=3 or any(not isinstance(v,(float,int)) or not math.isfinite(v) or abs(v)>limit or (positive and v<=0) for v in value):
  raise ValueError('Invalid 3D vector')
 return value


def color(value):
 if not isinstance(value,str) or not re.fullmatch('#[0-9a-fA-F]{6}',value):raise ValueError('Use a hex color')
 return value


def scene_valid(value):
 if not isinstance(value,dict) or not str(value.get('name','')).strip():raise ValueError('Name the 3D scene')
 value=json.loads(json.dumps(value))
 if len(value.get('objects',[]))>100 or not 1<=len(value.get('lights',[]))<=8:raise ValueError('Use at most 100 objects and 1â€“8 lights')
 ids=set()
 for obj in value['objects']:
  if obj['type'] not in ('cube','sphere','cylinder','cone','plane') or not re.fullmatch('[a-f0-9-]{12,40}',obj['id']) or obj['id'] in ids:raise ValueError('Invalid object')
  ids.add(obj['id']);vector(obj['position']);vector(obj['scale'],100,True);vector(obj['rotation'],3600);color(obj['color'])
  obj['name']=str(obj['name'])[:120]
 for light in value['lights']:
  vector(light['position']);vector(light['target']);color(light['color'])
  if not 0<float(light['power'])<=10000 or not .01<=float(light['size'])<=100:raise ValueError('Light settings out of range')
 vector(value['camera']['position']);vector(value['camera']['target'])
 if not 10<=float(value['camera']['lens'])<=300:raise ValueError('Lens out of range')
 motion=value.get('motion',{'preset':'still','seconds':5})
 if not isinstance(motion,dict) or motion.get('preset') not in ('still','orbit','dolly-in','dolly-out','truck-left','truck-right'):raise ValueError('Choose a supported camera move')
 seconds=motion.get('seconds',5)
 if isinstance(seconds,bool) or not isinstance(seconds,(float,int)) or not math.isfinite(seconds) or not 1<=seconds<=15:raise ValueError('Camera moves must last 1–15 seconds')
 value['motion']={'preset':motion['preset'],'seconds':seconds}
 if tuple((value['width'],value['height'])) not in ((640,360),(1280,720),(1920,1080)):raise ValueError('Choose a supported render size')
 return value


def env():
 result=dict(os.environ)
 for name,part in [('BLENDER_USER_CONFIG','User/blender/config'),('BLENDER_USER_SCRIPTS','User/blender/scripts'),('BLENDER_USER_DATAFILES','User/blender/data'),('NUMBA_CACHE_DIR','Cache/numba')]:
  path=ROOT/part;path.mkdir(parents=True,exist_ok=True);result[name]=str(path)
 result['HF_HUB_OFFLINE']='1';result['TRANSFORMERS_OFFLINE']='1'
 return result


def run_process(args,folder):
 with (folder/'worker.log').open('w',encoding='utf-8') as log:
  process=subprocess.run(args,cwd=ROOT,env=env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
    timeout=1800,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 if process.returncode:
  raise ValueError('Local worker failed: '+(folder/'worker.log').read_text(encoding='utf-8',errors='replace')[-1600:])
 return json.loads((folder/'result.json').read_text(encoding='utf-8'))


def dispatch(p,data):
 import studio_api as api
 action=data['action'].removeprefix('advanced/')
 if action=='blender-launch':
  if not BLENDER.is_file():raise ValueError('Portable Blender is not installed')
  subprocess.Popen([str(BLENDER),'--disable-autoexec'],cwd=ROOT,env=env(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  return dict(project=p,message='Portable Blender opened with project-local preferences')
 if action=='scene-save':
  scene=scene_valid(data['value']);key=data.get('id') or store.identifier();scene['id']=key
  def save(doc):
   records=doc.setdefault('sets3d',[])
   if data.get('id'):
    existing=next((s for s in records if s['id']==key),None)
    if existing is None:raise ValueError('Unknown 3D scene')
    existing.update(scene)
   else:records.append(scene)
  return dict(project=store.mutate(p['id'],data['revision'],'scene-3d-save',save),message='3D scene saved')
 if action=='voice-save':
  value=data['value'];key=data.get('id') or store.identifier()
  if not str(value.get('name','')).strip() or value.get('speaker') not in ('Vivian','Serena','Uncle_Fu','Dylan','Eric','Ryan','Aiden','Ono_Anna','Sohee'):
   raise ValueError('Name the voice and choose a supported speaker')
  voice=dict(id=key,name=str(value['name'])[:120],speaker=value['speaker'],language='English',instruct=str(value.get('instruct',''))[:2000],seed=int(value.get('seed',42)))
  def save(doc):
   records=doc.setdefault('voices',[])
   if data.get('id'):
    existing=next((v for v in records if v['id']==key),None)
    if existing is None:raise ValueError('Unknown voice')
    existing.update(voice)
   else:records.append(voice)
  return dict(project=store.mutate(p['id'],data['revision'],'voice-save',save),message='Reusable voice profile saved')
 if action=='blender-open':
  job=api.item(p,'jobs',data['job']);file=production.local_file(job['result']['blend'])
  if file.suffix!='.blend' or not file.is_relative_to((ROOT/'Projects'/p['id']).resolve()):raise ValueError('Choose this projectâ€™s Blender scene')
  subprocess.Popen([str(BLENDER),'--disable-autoexec',str(file)],cwd=ROOT,env=env(),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  return dict(project=p,message='Opened in the bundled portable Blender')
 if action not in ('blender-render','blender-rerender','speak','lipsync'):raise ValueError('Unknown advanced action')
 if not LOCK.acquire(False):raise ValueError('Another advanced render is running')
 try:
  import comfy_service,local_ai
  if local_ai.JOB['busy'] or production.JOB['busy'] or api.WORK.locked():raise ValueError('Wait for the current studio operation')
  if comfy_service.status()['busy']:raise ValueError('Finish the current ComfyUI queue first')
  if action=='blender-rerender':
   prior=api.item(p,'jobs',data['job']);file=production.local_file(prior['result']['blend'])
   if file.suffix!='.blend' or not file.is_relative_to((ROOT/'Projects'/p['id']).resolve()):raise ValueError('Choose a Blender scene from this project')
   payload=dict(blend=str(file),name='Edited Blender scene')
  elif action=='blender-render':
   if not BLENDER.exists():raise ValueError('Portable Blender installation is still in progress')
   scene=next((s for s in p.get('sets3d',[]) if s['id']==data['scene']),None)
   if not scene:raise ValueError('Choose a saved 3D scene')
   payload=scene_valid(scene)
  elif action=='speak':
   voice=next((v for v in p.get('voices',[]) if v['id']==data['voice']),None)
   text=str(data.get('text','')).strip()
   if not voice or not 1<=len(text)<=2000:raise ValueError('Choose a voice and enter 1â€“2000 characters')
   payload=dict(voice=voice,text=text)
  else:
   image=api.item(p,'assets',data['image']);audio=api.item(p,'assets',data['audio'])
   if image['kind']!='image' or not audio.get('audio') or audio['duration']>30:raise ValueError('Choose a portrait image and audio of up to 30 seconds')
   box=data['box']
   if not isinstance(box,list) or len(box)!=4 or any(not isinstance(v,(int,float)) or not 0<=v<=1 for v in box) or box[2]<=box[0] or box[3]<=box[1]:raise ValueError('Draw a face rectangle')
   payload=dict(image=str(api.source_of(p,image['id'])),audio=str(api.source_of(p,audio['id'])),box=box)
  key=store.identifier();folder=ROOT/'Projects'/p['id']/'advanced'/key;folder.mkdir(parents=True)
  production.write(folder/'input.json',payload)
  job=dict(id=key,type=action,status='running',created=time.time(),log=production.relative(folder/'worker.log'))
  updated=store.mutate(p['id'],data['revision'],action,lambda doc:doc['jobs'].append(job))
 except Exception:
  LOCK.release();raise
 def work():
  try:
   # These short-lived workers own their allocations; do not overlap other model servers.
   comfy_service.stop({});local_ai.stop()
   if action=='blender-rerender':
    args=[str(BLENDER),'--background','--disable-autoexec',payload['blend'],'--python',str(ROOT/'Harness/blender_saved.py'),'--',str(folder)]
   elif action=='blender-render':
    args=[str(BLENDER),'--background','--factory-startup','--disable-autoexec','--python',str(ROOT/'Harness/blender_scene.py'),'--',str(folder/'input.json')]
   else:args=[str(PYTHON),str(ROOT/'Harness/media_worker.py'),action,str(folder/'input.json')]
   result=run_process(args,folder)
   if result.get('frames'):
    import imageio_ffmpeg
    video=folder/'camera-preview.mp4'
    with (folder/'encode.log').open('w',encoding='utf-8') as log:
     subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate',str(result['fps']),'-i',str(folder/'frames/%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,stdout=log,stderr=log,timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    result['file']=str(video)
   source=Path(result['file']);asset=api.asset_record(p,source,('3D render Â· '+payload['name']) if action.startswith('blender-') else 'Voice take' if action=='speak' else 'Lip-sync take',dict(job=key,adapter=action,input=production.relative(folder/'input.json')))
   result['file']=asset['file']
   if result.get('blend'):result['blend']=production.relative(Path(result['blend']))
   def finish(doc):
    doc['assets'].append(asset);api.item(doc,'jobs',key).update(status='complete',result=result)
   store.mutate(p['id'],None,action+'-complete',finish)
  except Exception as e:
   store.mutate(p['id'],None,action+'-failed',lambda doc:api.item(doc,'jobs',key).update(status='failed',error=str(e)))
  finally:LOCK.release()
 threading.Thread(target=work,daemon=True).start()
 return dict(project=updated,message='Local '+action+' started. Its output will appear in Assets; progress and errors are in Jobs.')
