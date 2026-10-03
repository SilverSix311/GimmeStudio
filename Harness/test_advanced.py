import copy,io,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import advanced_studio as advanced
import cloud_handoff as cloud
import studio_store as store
import studio_api as api
import production

class AdvancedTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=store.ROOT/'Cache');self.root=Path(self.temp.name)
  self.patches=[patch.object(m,'ROOT',self.root) for m in (store,api,production,advanced,cloud)]
  self.patches += [patch.object(store,'DB',self.root/'studio.db'),patch.object(cloud,'CONFIG',self.root/'User/api.json')]
  for p in self.patches:p.start()
  self.p=store.insert(store.blank('Test'))
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def command(self,action,**data):
  r=api.command(dict(project=self.p['id'],revision=self.p['revision'],action=action,**data));self.p=r['project'];return r
 def scene(self):
  return dict(name='Set',objects=[],lights=[dict(name='Key',position=[2,3,4],target=[0,0,0],power=100,size=2,color='#ffffff')],camera=dict(position=[2,-4,3],target=[0,0,0],lens=50),width=640,height=360)
 def test_scene_rejects_nonfinite_and_unsupported_values(self):
  for change in ('nan','resolution','light'):
   scene=self.scene()
   if change=='nan':scene['camera']['position'][0]=float('nan')
   if change=='resolution':scene['width']=999999
   if change=='light':scene['lights'][0]['power']=-1
   with self.assertRaises(ValueError):advanced.scene_valid(scene)
 def test_voice_and_scene_survive_package_roundtrip(self):
  self.command('advanced/scene-save',value=self.scene())
  self.command('advanced/voice-save',value=dict(name='Guide',speaker='Ryan',seed=42))
  result=self.command('export');source=result['download'].removeprefix('/studio-file/')
  imported=api.import_package(dict(source=source))['project']
  self.assertEqual(imported['sets3d'],self.p['sets3d']);self.assertEqual(imported['voices'],self.p['voices'])
 def test_advanced_edits_reject_stale_revision(self):
  old=self.p['revision'];self.command('advanced/scene-save',value=self.scene())
  with self.assertRaises(ValueError):api.command(dict(project=self.p['id'],revision=old,action='advanced/scene-save',value=self.scene()))
 def asset(self):
  from PIL import Image
  path=self.root/'Input/frame.png';path.parent.mkdir();Image.new('RGB',(32,32),'red').save(path)
  self.command('import',source='Input/frame.png');a=self.p['assets'][-1]
  self.command('put',kind='assets',id=a['id'],value=dict(name='Frame',review='approved'))
  return a
 def test_upload_is_explicit_deduplicated_and_has_no_credentials_in_storage_request(self):
  a=self.asset();self.command('cloud/configure',key='test-key',secret='test-secret')
  with self.assertRaises(ValueError):self.command('cloud/upload',assets=[a['id']])
  calls=[]
  def request(req,**kwargs):
   calls.append(req)
   return io.BytesIO(json.dumps(dict(upload_url='https://storage.example/test',public_url='https://cdn.example/test',upload_headers={'Content-Type':'image/png'})).encode() if len(calls)==1 else b'')
  with patch.object(cloud.urllib.request,'urlopen',side_effect=request):
   self.command('cloud/upload',assets=[a['id']],confirm_upload=True)
   self.command('cloud/upload',assets=[a['id']],confirm_upload=True)
  self.assertEqual(len(calls),2);self.assertIn('Authorization',calls[0].headers);self.assertNotIn('Authorization',calls[1].headers)
  self.assertEqual(len(self.p['cloud_assets']),1)
 def test_handoff_plan_never_uploads(self):
  with patch.object(cloud.urllib.request,'urlopen',side_effect=AssertionError('Network forbidden')):
   r=self.command('cloud/plan')
  self.assertTrue((self.root/r['download'].removeprefix('/studio-file/')).is_file())

if __name__=='__main__':unittest.main()
