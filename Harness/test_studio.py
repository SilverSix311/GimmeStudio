import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import studio_store as store
import studio_api as api
import production


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=store.ROOT / 'Cache')
        self.root = Path(self.temp.name)
        self.patches = [patch.object(store, 'DB', self.root/'studio.db'),
                        patch.object(store, 'ROOT', self.root), patch.object(api, 'ROOT', self.root),
                        patch.object(production, 'ROOT', self.root)]
        for p in self.patches: p.start()
        (self.root/'Input').mkdir()
        self.p = store.insert(store.blank('Production A'))
        self.q = store.insert(store.blank('Production B'))

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def command(self, action, **data):
        result = api.command(dict(project=self.p['id'], revision=self.p['revision'], action=action, **data))
        self.p = result['project']
        return result

    def image(self):
        from PIL import Image
        file = self.root/'Input/test.png'
        Image.new('RGB',(64,64),'red').save(file)
        self.command('import', source='Input/test.png')
        return self.p['assets'][-1]

    def test_projects_isolated_and_edits_persist(self):
        self.command('put', kind='elements', value=dict(name='Iris',kind='character',description='Blue coat',references=[]))
        element = self.p['elements'][0]
        self.command('put', kind='elements', id=element['id'], value=dict(element, description='Green coat'))
        self.assertEqual(store.get(self.p['id'])['elements'][0]['description'],'Green coat')
        self.assertEqual(store.get(self.q['id'])['elements'],[])
        self.assertEqual(len(store.history(self.p['id'])),3)

    def test_edit_shot_preserves_adapter_stack(self):
        stack=[dict(name='character.safetensors',family='krea2',strength=.65)]
        self.command('put',kind='shots',value=dict(name='Opening',loras=stack))
        shot=self.p['shots'][0]
        self.command('put',kind='shots',id=shot['id'],value=dict(name='New opening',prompt='New action'))
        self.assertEqual(self.p['shots'][0]['loras'],stack)

    def test_cross_project_last_frame_rejected(self):
        asset=self.image()
        with self.assertRaises(ValueError):
            api.clean_record(self.q,'shots',dict(name='Other',last_frame=asset['id']))

    def test_stale_revision_cannot_clobber_work(self):
        old = self.p['revision']
        self.command('project',title='Changed',brief='',style='')
        with self.assertRaises(ValueError):
            api.command(dict(project=self.p['id'], revision=old, action='project',title='Lost',brief='',style=''))
        self.assertEqual(store.get(self.p['id'])['title'],'Changed')

    def test_cross_project_reference_rejected(self):
        a=self.image()
        with self.assertRaises(ValueError):
            api.command(dict(project=self.q['id'], revision=self.q['revision'], action='put',kind='elements',value=dict(name='Other',kind='character',references=[a['id']])))

    def test_trash_restore_preserves_identity(self):
        a=self.image()
        self.command('delete',kind='assets',id=a['id'])
        self.assertTrue(self.p['assets'][0]['deleted'])
        self.command('restore',kind='assets',id=a['id'])
        self.assertFalse(self.p['assets'][0]['deleted'])
        self.assertEqual(self.p['assets'][0]['sha256'],a['sha256'])

    def test_invalid_proposal_rolls_back_all_records(self):
        with self.assertRaises(ValueError):
            self.command('proposal', value=dict(elements=[dict(name='Good',kind='character'),dict(name='',kind='invalid')]))
        self.assertEqual(store.get(self.p['id'])['elements'],[])

    def test_export_preserves_media_and_rejects_tampering(self):
        import zipfile
        a=self.image()
        result=self.command('export')
        file=production.local_file(result['download'].removeprefix('/studio-file/'))
        with zipfile.ZipFile(file) as archive:
            manifest=json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['assets'][0]['sha256'],a['sha256'])
            self.assertIn(manifest['assets'][0]['file'],archive.namelist())
        imported=api.command(dict(action='import-package',source=production.relative(file)))['project']
        self.assertNotEqual(imported['id'],self.p['id'])
        self.assertEqual(imported['assets'][0]['sha256'],a['sha256'])
        self.assertIn(imported['id'],imported['assets'][0]['file'])
        production.local_file(a['file']).write_bytes(b'changed')
        with self.assertRaises(ValueError): self.command('export')

    def test_training_prevents_group_leakage(self):
        a=self.image()
        self.command('put',kind='elements',value=dict(name='Iris',kind='character',references=[]))
        element=self.p['elements'][0]['id']
        self.command('put',kind='assets',id=a['id'],value=dict(a,element=element,review='approved',caption='red square',split='train'))
        self.command('import',source='Input/test.png')
        b=self.p['assets'][-1]
        self.command('put',kind='assets',id=b['id'],value=dict(b,element=element,review='approved',caption='same square',split='validation'))
        with self.assertRaises(ValueError): self.command('dataset',element=element)

    def test_interrupted_jobs_remain_visible(self):
        store.mutate(self.p['id'],None,'test',lambda p:p['jobs'].append(dict(id='job',status='running')))
        store.recover_jobs()
        self.assertEqual(store.get(self.p['id'])['jobs'][0]['status'],'interrupted')

    def test_out_of_bounds_trim_rejected(self):
        a=self.image()
        with self.assertRaises(ValueError): self.command('timeline',value=dict(clips=[dict(asset=a['id'],**{'in':0,'out':999})]))

    def test_board_and_workflow_are_project_scoped(self):
        a=self.image()
        self.command('board',value=dict(nodes=[dict(id='123456abcdef',kind='assets',reference=a['id'],x=20,y=30)],edges=[]))
        self.assertEqual(self.p['board']['nodes'][0]['reference'],a['id'])
        with self.assertRaises(ValueError):
            self.command('board',value=dict(nodes=[dict(id='123456abcdef',kind='assets',reference='other-project',x=20,y=30)],edges=[]))
        self.command('workflow',name='Test canvas',value=dict(nodes=[],links=[]))
        recipe=self.p['workflows'][0]
        self.command('stage-recipe',workflow=recipe['id'])
        canvas=json.loads(production.local_file(self.p['jobs'][-1]['canvas']).read_text())
        self.assertEqual(canvas['extra']['gimmestudio']['project'],self.p['id'])

    def test_finishing_outputs_cannot_escape_project(self):
        with self.assertRaises(ValueError):
            production.output_home({'home':str(self.root.parent/'outside')})

    def test_model_staging_updates_native_canvas_and_graph(self):
        original=Path(__file__).resolve().parents[1]
        for mode in ('krea','h3'):
            for ext in ('.json','.api.json'):
                dest=self.root/'Workflows/krea-h3-lab'/(mode+ext)
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original/'Workflows/krea-h3-lab'/(mode+ext),dest)
        a=self.image()
        for mode in ('krea','h3'):
            self.command('stage',mode=mode,prompt='A robot in a garden',seed=123,reference=a['id'],width=1024,height=576)
            j=self.p['jobs'][-1]
            graph=json.loads(production.local_file(j['graph']).read_text())
            canvas=json.loads(production.local_file(j['canvas']).read_text())
            self.assertEqual(canvas['extra']['gimmestudio']['project'],self.p['id'])
            self.assertIn('robot',graph['7' if mode=='h3' else '4']['inputs']['prompt' if mode=='h3' else 'text'])
            self.assertEqual(graph['9' if mode=='h3' else '7']['inputs']['noise_seed' if mode=='h3' else 'seed'],123)


if __name__=='__main__': unittest.main()
