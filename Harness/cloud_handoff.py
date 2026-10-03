"""Explicit asset handoff using the documented Higgsfield media upload API.

This is not a native Cinema Studio project import and never submits generation.
"""
import json,time,threading,urllib.request,urllib.parse
from pathlib import Path
import production,studio_store as store
ROOT=store.ROOT
CONFIG=ROOT/'User/higgsfield-api.json'
LOCK=threading.Lock()

def dispatch(p,data):
 if not LOCK.acquire(False):raise ValueError('Wait for the current cloud handoff operation')
 try:return execute(p,data)
 finally:LOCK.release()

def execute(p,data):
 import studio_api as api
 action=data['action']
 if action=='cloud/configure':
  key=str(data.get('key','')).strip();secret=str(data.get('secret','')).strip()
  if not key or not secret or any(c in key+secret for c in '\r\n'):raise ValueError('Enter both API key fields')
  production.write(CONFIG,dict(key=key,secret=secret))
  return dict(project=p,message='Credentials saved only in User/higgsfield-api.json. Keep this portable folder private. No upload or generation was started.')
 if action=='cloud/forget':
  CONFIG.unlink(missing_ok=True)
  return dict(project=p,message='Local API credentials removed')
 if action=='cloud/plan':
  assets=[dict(id=a['id'],name=a['name'],file=a['file'],sha256=a['sha256']) for a in p['assets'] if not a.get('deleted') and a.get('review')=='approved']
  plan=dict(project=p['id'],title=p['title'],revision=p['revision'],assets=assets,elements=p['elements'],scenes=p['scenes'],shots=p['shots'],timeline=p['timeline'],mode='Assistant handoff; native project sync requires supported connector actions',created=time.time())
  path=ROOT/'Projects'/p['id']/'handoff'/'sync-plan.json';production.write(path,plan)
  return dict(project=p,message='Reviewable handoff plan prepared. No files uploaded.',download='/studio-file/'+production.relative(path))
 if action!='cloud/upload':raise ValueError('Unknown cloud action')
 if not CONFIG.exists():raise ValueError('Configure your Higgsfield developer API credentials first')
 if data.get('confirm_upload') is not True:raise ValueError('Explicitly choose Upload selected assets')
 keys=data.get('assets',[])
 if not isinstance(keys,list) or not 1<=len(keys)<=50:raise ValueError('Select 1–50 approved assets')
 selected=[api.item(p,'assets',key) for key in dict.fromkeys(keys)]
 if any(a.get('review')!='approved' for a in selected):raise ValueError('Approve each selected asset before uploading')
 credentials=json.loads(CONFIG.read_text(encoding='utf-8'));sent=[]
 for asset in selected:
  existing=next((x for x in p.get('cloud_assets',[]) if x['sha256']==asset['sha256']),None)
  if existing and not data.get('refresh'):continue
  source=api.source_of(p,asset['id']);kind={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.wav':'audio/wav','.mp4':'video/mp4'}.get(source.suffix.lower())
  if not kind:raise ValueError('Higgsfield upload supports PNG, JPEG, WebP, WAV and MP4 here')
  if source.stat().st_size>256*1024*1024:raise ValueError('This upload adapter accepts files up to 256 MB')
  request=urllib.request.Request('https://api.higgsfield.ai/files/generate-upload-url',data=json.dumps(dict(content_type=kind)).encode(),headers={'Authorization':'Key '+credentials['key']+':'+credentials['secret'],'Content-Type':'application/json'},method='POST')
  try:
   with urllib.request.urlopen(request,timeout=30) as response:upload=json.load(response)
   for name in ('upload_url','public_url'):
    if urllib.parse.urlparse(upload[name]).scheme!='https':raise ValueError('Upload service returned an invalid URL')
   headers=upload.get('upload_headers',{'Content-Type':kind})
   # API credentials must never be sent to the storage host.
   if any(k.lower()=='authorization' for k in headers):raise ValueError('Unexpected storage authorization header')
   with source.open('rb') as stream:
    request=urllib.request.Request(upload['upload_url'],data=stream.read(),headers=headers,method='PUT')
    with urllib.request.urlopen(request,timeout=180) as response:response.read()
  except urllib.error.HTTPError as e:raise ValueError('Higgsfield upload HTTP '+str(e.code)+'. Check API credentials and account access.') from None
  receipt=dict(asset=asset['id'],sha256=asset['sha256'],url=upload['public_url'],uploaded=time.time(),retention='Provider-managed; refresh before a later render')
  def save(doc):
   records=doc.setdefault('cloud_assets',[]);records[:]=[r for r in records if r['sha256']!=asset['sha256']];records.append(receipt)
  # Save each successful file so a failed later upload can resume without duplicating it.
  p=store.mutate(p['id'],p['revision'],'cloud-asset-upload',save);sent.append(receipt)
 return dict(project=p,message=f'{len(sent)} asset(s) uploaded. Public input URLs are saved; no generation was submitted and no Cinema Studio project was created.')
