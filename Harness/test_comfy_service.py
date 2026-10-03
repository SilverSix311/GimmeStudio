import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).parent))
import comfy_service as service


class ComfyServiceTests(unittest.TestCase):
    def test_active_queue_is_not_terminated(self):
        process = MagicMock()
        with patch.object(service, 'owned_process', return_value=process), patch.object(service, 'status', return_value={'busy': True}):
            with self.assertRaisesRegex(ValueError, 'Finish or cancel'):
                service.stop({})
        process.terminate.assert_not_called()

    def test_reused_pid_is_not_terminated(self):
        original, replacement = MagicMock(), MagicMock()
        original.create_time.return_value = 1
        replacement.create_time.return_value = 2
        with patch.object(service, 'owned_process', side_effect=[original, replacement]), patch.object(service, 'status', return_value={'busy': False}):
            with self.assertRaisesRegex(ValueError, 'process changed'):
                service.stop({})
        original.terminate.assert_not_called()
        replacement.terminate.assert_not_called()

    def test_stop_is_idempotent(self):
        with patch.object(service, 'owned_process', return_value=None):
            self.assertIn('already stopped', service.stop({})['message'])


if __name__ == '__main__':
    unittest.main()
