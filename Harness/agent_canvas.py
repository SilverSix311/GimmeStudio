"""Run an approved preset through the visible portable ComfyUI browser."""
import os,sys,json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Harness'))
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'Tools/browsers')
import studio_store,studio_api
from playwright.sync_api import sync_playwright
key,jobid=sys.argv[1:3];p=studio_store.get(key);job=studio_api.item(p,'jobs',jobid)
expected=json.loads((ROOT/job['graph']).read_text(encoding='utf-8'))
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=False,args=['--disable-breakpad','--disable-crash-reporter'])
 page=browser.new_page(viewport={'width':1600,'height':1000})
 page.goto('http://127.0.0.1:8188',wait_until='networkidle',timeout=60000)
 page.get_by_role('button',name='Load studio shot',exact=True).click(timeout=60000)
 page.wait_for_timeout(1500)
 actual=page.evaluate("async()=>{const {app}=await import('/scripts/app.js');return await app.graphToPrompt()}")
 tag=actual['workflow'].get('extra',{}).get('gimmestudio',{})
 if tag.get('project')!=key or tag.get('job')!=jobid:raise ValueError('Staged canvas changed before execution')
 for node,spec in expected.items():
  if node not in actual['output'] or actual['output'][node]['class_type']!=spec['class_type'] or not all(actual['output'][node]['inputs'].get(k)==v for k,v in spec['inputs'].items()):raise ValueError('Canvas differs from the approved preset; review it before running')
 with page.expect_response(lambda r:r.url.endswith('/api/prompt') and r.request.method=='POST',timeout=30000) as response:page.get_by_role('button',name='Run',exact=True).click()
 reply=response.value.json();print(json.dumps(reply),flush=True)
 if 'prompt_id' not in reply:raise ValueError('ComfyUI rejected the graph')
 deadline=time.time()+1700
 while time.time()<deadline:
  with urllib.request.urlopen('http://127.0.0.1:8188/history/'+reply['prompt_id']) as r:history=json.load(r)
  if reply['prompt_id'] in history:
   record=history[reply['prompt_id']]
   if record['status']['status_str']!='success':raise ValueError(json.dumps(record['status']))
   print('Visible generation finished',flush=True);break
  page.wait_for_timeout(1500)
 else:raise TimeoutError('Generation still running. Inspect ComfyUI before retrying.')
 browser.close()
