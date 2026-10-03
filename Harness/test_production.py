import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import production as p
from PIL import Image


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=p.ROOT / 'Cache')
        self.root = Path(self.temp.name)
        self.home = self.root / 'Studio'
        self.home.mkdir()
        self.patches = [patch.object(p, 'ROOT', self.root), patch.object(p, 'HOME', self.home)]
        for x in self.patches:
            x.start()

    def tearDown(self):
        for x in reversed(self.patches):
            x.stop()
        self.temp.cleanup()

    def fixture(self, name, color):
        f = self.home / name
        Image.new('RGB', (32, 32), color).save(f)
        return 'Studio/' + name

    def test_path_scope(self):
        with self.assertRaises(ValueError):
            p.local_file('../outside.txt')

    def test_caption_validation(self):
        for cues in ([{'start': 1, 'end': 0, 'text': 'x'}], [{'start': 0, 'end': 1, 'text': ''}],
                     [{'start': 0, 'end': 2, 'text': 'a'}, {'start': 1, 'end': 3, 'text': 'b'}],
                     [{'start': 0, 'end': float('nan'), 'text': 'x'}]):
            with self.assertRaises(ValueError):
                p.cues_valid(cues)
        self.assertEqual(p.cues_valid([]), [])
        self.assertEqual(p.stamp(3661.234, ','), '01:01:01,234')

    def test_subtitle_sidecars(self):
        f = self.fixture('source.png', 'blue')
        with patch.object(p, 'media_info', return_value={'duration': 5}):
            out = p.save_captions({'source': f, 'cues': [{'start': .5, 'end': 2.25, 'text': 'Try again, Maxi.'}], 'reviewed': True})
        srt = (self.root / out['downloads'][0]).read_text()
        vtt = (self.root / out['downloads'][1]).read_text()
        self.assertIn('00:00:00,500 --> 00:00:02,250', srt)
        self.assertTrue(vtt.startswith('WEBVTT\n\n'))
        self.assertIn('00:00:00.500 --> 00:00:02.250', vtt)
        with patch.object(p, 'media_info', return_value={'duration': 5}):
            p.save_captions({'source': f, 'cues': [], 'reviewed': False})
        self.assertEqual(len(list((self.home / 'captions').glob('*/revisions/*/transcript.json'))), 1)

    def test_dataset_review_and_split(self):
        a = self.fixture('front.png', 'red')
        b = self.fixture('profile.png', 'blue')
        p.add_asset({'source': a, 'character': 'Maxi', 'caption': 'maxi_mt, front', 'group': 'front-session'})
        with self.assertRaises(ValueError):
            p.add_asset({'source': a, 'character': 'Maxi', 'caption': 'duplicate'})
        p.add_asset({'source': b, 'character': 'Maxi', 'caption': 'maxi_mt, profile', 'group': 'profile-session'})
        with self.assertRaises(ValueError):
            p.export_dataset({'character': 'Maxi'})
        assets = p.read('dataset.json')
        for item, split in zip(assets, ['train', 'validation']):
            p.review_asset({'id': item['id'], 'review': 'approved', 'split': split})
        out = p.export_dataset({'character': 'Maxi'})
        with zipfile.ZipFile(self.root / out['downloads'][0]) as z:
            names = z.namelist()
            self.assertEqual(len([n for n in names if n.endswith('.png')]), 2)
            self.assertTrue(any(n.startswith('validation/') and n.endswith('.txt') for n in names))
        template = self.root / 'Workflows/production/training.json'
        p.write(template, {'nodes': [{'type': 'LoadImageTextDataSetFromFolder', 'widgets_values': ['studio-training']}]})
        prepared = p.prepare_training({'character': 'Maxi'})
        staged = json.loads((self.root / 'Harness/staged-workflow.json').read_text())
        train_name = staged['workflow']['nodes'][0]['widgets_values'][0]
        self.assertEqual(len(list((self.root / 'Input' / train_name).glob('*.png'))), 1)
        self.assertFalse((self.root / 'Input' / train_name / 'validation').exists())
        self.assertEqual(len(prepared['downloads']), 2)
        assets = p.read('dataset.json')
        assets[1]['group'] = assets[0]['group']
        p.write(self.home / 'dataset.json', assets)
        with self.assertRaises(ValueError):
            p.export_dataset({'character': 'Maxi'})


if __name__ == '__main__':
    unittest.main()
