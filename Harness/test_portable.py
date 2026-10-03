import json
import tempfile
import unittest
from pathlib import Path
from initialize_portable import initialize


class PortableTests(unittest.TestCase):
    def test_defaults_preserve_user_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            defaults = root / 'Config/defaults/Studio'
            defaults.mkdir(parents=True)
            (defaults / 'ai-models.json').write_text('[]')
            initialize(root)
            configured = root / 'Studio/ai-models.json'
            configured.write_text('[{"id":"mine"}]')
            (root / 'Projects/precious.txt').write_text('keep')
            initialize(root)
            self.assertEqual(json.loads(configured.read_text()), [{'id': 'mine'}])
            self.assertEqual((root / 'Projects/precious.txt').read_text(), 'keep')

    def test_owned_bridge_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bridge = root / 'Integrations/local_story_studio'
            bridge.mkdir(parents=True)
            (bridge / '__init__.py').write_text('# bridge')
            initialize(root)
            self.assertTrue((root / 'ComfyUI_windows_portable/ComfyUI/custom_nodes/local_story_studio/__init__.py').is_file())


if __name__ == '__main__':
    unittest.main()
