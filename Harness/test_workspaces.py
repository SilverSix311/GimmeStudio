import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import workspaces
import local_ai
import production


class WorkspaceTests(unittest.TestCase):
    def test_prepare_does_not_copy_user_data_and_preserves_private_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); private = root / 'Incognito'
            for folder in ('Harness','Docs','Config/defaults/Studio','Studio/chats','Projects/secret','Models','Tools','ComfyUI_windows_portable'):
                (root / folder).mkdir(parents=True)
            (root/'Harness/server.py').write_text("URL='http://127.0.0.1:8190'")
            (root/'Harness/series-bible.json').write_text('{"private":true}')
            (root/'Studio/chats/private.json').write_text('secret')
            (root/'Projects/secret/image.png').write_bytes(b'private')
            (root/'Config/defaults/Studio/ai-models.json').write_text('[]')
            with patch.object(workspaces,'INSTALL',root), patch.object(workspaces,'PRIVATE',private), patch.object(workspaces,'link_directory') as link:
                workspaces.prepare()
                config = private/'Studio/ai-models.json'
                config.write_text('[{"id":"private"}]')
                workspaces.prepare()
                self.assertIn('private',config.read_text())
                self.assertFalse((private/'Projects/secret').exists())
                self.assertFalse((private/'Studio/chats/private.json').exists())
                self.assertFalse((private/'Harness/series-bible.json').exists())
                self.assertIn('8290',(private/'Harness/server.py').read_text())
                link.assert_any_call(root/'Models',private/'Models/Shared-SFW')
                self.assertIn(str(root/'Models').replace('\\','\\\\'),(private/'Studio/shared-model-paths.yaml').read_text())

    def test_asset_paths_cannot_cross_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); private=root/'Incognito'
            (root/'Projects').mkdir(); (private/'Projects').mkdir(parents=True)
            (root/'Projects/public.png').write_bytes(b'sfw')
            (private/'Projects/private.png').write_bytes(b'private')
            with patch.object(production,'ROOT',root):
                with self.assertRaises(ValueError): production.local_file('Incognito/Projects/private.png')
            with patch.object(production,'ROOT',private):
                with self.assertRaises(ValueError): production.local_file('../Projects/public.png')

    def test_other_workspace_worker_blocks_start(self):
        status=dict(comfy={'running':True}, production={'busy':False}, ai={'busy':False},studio_finishing=False,advanced_busy=False)
        with patch.object(workspaces,'request',return_value=status):
            with self.assertRaisesRegex(ValueError,'other workspace'): workspaces.guard_other_workers()

    def test_private_chat_profile_overrides_shared_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);private=root/'Incognito'
            (root/'Studio').mkdir();(private/'Studio').mkdir(parents=True)
            (root/'Studio/ai-models.json').write_text(json.dumps([dict(id='normal',file='Models/llm/shared.gguf'),dict(id='heretic',file='Models/llm/heretic.gguf')]))
            (private/'Studio/ai-models.json').write_text(json.dumps([dict(id='normal',file='Models/llm/private.gguf')]))
            with patch.object(local_ai,'ROOT',private),patch.object(workspaces,'INSTALL',root),patch.object(workspaces,'is_incognito',return_value=True):
                models={m['id']:m for m in local_ai.models()}
                self.assertEqual(models['normal']['file'],'Models/llm/private.gguf')
                self.assertEqual(models['heretic']['file'],'Models/Shared-SFW/llm/heretic.gguf')


if __name__=='__main__': unittest.main()
