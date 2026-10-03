import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import local_agent as agent,studio_store as store,studio_api as api,production

class AgentTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=store.ROOT/'Cache');root=Path(self.temp.name)
  self.patches=[patch.object(m,'ROOT',root) for m in (agent,store,api,production)]+[patch.object(store,'DB',root/'store.db')]
  for p in self.patches:p.start()
  self.p=store.insert(store.blank('Test'));self.key=self.p['id']
  self.settings=dict(agent.DEFAULT,enabled=True,mode='routine')
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def plan(self):
  return dict(summary='Create and refine a robot',steps=[dict(description='Create robot',action='put',data=dict(kind='elements',value=dict(name='Pip',kind='character',description='Blue robot',references=[]))),dict(description='Refine robot',action='put',data=dict(kind='elements',id='$1',value=dict(name='Pip',kind='character',description='Blue robot with amber eyes',references=[])))])
 def prepare(self,mode='routine'):
  self.settings['mode']=mode;plan=agent.validate(self.plan(),self.p,self.settings)
  state=dict(settings=self.settings,run=dict(id='aabbccddeeff',request='Create robot',status='awaiting_approval',plan=plan,cursor=0,refs={},expected_revision=self.p['revision'],before=self.p,events=[]));agent.save(self.key,state);return state
 def test_rejects_cloud_shell_approval_and_cross_project_override(self):
  for action,data in [('cloud/upload',{}),('shell',{}),('put',{'kind':'assets','value':{'name':'Frame','review':'approved'}}),('put',{'kind':'elements','project':'other','value':{}})]:
   plan=dict(summary='Bad',steps=[dict(description='Do bad thing',action=action,data=data)])
   with self.assertRaises(ValueError):agent.validate(plan,self.p,self.settings)
 def test_budget_and_forward_references_rejected(self):
  plan=self.plan();plan['steps'][0]['data']['id']='$2'
  with self.assertRaises(ValueError):agent.validate(plan,self.p,self.settings)
  plan=dict(summary='Too many',steps=[dict(description='Image',action='stage',data=dict(prompt='Robot'))])
  with self.assertRaises(ValueError):agent.validate(plan,self.p,dict(self.settings,max_generations=0))
 def test_ask_mode_stops_after_each_step(self):
  self.prepare('ask');agent.execute(self.key);state=agent.read(self.key)
  self.assertEqual(state['run']['cursor'],1);self.assertEqual(state['run']['status'],'awaiting_approval');self.assertEqual(store.get(self.key)['elements'][0]['description'],'Blue robot')
  agent.execute(self.key);self.assertEqual(agent.read(self.key)['run']['status'],'complete')
 def test_routine_runs_approved_scope_and_undo_retains_evidence(self):
  self.prepare();agent.execute(self.key);p=store.get(self.key);self.assertEqual(len(p['elements']),1);self.assertEqual(p['elements'][0]['description'],'Blue robot with amber eyes')
  agent.dispatch('undo',{'project':self.key});self.assertEqual(store.get(self.key)['elements'],[]);self.assertEqual(agent.read(self.key)['run']['status'],'undone')
 def test_stale_plan_and_stale_undo_cannot_overwrite_manual_edit(self):
  self.prepare();store.mutate(self.key,self.p['revision'],'manual',lambda d:d.update(title='Changed'))
  with self.assertRaises(ValueError):agent.execute(self.key)
  self.assertEqual(store.get(self.key)['title'],'Changed')
 def test_disabled_agent_cannot_execute_and_settings_cancel_old_plan(self):
  self.prepare();agent.dispatch('settings',dict(project=self.key,settings=dict(self.settings,enabled=False)))
  with self.assertRaises(ValueError):agent.execute(self.key)
  self.assertEqual(store.get(self.key)['elements'],[])
 def test_approval_requires_correct_plan_id(self):
  self.prepare()
  with self.assertRaises(ValueError):agent.dispatch('approve',dict(project=self.key,run='wrong'))
 def test_public_state_does_not_expose_undo_snapshot(self):
  self.prepare();self.assertNotIn('before',agent.public(self.key)['run']);self.assertIn('before',agent.read(self.key)['run'])
 def test_restart_does_not_replay_operations(self):
  state=self.prepare();state['run']['status']='running';agent.save(self.key,state);agent.recover();self.assertEqual(agent.read(self.key)['run']['status'],'failed');self.assertEqual(store.get(self.key)['elements'],[])
 def test_full_mode_executes_validated_plan_without_approval(self):
  self.prepare('full')
  response={'choices':[{'message':{'content':json.dumps(self.plan())}}],'usage':{'total_tokens':100}}
  with patch.object(agent.comfy_service,'stop'),patch.object(agent.local_ai,'state',return_value={'loaded':'normal'}),patch.object(agent.local_ai,'request',return_value=response):
   agent.plan_work(self.key,'Create a robot')
  self.assertEqual(agent.read(self.key)['run']['status'],'complete');self.assertEqual(len(store.get(self.key)['elements']),1)
 def test_pause_stops_before_the_next_step(self):
  self.prepare();original=api.command
  def command(data):
   result=original(data);agent.dispatch('pause',{'project':self.key});return result
  with patch.object(api,'command',side_effect=command):agent.execute(self.key)
  state=agent.read(self.key);self.assertEqual(state['run']['status'],'paused');self.assertEqual(state['run']['cursor'],1)
 def test_references_cannot_cross_projects(self):
  other=store.insert(store.blank('Other'))
  result=api.command(dict(project=other['id'],revision=1,action='put',kind='elements',value=dict(name='Other robot',kind='character',references=[])))
  plan=self.plan();plan['steps'][0]['data']['id']=result['project']['elements'][0]['id']
  with self.assertRaises(ValueError):agent.validate(plan,self.p,self.settings)

if __name__=='__main__':unittest.main()
