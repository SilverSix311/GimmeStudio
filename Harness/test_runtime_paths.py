import json
import tempfile
import unittest
from pathlib import Path
import runtime_paths as runtime


class RuntimePathsTests(unittest.TestCase):
    def test_platform_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(runtime.path('python', root, 'Windows'), root / 'ComfyUI_windows_portable/python_embeded/python.exe')
            self.assertEqual(runtime.path('python', root, 'Linux'), root / 'Tools/runtime/bin/python')
            self.assertEqual(runtime.path('llama', root, 'Darwin'), root / 'Tools/llama/llama-server')
            self.assertTrue(runtime.path('blender', root, 'Darwin').as_posix().endswith('Contents/MacOS/Blender'))

    def test_config_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'Studio').mkdir()
            (root / 'Studio/runtime.json').write_text(json.dumps({'python': '../outside/python'}))
            with self.assertRaisesRegex(ValueError, 'inside'):
                runtime.path('python', root)

    def test_backend_options_are_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'Studio').mkdir()
            config = root / 'Studio/runtime.json'
            config.write_text('{"backend":"cpu"}')
            self.assertEqual(runtime.comfy_args(root), ['--cpu'])
            config.write_text('{"backend":"mps"}')
            self.assertEqual(runtime.comfy_args(root), [])
            config.write_text('{"backend":"--arbitrary-flag"}')
            with self.assertRaises(ValueError):
                runtime.comfy_args(root)
