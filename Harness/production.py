"""Local production records, caption sidecars, dataset exports and preview edits."""
import hashlib
import json
import math
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
import comfy_service

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'Studio'
GUARD = threading.Lock()
JOB = {'busy': False, 'message': 'Ready', 'error': None}


def output_home(data):
    home = Path(data.get('home', HOME)).resolve()
    if home != HOME.resolve() and not home.is_relative_to((ROOT / 'Projects').resolve()):
        raise ValueError('Finishing output must stay in this studio or its projects')
    return home


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def read(name, default=None):
    p = HOME / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def local_file(value):
    p = (ROOT / str(value)).resolve()
    allowed = [ROOT / n for n in ('Studio', 'Output', 'Input', 'Workflows', 'Projects')]
    if not any(p.is_relative_to(a.resolve()) for a in allowed) or not p.is_file():
        raise ValueError('Choose an existing asset inside this studio workspace')
    return p


def relative(p):
    return p.relative_to(ROOT).as_posix()


def media_info(path):
    import av
    with av.open(str(path)) as c:
        duration = c.duration / 1000000 if c.duration else 0
        return {'duration': duration, 'audio': bool(c.streams.audio), 'video': bool(c.streams.video)}


def cues_valid(cues, duration=None):
    if not isinstance(cues, list):
        raise ValueError('Cues must be an array')
    last = 0
    clean = []
    for c in cues:
        a, b = float(c['start']), float(c['end'])
        text = str(c['text']).strip().replace('\r', '')
        if not math.isfinite(a + b) or a < last or b <= a or not text or '-->' in text:
            raise ValueError('Each cue needs ordered, non-overlapping times and nonempty text')
        if duration is not None and b > duration + .05:
            raise ValueError('A caption extends beyond the selected media')
        clean.append({'start': a, 'end': b, 'text': text, 'speaker': str(c.get('speaker', ''))})
        last = b
    return clean


def stamp(seconds, sep):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'


def save_captions(data):
    home = output_home(data)
    source = local_file(data['source'])
    cues = cues_valid(data['cues'], media_info(source)['duration'])
    key = hashlib.sha256(relative(source).encode()).hexdigest()[:12]
    folder = home / 'captions' / key
    if (folder / 'transcript.json').exists():
        revision = folder / 'revisions' / str(time.time_ns())
        revision.mkdir(parents=True)
        for old in folder.iterdir():
            if old.is_file():
                shutil.copy2(old, revision / old.name)
    record = {'source': relative(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'cues': cues, 'reviewed': data.get('reviewed') is True, 'origin': data.get('origin', 'manual'), 'updated': time.time()}
    write(folder / 'transcript.json', record)
    # Both formats use the same reviewed timeline; do not substitute planned script text.
    for ext, sep in [('srt', ','), ('vtt', '.')]:
        blocks = [f"{i}\n{stamp(c['start'], sep)} --> {stamp(c['end'], sep)}\n{c['text']}" for i, c in enumerate(cues, 1)]
        (folder / ('captions.' + ext)).write_text(('WEBVTT\n\n' if ext == 'vtt' else '') + '\n\n'.join(blocks) + '\n', encoding='utf-8')
    return {'message': 'Transcript and SRT/VTT saved' + ('' if record['reviewed'] else ' as an unreviewed draft'),
            'downloads': [relative(folder / ('captions.' + e)) for e in ('srt', 'vtt')]}


def transcribe(data):
    home = output_home(data)
    from faster_whisper import WhisperModel
    import imageio_ffmpeg
    import numpy as np
    source = local_file(data['source'])
    model = ROOT / 'Models/asr/faster-whisper-base.en'
    if not (model / 'model.bin').exists():
        raise ValueError('Local ASR model is not installed yet')
    engine = WhisperModel(str(model), device='cpu', compute_type='int8', local_files_only=True, cpu_threads=6)
    # Decode with our pinned FFmpeg binary: ComfyUI's PyAV API differs from Whisper's file decoder.
    decoded = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(source),
                              '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1'],
                             capture_output=True, timeout=600, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if decoded.returncode or not decoded.stdout:
        raise ValueError('Could not decode an audio stream for transcription')
    samples = np.frombuffer(decoded.stdout, dtype=np.float32).copy()
    segments, _ = engine.transcribe(samples, language='en', vad_filter=True, condition_on_previous_text=False,
                                    word_timestamps=True, beam_size=5)
    segments = list(segments)
    cues = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in segments if s.text.strip()]
    result = save_captions({'source': relative(source), 'cues': cues, 'reviewed': False, 'origin': 'faster-whisper-base.en', 'home': home})
    key = hashlib.sha256(relative(source).encode()).hexdigest()[:12]
    write(home / 'captions' / key / 'words.json', [
        {'start': w.start, 'end': w.end, 'word': w.word, 'probability': w.probability}
        for s in segments for w in (s.words or [])])
    return {**result, 'message': f'Local transcription complete: {len(cues)} cues. Listen and review before delivery.'}


def add_asset(data):
    from PIL import Image
    source = local_file(data['source'])
    with Image.open(source) as im:
        im.verify()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assets = read('dataset.json', [])
    if any(a['sha256'] == digest for a in assets):
        raise ValueError('This exact image is already in the dataset')
    caption = str(data.get('caption', '')).strip()
    character = data.get('character')
    if character not in ('Maxi', 'Rush', 'Taski') or not caption:
        raise ValueError('Choose a character and provide an image-specific caption')
    target = HOME / 'dataset/assets' / (digest[:16] + source.suffix.lower())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assets.append({'id': digest[:16], 'file': relative(target), 'source': relative(source), 'sha256': digest,
                   'character': character, 'caption': caption, 'review': 'pending', 'split': 'train',
                   'group': str(data.get('group', digest[:16])), 'notes': ''})
    write(HOME / 'dataset.json', assets)
    return {'message': 'Image added for review; it is not approved for training yet'}


def review_asset(data):
    assets = read('dataset.json', [])
    item = next((a for a in assets if a['id'] == data['id']), None)
    if item is None:
        raise ValueError('Unknown asset')
    if data['review'] not in ('pending', 'approved', 'rejected') or data['split'] not in ('train', 'validation'):
        raise ValueError('Invalid review or split')
    caption = str(data.get('caption', item['caption'])).strip()
    if not caption:
        raise ValueError('Caption cannot be empty')
    item.update(review=data['review'], split=data['split'], caption=caption, notes=str(data.get('notes', '')))
    write(HOME / 'dataset.json', assets)
    return {'message': 'Dataset review saved'}


def export_dataset(data):
    who = data['character']
    if who not in ('Maxi', 'Rush', 'Taski'):
        raise ValueError('Unknown character')
    assets = [a for a in read('dataset.json', []) if a['character'] == who and a['review'] == 'approved']
    if not any(a['split'] == 'train' for a in assets) or not any(a['split'] == 'validation' for a in assets):
        raise ValueError('Approve separate training and held-out validation images first')
    groups = {}
    for a in assets:
        if a['group'] in groups and groups[a['group']] != a['split']:
            raise ValueError('Related crops from one source must stay in the same split')
        groups[a['group']] = a['split']
        if hashlib.sha256(local_file(a['file']).read_bytes()).hexdigest() != a['sha256']:
            raise ValueError('An approved source changed; reimport and review it')
    folder = HOME / 'exports' / (who.lower() + '-dataset-' + str(time.time_ns()))
    folder.mkdir(parents=True)
    for a in assets:
        dest = folder / a['split'] / Path(a['file']).name
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(local_file(a['file']), dest)
        dest.with_suffix('.txt').write_text(a['caption'], encoding='utf-8')
    write(folder / 'manifest.json', {'character': who, 'assets': assets, 'trained': False,
                                    'note': 'Quality and coverage must be evaluated before training. Count alone is not readiness.'})
    archive = Path(shutil.make_archive(str(folder), 'zip', folder))
    return {'message': 'Approved dataset exported with separate validation images. No training has run.', 'downloads': [relative(archive)]}


def prepare_training(data):
    exported = export_dataset(data)
    folder = local_file(exported['downloads'][0]).with_suffix('')
    name = folder.name
    destination = ROOT / 'Input' / name
    shutil.copytree(folder / 'train', destination)
    graph = json.loads((ROOT / 'Workflows/production/training.json').read_text(encoding='utf-8'))
    for n in graph['nodes']:
        if n['type'] == 'LoadImageTextDataSetFromFolder':
            n['widgets_values'][0] = name
    # Keep the empty template unchanged. This graph names one immutable reviewed export.
    target = folder / 'training-canvas.json'
    write(target, graph)
    write(ROOT / 'Harness/staged-workflow.json', {'title': data['character'] + ' — reviewed dataset training experiment',
          'stage_id': uuid.uuid4().hex, 'workflow': graph})
    return {'message': 'Approved train split prepared and canvas staged. Validation stays separate. No training was queued.',
            'downloads': exported['downloads'] + [relative(target)]}


def render_edit(data):
    home = output_home(data)
    import imageio_ffmpeg
    edit = data.get('timeline', read('timeline.json'))
    clips = edit.get('clips', [])
    if not 1 <= len(clips) <= 24:
        raise ValueError('Use 1–24 video clips')
    fps = int(edit.get('fps', 24))
    width, height = int(edit.get('width', 1280)), int(edit.get('height', 720))
    if fps not in (24, 25, 30) or (width, height) not in ((608, 352), (1280, 720), (1920, 1080)):
        raise ValueError('Choose 24/25/30 fps and a supported preview resolution')
    overlap = float(edit.get('transition_seconds', .5))
    transition = edit.get('transition', 'fade')
    if transition not in ('fade', 'smoothleft', 'smoothright', 'fadeblack') or not .125 <= overlap <= 1.5:
        raise ValueError('Choose a supported transition lasting 0.125–1.5 seconds')
    args = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-y']
    filters, durations, mapping = [], [], []
    elapsed = 0
    for i, clip in enumerate(clips):
        source = local_file(clip['source'])
        still = source.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
        info = {'duration': 120, 'audio': False, 'video': True} if still else media_info(source)
        start, end = float(clip.get('in', 0)), float(clip.get('out', 5 if still else info['duration']))
        if not math.isfinite(start + end) or start < 0 or end > info['duration'] + .05 or end - start <= 2 * overlap or not info['video']:
            raise ValueError('Each video trim must exist and leave room for both transition handles')
        d = end - start
        args += (['-loop', '1', '-t', str(end)] if still else []) + ['-i', str(source)]
        brightness, saturation = float(clip.get('brightness', 0)), float(clip.get('saturation', 1))
        volume = float(clip.get('volume', 1))
        if not -.5 <= brightness <= .5 or not 0 <= saturation <= 2 or not 0 <= volume <= 2:
            raise ValueError('Invalid clip color or volume adjustment')
        filters.append(f'[{i}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},settb=AVTB,format=yuv420p,eq=brightness={brightness}:saturation={saturation}[v{i}]')
        if info['audio']:
            filters.append(f'[{i}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={volume}[a{i}]')
        else:
            filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={d}[a{i}]')
        mapping.append({'source': relative(source), 'source_in': start, 'source_out': end, 'timeline_start': elapsed})
        durations.append(d)
        elapsed += d - (overlap if i < len(clips) - 1 else 0)
    v, a, total = 'v0', 'a0', durations[0]
    for i in range(1, len(clips)):
        filters.append(f'[{v}][v{i}]xfade=transition={transition}:duration={overlap}:offset={total-overlap}[vx{i}]')
        filters.append(f'[{a}][a{i}]acrossfade=d={overlap}:c1=tri:c2=tri[ax{i}]')
        v, a = f'vx{i}', f'ax{i}'
        total += durations[i] - overlap
    tracks = edit.get('audio', [])
    if not isinstance(tracks, list) or len(tracks) > 8:
        raise ValueError('Use up to eight audio layers')
    for n, track in enumerate(tracks):
        source = local_file(track['source'])
        info = media_info(source)
        start, end = float(track.get('in', 0)), float(track.get('out', info['duration']))
        offset, volume = float(track.get('at', 0)), float(track.get('volume', .25))
        if not info['audio'] or not math.isfinite(start+end+offset+volume) or not 0 <= start < end <= info['duration']+.05 or not 0 <= offset < total or not 0 <= volume <= 2:
            raise ValueError('Invalid soundtrack trim, position or volume')
        index = len(clips)+n
        args += ['-i', str(source)]
        duration = min(end-start, total-offset)
        fade = min(.5, duration/2)
        filters.append(f'[{index}:a]atrim=start={start}:end={start+duration},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={volume},afade=t=in:d={fade},afade=t=out:st={duration-fade}:d={fade},adelay={round(offset*1000)}:all=1,apad,atrim=duration={total}[music{n}]')
        if track.get('duck') is True:
            filters.append(f'[{a}]asplit=2[main{n}][side{n}]')
            filters.append(f'[music{n}][side{n}]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[duck{n}]')
            filters.append(f'[main{n}][duck{n}]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:latency=1[mix{n}]')
        else:
            filters.append(f'[{a}][music{n}]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:latency=1[mix{n}]')
        a = f'mix{n}'
    folder = home / 'edits' / str(time.time_ns())
    folder.mkdir(parents=True)
    target = folder / 'preview.mp4'
    args += ['-filter_complex_threads', '1', '-filter_complex', ';'.join(filters), '-map', f'[{v}]', '-map', f'[{a}]',
             '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(target)]
    write(folder / 'timeline.json', {**edit, 'mapping': mapping, 'expected_duration': total, 'preview_only': True})
    result = subprocess.run(args, capture_output=True, text=True, timeout=1800, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    (folder / 'ffmpeg.log').write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise ValueError('Preview render failed: ' + result.stderr[-1500:])
    actual = media_info(target)
    if abs(actual['duration'] - total) > .15:
        raise ValueError('Rendered duration differs from the saved timeline')
    write(folder / 'validation.json', actual)
    write(home / 'timeline.json', edit)
    return {'message': f'Preview rendered locally: {actual["duration"]:.2f}s, video transition and audio crossfade. Transcribe this final edit for aligned subtitles.',
            'downloads': [relative(target), relative(folder / 'timeline.json')]}


def stage(data):
    registry = read('workflows.json', [])
    item = next((w for w in registry if w['id'] == data['id']), None)
    if not item:
        raise ValueError('Unknown workflow')
    graph = json.loads(local_file(item['file']).read_text(encoding='utf-8'))
    write(ROOT / 'Harness/staged-workflow.json', {'title': item['name'], 'stage_id': uuid.uuid4().hex, 'workflow': graph})
    return {'message': 'Staged in ComfyUI. Click Load studio shot, or enable Follow new studio workflows. Nothing was queued.'}


def save_profile(data):
    profile = data['profile']
    if not isinstance(profile, dict) or not profile.get('name') or not isinstance(profile.get('editing'), dict):
        raise ValueError('Profile needs a name and editing settings')
    write(HOME / 'editor-profile.json', profile)
    return {'message': 'Editor profile saved'}


def state():
    media = []
    for base in (ROOT / 'Workflows/krea-h3-lab', HOME / 'edits', ROOT / 'Output/VNCCS'):
        if base.exists():
            media += [relative(p) for p in base.rglob('*') if p.suffix.lower() in ('.png', '.jpg', '.webp', '.mp4', '.wav', '.mp3')][:100]
    captions = []
    for p in (HOME / 'captions').glob('*/transcript.json'):
        record = json.loads(p.read_text(encoding='utf-8'))
        record['downloads'] = [relative(p.parent / ('captions.' + e)) for e in ('srt', 'vtt')]
        captions.append(record)
    return {'comfy': comfy_service.status(), 'job': dict(JOB), 'profile': read('editor-profile.json', {}), 'characters': read('characters.json', []),
            'research': read('research.json', []), 'workflows': read('workflows.json', []), 'assets': read('dataset.json', []),
            'timeline': read('timeline.json', {}), 'captions': captions, 'media': sorted(set(media)),
            'asr_ready': (ROOT / 'Models/asr/faster-whisper-base.en/model.bin').exists()}


ACTIONS = {'comfy-stop': comfy_service.stop, 'comfy-start': comfy_service.start,
           'stage': stage, 'profile': save_profile, 'captions': save_captions, 'transcribe': transcribe,
           'asset': add_asset, 'review': review_asset, 'dataset-export': export_dataset, 'prepare-training': prepare_training,
           'render-edit': render_edit}


def dispatch(action, data):
    if action not in ACTIONS:
        raise ValueError('Unknown production action')
    if not GUARD.acquire(False):
        raise ValueError('Another production operation is running')
    JOB.update(busy=True, error=None, downloads=[], message='Working: ' + action)

    def run():
        try:
            JOB.update(ACTIONS[action](data))
        except Exception as e:
            JOB.update(error=str(e), message='Needs attention')
        finally:
            JOB['busy'] = False
            GUARD.release()
    threading.Thread(target=run, daemon=True).start()
    return {'ok': True}
