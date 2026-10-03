"""One CPU prediction per process: release RAM when the decision completes."""
import json
import os
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tools/laya-sdk'))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(ROOT / 'Cache/huggingface')
import torch
torch.set_num_threads(4)
import laya

QUESTIONS = {'workspace': {'type': 'choice', 'instructions': 'Choose the workspace matching the request.', 'criteria': {
    'A': 'Writing a story, dialogue, characters or episode script',
    'B': 'Creating an image or video generation prompt, shot, camera move or storyboard',
    'C': 'Editing footage, sound, transitions, transcripts or subtitles',
    'D': 'Preparing datasets or training a character LoRA',
    'E': 'Software setup, model servers, troubleshooting or technical configuration'}}}
LABELS = {'A': 'Story development', 'B': 'Visual prompts', 'C': 'Editing and captions', 'D': 'Dataset and LoRA', 'E': 'Technical setup'}

if __name__ == '__main__':
    data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    began = time.time()
    agent = laya.load(str(ROOT / 'Models/decisions/laya'), device='cpu')
    loaded = time.time()
    result = agent.predict(data['text'], QUESTIONS)
    answer = result['answers']['workspace']
    value = {'input': data['text'], 'label': LABELS.get(answer.get('choice'), 'Unknown'), 'answer': answer,
             'inference_seconds': round(time.time() - loaded, 3), 'total_seconds': round(time.time() - began, 3),
             'experimental': True, 'note': 'Advisory only. Confidence is not calibrated for studio tasks. No action was executed.'}
    target = ROOT / 'Studio/decision-result.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temp.replace(target)
    print(json.dumps(value))
