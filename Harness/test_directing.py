import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import directing, studio_api as api, studio_store as store

class DirectorTests(unittest.TestCase):
 def setUp(self):
  (store.ROOT/"Cache").mkdir(exist_ok=True)
 def test_rejects_foreign_and_wrong_role_references(self):
  shot={'duration':5};assets=[{'id':'v','kind':'video'}]
  for ref in [{'asset':'foreign','role':'motion','at':0},{'asset':'v','role':'character','at':0},{'asset':'v','role':'motion','at':float('nan')}]:
   with self.assertRaises(ValueError):directing.validate({'references':[ref]},shot,assets)
 def test_cues_are_bounded_and_ordered(self):
  for start,end in [(2,1),(-1,2),(0,6),(0,float('nan'))]:
   with self.assertRaises(ValueError):directing.validate({'cues':[dict(start=start,end=end,text='beat')]},{'duration':5},[])
  result=directing.validate({'cues':[dict(start=3,end=5,text='end'),dict(start=0,end=2,text='start')]},{'duration':5},[])
  self.assertEqual(result['cues'][0]['text'],'start')
 def test_revision_rejection_and_direction_persistence(self):
  with tempfile.TemporaryDirectory(dir=store.ROOT/"Cache") as t,patch.object(store,'DB',Path(t)/'studio.db'):
   p=store.insert(store.blank('Test'));data=dict(project=p['id'],revision=1,action='put',kind='shots',value={'name':'Shot','duration':5,'direction':{'cues':[dict(start=0,end=1,text='hello')]}})
   saved=api.command(data)['project']
   self.assertEqual(store.get(p['id'])['shots'][0]['direction']['cues'][0]['text'],'hello')
   with self.assertRaises(ValueError):api.command(data)
   self.assertEqual(saved['revision'],2)
 def test_dependency_scan_does_not_read_foreign_graphs(self):
  with tempfile.TemporaryDirectory(dir=store.ROOT/"Cache") as t:
   root=Path(t);(root/'secret.json').write_text('{}')
   p={'id':'p','revision':1,'shots':[],'jobs':[{'id':'j','graph':'secret.json'}]}
   report=directing.dependencies(p,root)
   self.assertTrue(report['warnings']);self.assertEqual(report['node_types'],[])
 def test_dependency_graph_inventory(self):
  with tempfile.TemporaryDirectory(dir=store.ROOT/"Cache") as t:
   root=Path(t);path=root/'Projects/p/graph.json';path.parent.mkdir(parents=True)
   path.write_text(json.dumps({'1':{'class_type':'UNETLoader','inputs':{'unet_name':'base.safetensors'}}}))
   result=directing.dependencies({'id':'p','revision':1,'shots':[],'jobs':[dict(id='j',graph='Projects/p/graph.json')]},root)
   self.assertEqual(result['model_filenames'],['base.safetensors'])
 def test_frame_capture_rejects_invalid_time_and_foreign_asset(self):
  p={'assets':[{'id':'v','kind':'video','duration':1}]}
  for data in [{'asset':'foreign','seconds':0},{'asset':'v','seconds':1},{'asset':'v','seconds':float('nan')}]:
   with self.assertRaises(ValueError):api.extract_frame(p,data)
 def test_shorter_shot_cannot_silently_keep_out_of_range_cues(self):
  with tempfile.TemporaryDirectory(dir=store.ROOT/'Cache') as t,patch.object(store,'DB',Path(t)/'studio.db'):
   p=store.blank('Test');p['shots']=[{'id':'s','name':'Shot','duration':5,'direction':{'cues':[dict(start=3,end=5,text='end')]}}];store.insert(p)
   with self.assertRaises(ValueError):api.command(dict(project=p['id'],revision=1,action='put',kind='shots',id='s',value=dict(name='Shorter',duration=2)))
 def test_camera_motion_validation(self):
  import advanced_studio
  value=dict(name='Set',objects=[],lights=[dict(position=[0,0,4],target=[0,0,0],color='#ffffff',power=100,size=1)],camera=dict(position=[0,-4,3],target=[0,0,0],lens=50),width=640,height=360,motion=dict(preset='orbit',seconds=2))
  self.assertEqual(advanced_studio.scene_valid(value)['motion']['seconds'],2)
  value['motion']['seconds']=float('nan')
  with self.assertRaises(ValueError):advanced_studio.scene_valid(value)

if __name__=='__main__':unittest.main()
