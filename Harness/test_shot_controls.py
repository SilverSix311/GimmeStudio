import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import shot_controls as controls
import lora_library


class ShotControlTests(unittest.TestCase):
    def test_invalid_stacks(self):
        for entry in [dict(name='../escape',family='krea2'),dict(name='a',family='wrong'),
                      dict(name='a',family='krea2',strength=float('nan'))]:
            with self.assertRaises(ValueError):controls.validate_stack([entry])

    def test_workspace_settings_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            normal=lora_library.environment(root)
            private=lora_library.environment(root/'Incognito')
            self.assertNotEqual(normal['LORA_MANAGER_SETTINGS_DIR'],private['LORA_MANAGER_SETTINGS_DIR'])
            for folder in (root,root/'Incognito'):
                data=json.loads((folder/'User/lora-manager/settings.json').read_text())
                self.assertEqual(data['sidecar_storage_mode'],'centralized')
                self.assertTrue(Path(data['libraries']['comfyui']['recipes_path']).is_relative_to(folder))

    def test_stack_rewires_both_native_and_api(self):
        graph={'1':{'class_type':'UNETLoader','inputs':{}},'2':{'class_type':'KSampler','inputs':{'model':['1',0]}}}
        canvas={'nodes':[dict(id=1,outputs=[dict(links=[1])],inputs=[]),dict(id=2,inputs=[dict(name='model',link=1)],outputs=[])],
                'links':[[1,1,0,2,0,'MODEL']]}
        stack=[dict(name='test.safetensors',family='krea2',strength=.6)]
        with patch.object(controls,'inventory',return_value=[dict(name='test.safetensors')]):
            controls.apply(graph,canvas,'krea',stack,Path('.'))
        self.assertEqual(graph['2']['inputs']['model'],['3',0])
        self.assertEqual(graph['3']['inputs']['model'],['1',0])
        target_link=canvas['nodes'][1]['inputs'][0]['link']
        self.assertEqual(next(l for l in canvas['links'] if l[0]==target_link)[1],3)
        self.assertEqual(graph['3']['inputs']['strength_model'],.6)
        with self.assertRaises(ValueError):controls.apply(graph,canvas,'h3',stack,Path('.'))


if __name__=='__main__':unittest.main()
