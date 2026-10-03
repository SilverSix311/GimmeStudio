import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import server
class HarnessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=server.ROOT/'Cache');self.original=server.PROJECTS;server.PROJECTS=Path(self.tmp.name)
  self.p={'id':'123456abcdef','title':'Test','style':'3D','characters':'Maxi they/them','shots':[{'id':'one','duration':5,'prompt':'Sandcastle','seed':42,'camera':'wide','dialogue':''}],'renders':{},'approved':None}
 def tearDown(self):
  server.PROJECTS=self.original;self.tmp.cleanup()
 def test_reject_traversal(self):
  with self.assertRaises(ValueError):server.project_dir('../other')
 def test_json_file_download_preserves_bytes(self):
  import threading,urllib.request
  from unittest.mock import patch
  payload=b'{"schema_version": 1, "message": "download me"}\n'
  path=Path(self.tmp.name)/'manifest.json';path.write_bytes(payload)
  http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   with patch.object(server.production,'local_file',return_value=path):
    with urllib.request.urlopen(f'http://127.0.0.1:{http.server_port}/studio-file/Studio/manifest.json',timeout=3) as response:
     self.assertEqual(response.status,200);self.assertEqual(response.headers['Content-Type'],'application/json');self.assertEqual(response.read(),payload)
  finally:http.shutdown();http.server_close();thread.join(timeout=3)
 def test_duplicate_shots_rejected(self):
  p=copy.deepcopy(self.p);p['shots']*=2
  with self.assertRaises(ValueError):server.validate(p)
 def test_lock_requires_current_images(self):
  server.persist(self.p)
  with self.assertRaises(ValueError):server.approve({'id':self.p['id']})
 def test_export_rejects_changed_vision(self):
  p=self.p;p['approved']={'fingerprint':server.fingerprint(p)};p['shots'][0]['duration']=7;server.persist(p)
  with self.assertRaises(ValueError):server.export({'id':p['id']})
 def test_lora_wiring(self):
  g=server.graph(self.p,self.p['shots'][0],'base.safetensors','style.safetensors')
  self.assertEqual(g['5']['inputs']['model'],['8',0]);self.assertEqual(g['2']['inputs']['clip'],['8',1])
 def test_revision_retained(self):
  server.persist(self.p);self.p['title']='Changed';server.persist(self.p)
  self.assertEqual(len(list((server.project_dir(self.p['id'])/'revisions').glob('*.json'))),1)
 def test_approved_export_contains_only_current_frames(self):
  p=self.p;d=server.project_dir(p['id']);(d/'boards').mkdir(parents=True)
  (d/'boards/one.png').write_bytes(b'fixture')
  (d/'boards/one.png.workflow.json').write_text('{}')
  p['renders']={'one':{'file':'boards/one.png','fingerprint':server.fingerprint(p)}}
  server.persist(p);server.approve({'id':p['id']});server.export({'id':p['id']})
  import zipfile
  with zipfile.ZipFile(next(d.glob('VISION-*-handoff.zip'))) as z:
   self.assertIn('VISION.json',z.namelist());self.assertIn('boards/one.png',z.namelist())
if __name__=='__main__':unittest.main()

