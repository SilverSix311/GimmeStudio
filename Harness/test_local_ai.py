import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import local_ai

class LocalAITest(unittest.TestCase):
    def test_chat_path_stays_in_project(self):
        for key in ('../outside', 'ABC', '', 'a' * 13):
            with self.assertRaises(ValueError):
                local_ai.chat_path(key)

    def test_model_load_requires_comfy_shutdown(self):
        with patch('workspaces.guard_other_workers'), patch.object(local_ai, 'models', return_value=[{'id':'test','ready':True}]), patch.object(local_ai.comfy_service, 'status', return_value={'running':True}), patch.object(local_ai, 'stop') as stop:
            with self.assertRaisesRegex(ValueError, 'Shut down'):
                local_ai.start({'model':'test'})
            stop.assert_not_called()

    def test_chat_requires_owned_server(self):
        with patch.object(local_ai, 'owned_process', return_value=None), patch.object(local_ai, 'request') as request:
            with self.assertRaisesRegex(ValueError, 'portable model'):
                local_ai.chat({'prompt':'test'})
            request.assert_not_called()

    def test_failed_generation_is_saved_without_fabricated_reply(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(local_ai, 'HOME', Path(folder)), patch.object(local_ai, 'owned_process', return_value=object()), patch.object(local_ai, 'request', side_effect=[{'data':[{'id':'test'}]}, RuntimeError('inference failed')]):
            with self.assertRaisesRegex(RuntimeError, 'inference failed'):
                local_ai.chat({'prompt':'hello'})
            record = local_ai.read_chat(local_ai.JOB['chat'])
            self.assertEqual(len(record['messages']), 1)
            self.assertEqual(record['messages'][0]['error'], 'inference failed')

if __name__ == '__main__':
    unittest.main()
