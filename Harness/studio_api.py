"""Local studio command surface. Every edit is revisioned and project scoped."""
import base64
import hashlib
import json
import math
import re
import shutil
import threading
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
import production
import studio_store as store
import shot_controls
import directing

ROOT = store.ROOT
WORK = threading.Lock()
STAGE = threading.Lock()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def item(p, kind, key):
    found = next((a for a in p[kind] if a['id'] == key and not a.get('deleted')), None)
    if found is None:
        raise ValueError('Unknown ' + kind + ' item in this project')
    return found


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def asset_record(p, source, name=None, provenance=None):
    source = production.local_file(production.relative(source))
    suffix = source.suffix.lower()
    if suffix not in ('.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm', '.mov', '.wav', '.mp3', '.flac', '.ogg'):
        raise ValueError('Use an image, video or audio file')
    kind = 'image' if suffix in ('.png', '.jpg', '.jpeg', '.webp') else 'audio' if suffix in ('.wav', '.mp3', '.flac', '.ogg') else 'video'
    if kind == 'image':
        from PIL import Image
        with Image.open(source) as im:
            width, height = im.size
            im.verify()
        info = dict(width=width, height=height)
    else:
        info = production.media_info(source)
        if not info['duration'] or (kind == 'video' and not info['video']):
            raise ValueError('Media has no usable duration or video stream')
    sha = digest(source)
    dest = ROOT / 'Projects' / p['id'] / 'assets' / (sha + suffix)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(source, dest)
    return dict(id=store.identifier(), name=name or source.name, kind=kind, file=production.relative(dest),
                sha256=sha, review='pending', notes='', folder='', caption='', split='train', group=sha,
                element='', created=time.time(), provenance=provenance or {}, **info)


def source_of(p, key):
    return production.local_file(item(p, 'assets', key)['file'])


def status():
    return dict(projects=store.listing(), workflows=production.read('workflows.json', []),
                research=production.read('research.json', []), capabilities=production.read('implementation-status.json', {}), mode='local', api='/api/studio/command',
                operations=['create', 'project', 'put', 'delete', 'restore', 'import', 'upload', 'timeline',
                            'stage', 'collect', 'extract-frame', 'render', 'transcribe', 'captions', 'dataset', 'training', 'export', 'import-package', 'proposal', 'board', 'workflow', 'stage-recipe', 'masked-edit', 'advanced/scene-save', 'advanced/blender-render', 'advanced/blender-rerender', 'advanced/blender-open', 'advanced/blender-launch', 'advanced/voice-save', 'advanced/speak', 'advanced/lipsync', 'cloud/plan', 'cloud/configure', 'cloud/forget', 'cloud/upload'])


def migrate_assets():
    """Bring previous episode boards and local character studies into their original project."""
    for summary in store.listing():
        p = store.get(summary['id'])
        if not p.get('legacy') or p.get('legacy_assets_migrated'):
            continue
        legacy = read_json(ROOT / 'Projects' / p['id'] / 'episode.json')
        assets, selected = [], {}
        for shotname, record in legacy.get('renders', {}).items():
            source = ROOT / 'Projects' / p['id'] / record['file']
            if source.is_file():
                a = asset_record(p, source, shotname+' · original storyboard', dict(legacy=record))
                assets.append(a)
                selected[shotname] = a['id']
        known = [
            ('Input/maxi-reference/higgsfield-lineup.png', 'Original Higgsfield character lineup'),
            ('Workflows/maxi-comparison/reference.png', 'Maxi · original comparison reference'),
            ('Workflows/maxi-comparison/reference-55-hi.png', 'Maxi · Krea reference-guided study'),
            ('Workflows/maxi-comparison/text-hi.png', 'Maxi · Krea text-only study'),
            ('Workflows/krea-h3-lab/maxi-krea-start.png', 'Maxi · Krea beach keyframe'),
            ('Workflows/krea-h3-lab/maxi-h3.mp4', 'Maxi · H3 motion study'),
        ]
        reference = None
        for file, name in known:
            if (ROOT / file).is_file():
                a = asset_record(p, ROOT / file, name, dict(legacy_source=file))
                assets.append(a)
                if file.endswith('/reference.png'):
                    reference = a['id']
        def update(doc):
            doc['assets'].extend(assets)
            doc['canon'] = legacy.get('series_rules', [])
            for shot in doc['shots']:
                if shot['name'] in selected:
                    shot['selected'] = selected[shot['name']]
            for element in doc['elements']:
                if element['name']=='Maxi' and reference and not element.get('references'):
                    element['references']=[reference]
            doc['legacy_assets_migrated']=True
        store.mutate(p['id'],None,'migrate-existing-assets',update)


def clean_record(p, kind, value):
    fields = {
        'elements': ('name', 'kind', 'description', 'pronouns', 'trigger', 'notes', 'references'),
        'scenes': ('name', 'description', 'lighting', 'palette', 'notes', 'elements'),
        'shots': ('name', 'prompt', 'camera', 'dialogue', 'duration', 'seed', 'scene', 'elements', 'selected', 'notes',
                  'framing', 'lens', 'aperture', 'movement', 'lighting', 'palette', 'loras', 'first_frame', 'last_frame', 'direction'),
        'assets': ('name', 'review', 'notes', 'folder', 'caption', 'split', 'group', 'element'),
    }
    if kind not in fields:
        raise ValueError('Unknown editor collection')
    result = {k:value[k] for k in fields[kind] if k in value}
    for key, val in result.items():
        if key not in ('references', 'elements', 'duration', 'seed', 'loras', 'direction') and (not isinstance(val, str) or len(val) > 20000):
            raise ValueError('Invalid ' + key)
    if not str(result.get('name', '')).strip():
        raise ValueError('Give this item a name')
    if kind == 'elements' and result.get('kind') not in ('character', 'location', 'object'):
        raise ValueError('Choose character, location or object')
    for field, collection in [('references', 'assets'), ('elements', 'elements')]:
        if field in result:
            if not isinstance(result[field], list) or len(result[field]) > 50:
                raise ValueError('Too many references')
            for key in result[field]:
                target = item(p, collection, key)
                if field == 'references' and target['kind'] != 'image':
                    raise ValueError('Element references must be images')
    if kind == 'shots':
        if 'loras' in result:
            result['loras'] = shot_controls.validate_stack(result['loras'])
        for field in ('first_frame', 'last_frame'):
            if result.get(field) and item(p, 'assets', result[field])['kind'] != 'image':
                raise ValueError('Keyframes must be project images')
        result['duration'] = float(result.get('duration', 5))
        result['seed'] = int(result.get('seed', 4102026))
        if not math.isfinite(result['duration']) or not 1 <= result['duration'] <= 120 or not 0 <= result['seed'] < 2**53:
            raise ValueError('Invalid duration or seed')
        if 'direction' in result:
            result['direction'] = directing.validate(result['direction'], result, p['assets'])
        for field, collection in [('scene', 'scenes'), ('selected', 'assets')]:
            if result.get(field):
                item(p, collection, result[field])
    if kind == 'assets':
        if result.get('review', 'pending') not in ('pending', 'approved', 'rejected') or result.get('split', 'train') not in ('train', 'validation'):
            raise ValueError('Invalid review or dataset split')
        if result.get('element'):
            item(p, 'elements', result['element'])
    return result


def stage(p, data):
    """Customize proven templates, retaining native canvas layouts and execution graph."""
    if not STAGE.acquire(False):
        raise ValueError('Another workflow is being staged')
    try:
        mode = data.get('mode', 'krea')
        if mode not in ('krea', 'reference', 'h3', 'anima'):
            raise ValueError('Unknown generation workflow')
        shot = item(p, 'shots', data['shot']) if data.get('shot') else None
        element = item(p, 'elements', data['element']) if data.get('element') else None
        text = str(data.get('prompt') or (shot or {}).get('prompt') or (element or {}).get('description') or '').strip()
        if not text:
            raise ValueError('Write a design or shot prompt first')
        parts = [p.get('style', ''), text]
        if element:
            parts += [element.get('description', '')]
        if shot:
            parts += [item(p, 'elements', e).get('description', '') for e in shot.get('elements', [])]
            if shot.get('scene'):
                scene = item(p, 'scenes', shot['scene'])
                parts += [scene.get(k, '') for k in ('description', 'lighting', 'palette')]
            parts += [shot.get('camera', ''), shot.get('dialogue', '')]
            parts += [key.title()+': '+shot[key] for key in ('framing','lens','aperture','movement','lighting','palette') if shot.get(key)]
        text = '\n'.join(filter(None, parts))
        seed = int(data.get('seed', (shot or {}).get('seed', 4102026)))
        if not 0 <= seed < 2**53:
            raise ValueError('Seed is out of range')
        motion = data.get('motion_recipe', 'turbo')
        if motion not in ('turbo', 'orbit'):
            raise ValueError('Unknown motion recipe')
        base = ROOT / ('Workflows/maxi-comparison/reference-55-hi' if mode == 'reference' else 'Workflows/krea-h3-lab/' + ('krea' if mode == 'anima' else mode))
        graph, canvas = read_json(base.with_suffix('.api.json')), read_json(base.with_suffix('.json'))
        shot_controls.configure(graph, canvas, mode, motion)
        changes = {}
        if mode == 'h3':
            width, height = (768,768) if motion == 'orbit' else (608,352)
            changes = {'7':dict(prompt=text, width=width, height=height, length=73 if motion == 'orbit' else 124), '9':dict(noise_seed=seed)}
        else:
            width, height = int(data.get('width', 1200)), int(data.get('height', 2048))
            if mode == 'anima' and (min(width,height) < 512 or max(width,height) > 1536):
                raise ValueError('Anima uses 512–1536 pixels per side; choose square or quick draft')
            if min(width, height) < 256 or width % 8 or height % 8 or width * height > 2500000:
                raise ValueError('Image dimensions must be multiples of 8, at least 256, and at most 2.5 MP')
            changes['4'] = dict(text=text)
            if mode in ('krea', 'anima'):
                changes.update({'6':dict(width=width, height=height), '7':dict(seed=seed)})
            else:
                strength = float(data.get('denoise', .55))
                if not .05 <= strength <= 1:
                    raise ValueError('Denoise must be between 0.05 and 1')
                changes.update({'6':dict(seed=seed, denoise=strength), '11':dict(width=width, height=height)})
        reference = data.get('reference') or (shot or {}).get('first_frame') or ((element or {}).get('references') or [''])[0]
        if mode in ('reference', 'h3'):
            a = item(p, 'assets', reference)
            if a['kind'] != 'image':
                raise ValueError('Choose an image reference')
            source = source_of(p, reference)
            target = ROOT / 'Input/gimmestudio' / p['id'] / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
            changes['6' if mode == 'h3' else '9'] = dict(image=target.relative_to(ROOT / 'Input').as_posix())
            if mode == 'reference':
                changes['10'] = dict(width=a['width'], height=a['height'], x=0, y=0)
        jobid = store.identifier()
        output = '16' if mode == 'h3' else '8' if mode == 'reference' else '9'
        changes[output] = dict(filename_prefix=f'gimmestudio/{p["id"]}/{jobid}/take')
        # Widget order is pinned by the saved native canvases. Control-after-generate is UI-only.
        widget_names = {
            'CLIPTextEncode':['text'], 'EmptyLatentImage':['width','height','batch_size'],
            'KSampler':['seed','control_after_generate','steps','cfg','sampler_name','scheduler','denoise'],
            'RandomNoise':['noise_seed','control_after_generate'], 'LoadImage':['image','upload'],
            'ImageCrop':['width','height','x','y'], 'ImageScale':['upscale_method','width','height','crop'],
            'MiniMaxH3ImageToVideo':['prompt','width','height','length'],
            'SaveImage':['filename_prefix'], 'SaveVideo':['filename_prefix','format','codec','extra']}
        for node in canvas['nodes']:
            updates = changes.get(str(node['id']), {})
            if updates:
                graph[str(node['id'])]['inputs'].update(updates)
                node.pop('widgets_values_named', None)
                names = widget_names[node['type']]
                for key, val in updates.items():
                    node['widgets_values'][names.index(key)] = val
                node['title'] = node['type'] + ' Â· GimmeStudio'
        last_frame = data.get('last_frame', (shot or {}).get('last_frame', ''))
        if motion == 'orbit':
            last_frame = reference
            if 'minimax_h3_flf2v_lora_v1.safetensors' not in {r['name'] for r in shot_controls.inventory(ROOT)}:
                raise ValueError('Install the 360 orbit LoRA before staging this recipe')
        last_image = None
        if last_frame:
            if item(p, 'assets', last_frame)['kind'] != 'image':
                raise ValueError('Last frame must be a project image')
            source = source_of(p, last_frame)
            target = ROOT / 'Input/gimmestudio' / p['id'] / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
            last_image = target.relative_to(ROOT / 'Input').as_posix()
        stack = data.get('loras', (shot or {}).get('loras', []))
        shot_controls.apply(graph, canvas, mode, stack, ROOT, last_image)
        canvas.setdefault('extra', {})['gimmestudio'] = dict(project=p['id'], job=jobid, shot=data.get('shot'), element=data.get('element'))
        folder = ROOT / 'Projects' / p['id'] / 'workflows' / jobid
        production.write(folder / 'canvas.json', canvas)
        production.write(folder / 'prompt.json', graph)
        job = dict(id=jobid, type=mode, status='staged', created=time.time(), shot=data.get('shot'), element=data.get('element'),
                   reference=reference, last_frame=last_frame, motion_recipe=motion, loras=stack, seed=seed, width=width, height=height, prompt=text,
                   canvas=production.relative(folder / 'canvas.json'), graph=production.relative(folder / 'prompt.json'))
        updated = store.mutate(p['id'], data['revision'], 'stage', lambda doc:doc['jobs'].append(job))
        production.write(ROOT / 'Harness/staged-workflow.json', dict(title=p['title'] + ' / ' + mode, stage_id=jobid, workflow=canvas))
        return dict(project=updated, message='Workflow staged. Load studio shot in ComfyUI, inspect the graph, then Run. Orbit and additional LoRA combinations need visual review.')
    finally:
        STAGE.release()


def stage_recipe(p, data):
    if not STAGE.acquire(False):
        raise ValueError('Another workflow is being staged')
    try:
        registry = production.read('workflows.json', []) + p.get('workflows', [])
        recipe = next((w for w in registry if w['id']==data['workflow']), None)
        if recipe is None:
            raise ValueError('Choose a registered workflow')
        graph = read_json(production.local_file(recipe['file']))
        jobid = store.identifier()
        graph.setdefault('extra', {})['gimmestudio'] = dict(project=p['id'], job=jobid)
        folder = ROOT / 'Projects' / p['id'] / 'workflows' / jobid
        production.write(folder / 'canvas.json', graph)
        job = dict(id=jobid, type='workflow', status='staged', created=time.time(), recipe=recipe['id'],
                   canvas=production.relative(folder / 'canvas.json'))
        updated = store.mutate(p['id'], data['revision'], 'stage-recipe', lambda doc:doc['jobs'].append(job))
        production.write(ROOT / 'Harness/staged-workflow.json',dict(stage_id=jobid,title=p['title']+' / '+recipe['name'],workflow=graph))
        return dict(project=updated,message='Project workflow staged. Check its models and settings in the visible canvas before Run.')
    finally:
        STAGE.release()


def collect(p):
    with urllib.request.urlopen('http://127.0.0.1:8188/history?max_items=200', timeout=10) as r:
        history = json.load(r)
    imported, updates = [], []
    known = {a.get('provenance', {}).get('output') for a in p['assets']}
    for promptid, record in history.items():
        prompt = record.get('prompt', [])
        if len(prompt) < 4:
            continue
        canvas = prompt[3].get('extra_pnginfo', {}).get('workflow', {})
        tag = canvas.get('extra', {}).get('gimmestudio', {})
        if tag.get('project') != p['id'] or not any(j['id'] == tag.get('job') for j in p['jobs']):
            continue
        jobid = tag['job']
        success = record.get('status', {}).get('status_str') == 'success'
        job = item(p, 'jobs', jobid)
        state = 'complete' if success else 'failed'
        if job.get('status') != state or job.get('prompt_id') != promptid:
            updates.append((jobid, state, promptid))
        if not success:
            continue
        runfolder = ROOT / 'Projects' / p['id'] / 'workflows' / jobid / promptid
        production.write(runfolder / 'executed.json', prompt[2])
        production.write(runfolder / 'canvas.json', canvas)
        production.write(runfolder / 'history.json', record)
        for nodeid, output in record.get('outputs', {}).items():
            if nodeid == '13' and item(p, 'jobs', jobid)['type'] == 'reference':
                continue  # Reference crop is not a generated take.
            for kind in ('images', 'gifs', 'videos', 'audio'):
                for entry in output.get(kind, []):
                    if entry.get('type') != 'output':
                        continue
                    source = (ROOT / 'Output' / entry.get('subfolder', '') / entry['filename']).resolve()
                    if not source.is_relative_to((ROOT / 'Output').resolve()):
                        raise ValueError('Output escaped workspace')
                    identity = promptid + '/' + production.relative(source)
                    if identity in known:
                        continue
                    owner = next((s['name'] for s in p['shots'] if s['id']==tag.get('shot')), None)
                    owner = owner or next((e['name'] for e in p['elements'] if e['id']==tag.get('element')), p['title'])
                    asset = asset_record(p, source, name=owner+' · '+job['type']+' take '+promptid[:6], provenance=dict(output=identity, job=jobid, shot=tag.get('shot'), element=tag.get('element'), execution=production.relative(runfolder / 'executed.json')))
                    if tag.get('element') and any(e['id']==tag['element'] and not e.get('deleted') for e in p['elements']):
                        asset['element']=tag['element']
                    imported.append(asset)
                    known.add(identity)
    def update(doc):
        # Recheck deduplication inside the transaction after slow media inspection.
        seen = {a.get('provenance', {}).get('output') for a in doc['assets']}
        doc['assets'].extend(a for a in imported if a['provenance']['output'] not in seen)
        for jobid, state, promptid in updates:
            item(doc, 'jobs', jobid).update(status=state, prompt_id=promptid)
    return store.mutate(p['id'], None, 'collect', update) if imported or updates else store.get(p['id'])


def run_background(p, action, data):
    import advanced_studio
    if advanced_studio.LOCK.locked():
        raise ValueError('Wait for the local 3D or media worker')
    if not WORK.acquire(False):
        raise ValueError('Another studio finishing job is running')
    job = dict(id=store.identifier(), type=action, status='running', created=time.time())
    try:
        updated = store.mutate(p['id'], data['revision'], action, lambda doc:doc['jobs'].append(job))
    except Exception:
        WORK.release()
        raise
    def work():
        try:
            home = ROOT / 'Projects' / p['id'] / 'finishing'
            if action == 'render':
                timeline = dict(p['timeline'])
                timeline['clips'] = [dict(c, source=item(p, 'assets', c['asset'])['file']) for c in timeline['clips']]
                timeline['audio'] = [dict(c, source=item(p, 'assets', c['asset'])['file']) for c in timeline.get('audio', [])]
                result = production.render_edit(dict(timeline=timeline, home=home))
                asset = asset_record(p, production.local_file(result['downloads'][0]), 'Timeline render', dict(timeline_revision=p['revision']))
                store.mutate(p['id'], None, 'render-output', lambda doc:doc['assets'].append(asset))
            elif action == 'transcribe':
                asset = item(p, 'assets', data['asset'])
                result = production.transcribe(dict(source=asset['file'], home=home))
                transcript = home / 'captions' / hashlib.sha256(asset['file'].encode()).hexdigest()[:12] / 'transcript.json'
                record = read_json(transcript)
                record.update(id=store.identifier(), asset=asset['id'], downloads=result['downloads'])
                store.mutate(p['id'], None, 'transcript', lambda doc:doc['captions'].append(record))
            else:
                raise ValueError('Unknown background operation')
            store.mutate(p['id'], None, action+'-complete', lambda doc:item(doc, 'jobs', job['id']).update(status='complete', result=result))
        except Exception as e:
            store.mutate(p['id'], None, action+'-failed', lambda doc:item(doc, 'jobs', job['id']).update(status='failed', error=str(e)))
        finally:
            WORK.release()
    threading.Thread(target=work, daemon=True).start()
    return dict(project=updated, message='Local '+action+' started. Progress is saved in Jobs.')


def export(p, dataset=None, training=False):
    training_job = None
    assets = [a for a in p['assets'] if not a.get('deleted')]
    if dataset:
        element = item(p, 'elements', dataset)
        assets = [a for a in assets if a.get('element') == dataset and a['review'] == 'approved' and a['kind'] == 'image']
        if {a.get('split') for a in assets} != {'train', 'validation'} or any(not a.get('caption', '').strip() for a in assets):
            raise ValueError('Approve captioned images in both train and validation splits first')
        groups, hashes = {}, set()
        for a in assets:
            if a['sha256'] in hashes:
                raise ValueError('Remove duplicate image content from the approved dataset')
            hashes.add(a['sha256'])
            if a['group'] in groups and groups[a['group']] != a['split']:
                raise ValueError('Related source images must stay in one dataset split')
            groups[a['group']] = a['split']
    folder = ROOT / 'Projects' / p['id'] / 'exports' / store.identifier()
    folder.mkdir(parents=True)
    manifest = dict(schema='gimmestudio/1', project=p, purpose='dataset' if dataset else 'local-vision-handoff',
                    cloud_submitted=False, native_higgsfield_import=False, assets=[])
    for a in assets:
        source = source_of(p, a['id'])
        if digest(source) != a['sha256']:
            raise ValueError('Asset changed on disk: '+a['name'])
        relative = (a['split'] if dataset else 'assets') + '/' + source.name
        target = folder / relative
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
        if dataset:
            target.with_suffix('.txt').write_text(a['caption'], encoding='utf-8')
        manifest['assets'].append(dict(id=a['id'], file=relative, sha256=a['sha256']))
    if not dataset:
        for job in p['jobs']:
            if job.get('mask'):
                source = production.local_file(job['mask'])
                target = folder / 'workflows' / job['id'] / 'mask.png'
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            if job.get('type') in ('blender-render', 'blender-rerender', 'speak', 'lipsync'):
                source_dir = ROOT / 'Projects' / p['id'] / 'advanced' / job['id']
                for filename in ('input.json', 'result.json', 'scene.blend'):
                    source = source_dir / filename
                    if source.is_file():
                        target = folder / 'advanced' / job['id'] / filename
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
            for field in ('canvas', 'graph'):
                if job.get(field):
                    source = production.local_file(job[field])
                    target = folder / 'workflows' / job['id'] / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            if job.get('canvas'):
                base = production.local_file(job['canvas']).parent
                for source in base.glob('*/*.json'):
                    target = folder / 'workflows' / job['id'] / source.relative_to(base)
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)
        for record in p['captions']:
            for file in record.get('downloads', []):
                source = production.local_file(file)
                target = folder / 'captions' / record['id'] / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        (folder / 'SHOT-PACKET.txt').write_text(p['title']+'\n'+p['brief']+'\n\n'+'\n\n'.join(
            s['name']+'\n'+s.get('prompt','')+'\nCamera: '+s.get('camera','')+'\nDialogue: '+s.get('dialogue','')
            for s in p['shots'] if not s.get('deleted')), encoding='utf-8')
    if not dataset:
        production.write(folder / 'DIRECTION.json', directing.packet(p))
        production.write(folder / 'DEPENDENCIES.json', directing.dependencies(p, ROOT))
    manifest['files'] = [{'file':f.relative_to(folder).as_posix(),'sha256':digest(f)} for f in folder.rglob('*') if f.is_file()]
    production.write(folder / 'manifest.json', manifest)
    if training:
        dest = ROOT / 'Input' / ('gimmestudio-training-' + folder.name)
        shutil.copytree(folder / 'train', dest)
        graph = read_json(ROOT / 'Workflows/production/training.json')
        for node in graph['nodes']:
            if node['type'] == 'LoadImageTextDataSetFromFolder':
                node['widgets_values'][0] = dest.name
        jobid = store.identifier()
        graph.setdefault('extra',{})['gimmestudio'] = dict(project=p['id'],job=jobid,element=dataset)
        production.write(folder / 'training-canvas.json', graph)
        training_job = dict(id=jobid,type='training',status='staged',created=time.time(),element=dataset,
                            canvas=production.relative(folder / 'training-canvas.json'))
        production.write(ROOT / 'Harness/staged-workflow.json', dict(stage_id=jobid, title=element['name']+' / SDXL training experiment', workflow=graph))
    archive = Path(shutil.make_archive(str(folder), 'zip', folder))
    record = dict(id=store.identifier(), file=production.relative(archive), revision=p['revision'], created=time.time(), purpose=manifest['purpose'])
    def save_export(doc):
        doc['exports'].append(record)
        if training_job:
            doc['jobs'].append(training_job)
    updated = store.mutate(p['id'], None, 'export', save_export)
    return dict(project=updated, download='/studio-file/'+record['file'], message='Local package exported.' + (' SDXL training canvas staged; no training has run.' if training else ' No cloud job was submitted.'))


def import_package(data):
    """Read only declared assets and metadata; never execute code or extract ZIP paths."""
    source = production.local_file(data['source'])
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        if len(infos)>20000 or sum(i.file_size for i in infos)>4*1024**3:
            raise ValueError('Package is too large')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('schema')!='gimmestudio/1' or manifest.get('purpose')!='local-vision-handoff':
            raise ValueError('Choose a GimmeStudio VISION package')
        original = manifest['project']
        for collection in ('elements','scenes','shots','assets','captions','jobs'):
            records = original.get(collection, [])
            if not isinstance(records,list) or len(records)>10000:
                raise ValueError('Invalid package collection')
            if any(not isinstance(r,dict) or not re.fullmatch('[a-f0-9]{12}',str(r.get('id',''))) for r in records):
                raise ValueError('Invalid package record ID')
        for node in original.get('board',{}).get('nodes',[]):
            if not re.fullmatch('[a-f0-9-]{12,40}',str(node.get('id',''))) or node.get('kind') not in ('note','assets','elements','scenes','shots'):
                raise ValueError('Invalid board card')
            if any(not isinstance(node.get(axis),(int,float)) or not 0<=node[axis]<=5000 for axis in ('x','y')):
                raise ValueError('Invalid board coordinate')
        p = store.blank(str(original['title'])+' · imported')
        for key in ('brief','style','canon','elements','scenes','shots','timeline','board','sets3d','voices'):
            if key in original:
                p[key] = original[key]
        import advanced_studio
        for scene in p.get('sets3d', []):
            advanced_studio.scene_valid(scene)
        declared = {f['file']:f['sha256'] for f in manifest.get('files', [])}
        for job in original.get('jobs', []):
            name = 'advanced/' + job['id'] + '/scene.blend'
            if job.get('type') in ('blender-render','blender-rerender') and name in declared:
                dest = ROOT / 'Projects' / p['id'] / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as incoming, dest.open('wb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
                if digest(dest) != declared[name]:
                    raise ValueError('Blender scene checksum mismatch')
                p['jobs'].append(dict(id=job['id'], type='blender-render', status='imported', created=time.time(), result=dict(blend=production.relative(dest))))
        records = {a['id']:a for a in original['assets']}
        for entry in manifest['assets']:
            record = records[entry['id']]
            name = Path(record['file']).name
            dest = ROOT / 'Projects' / p['id'] / 'assets' / name
            dest.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(entry['file']) as incoming, dest.open('wb') as outgoing:
                shutil.copyfileobj(incoming,outgoing)
            if digest(dest)!=entry['sha256']:
                raise ValueError('Package checksum mismatch')
            validated = asset_record(p,dest,record['name'],dict(imported_from=original['id'],original=record.get('provenance',{})))
            validated.update({k:record[k] for k in ('id','review','notes','folder','caption','split','group','element') if k in record})
            p['assets'].append(validated)
        for shot in p['shots']:
            if 'direction' in shot:
                shot['direction'] = directing.validate(shot['direction'], shot, p['assets'])
        # Retain speech scripts/performance metadata with the imported media.
        for job in original.get('jobs', []):
            if job.get('type') not in ('speak', 'lipsync'):
                continue
            result = json.loads(json.dumps(job.get('result', {})))
            original_asset = next((a for a in original['assets'] if a['file'] == result.get('file')), None)
            if original_asset:
                result['file'] = item(p, 'assets', original_asset['id'])['file']
            p['jobs'].append(dict(id=job['id'], type=job['type'], status='imported', created=time.time(), result=result))
        for caption in original.get('captions',[]):
            files=[]
            for extension in ('srt','vtt'):
                name='captions/'+caption['id']+'/captions.'+extension
                if name in archive.namelist():
                    dest=ROOT/'Projects'/p['id']/name
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(archive.read(name))
                    files.append(production.relative(dest))
            p['captions'].append(dict(caption,downloads=files))
        for job in original.get('jobs',[]):
            name='workflows/'+job['id']+'/canvas.json'
            if name in archive.namelist():
                graph=json.loads(archive.read(name))
                key=store.identifier()
                dest=ROOT/'Projects'/p['id']/'recipes'/(key+'.json')
                production.write(dest,graph)
                p.setdefault('workflows',[]).append(dict(id=key,name='Imported '+job['type']+' '+job['id'],file=production.relative(dest),status='Imported · rebind references before running'))
    return dict(project=store.insert(p),message='Imported as an independent local project. Original files and project are unchanged.')


def extract_frame(p, data):
    import subprocess
    import imageio_ffmpeg
    asset = item(p, 'assets', data.get('asset'))
    at = data.get('seconds')
    if asset['kind'] != 'video' or isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or not 0 <= at < asset['duration']:
        raise ValueError('Choose a video and a frame time before its end')
    folder = ROOT / 'Projects' / p['id'] / 'frame-captures' / store.identifier()
    folder.mkdir(parents=True)
    target = folder / 'frame.png'
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-ss', str(at), '-i', str(source_of(p, asset['id'])), '-frames:v', '1', str(target)], capture_output=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or not target.is_file():
        raise ValueError('Could not decode that video frame')
    captured = asset_record(p, target, asset['name'] + ' / ' + str(round(at, 3)) + 's',
                            dict(source_asset=asset['id'], source_sha256=asset['sha256'], seconds=at))
    captured['group'] = asset['sha256']  # Related video frames must share a dataset split.
    updated = store.mutate(p['id'], data['revision'], 'extract-frame', lambda doc: doc['assets'].append(captured))
    return dict(project=updated, message='Captured frame saved to Assets for review; no automatic approval.')


def command(data):
    action = data.get('action')
    if action == 'import-package':
        return import_package(data)
    if action == 'create':
        return dict(project=store.insert(store.blank(data.get('title', ''))))
    p = store.get(data.get('project'))
    revision = data.get('revision')
    if not isinstance(revision, int):
        raise ValueError('Provide the current project revision')
    if p['revision'] != revision:
        raise ValueError('Project changed. Reload before saving.')
    if str(action).startswith('cloud/'):
        import cloud_handoff
        return cloud_handoff.dispatch(p,data)
    if action == 'masked-edit':
        import masked_edit
        return masked_edit.stage(p,data)
    if str(action).startswith('advanced/'):
        import advanced_studio
        return advanced_studio.dispatch(p, data)
    if action == 'stage':
        return stage(p, data)
    if action == 'stage-recipe':
        return stage_recipe(p, data)
    if action == 'collect':
        return dict(project=collect(p))
    if action == 'extract-frame':
        return extract_frame(p, data)
    if action in ('render', 'transcribe'):
        return run_background(p, action, data)
    if action in ('export', 'dataset', 'training'):
        if action != 'export' and not data.get('element'):
            raise ValueError('Choose a dataset identity')
        if action == 'training':
            if not STAGE.acquire(False):
                raise ValueError('Another workflow is being staged')
            try:
                return export(p,data['element'],True)
            finally:
                STAGE.release()
        return export(p, data.get('element') if action != 'export' else None)
    def change(doc):
        if action == 'project':
            title = str(data.get('title', '')).strip()
            if not title or len(title) > 160:
                raise ValueError('Project title required (maximum 160 characters)')
            doc.update(title=title, brief=str(data.get('brief', ''))[:20000], style=str(data.get('style', ''))[:20000])
        elif action == 'put':
            kind = data['kind']
            clean = clean_record(doc, kind, data['value'])
            if data.get('id'):
                target = item(doc, kind, data['id'])
                if kind == 'shots' and 'direction' in target and 'direction' not in clean:
                    clean['direction'] = directing.validate(target['direction'], {**target, **clean}, doc['assets'])
                target.update(clean)
            else:
                if kind == 'assets':
                    raise ValueError('Import an asset first')
                doc[kind].append(dict(id=store.identifier(), created=time.time(), **clean))
        elif action == 'proposal':
            proposal = data['value']
            if not isinstance(proposal, dict) or set(proposal)-{'elements','scenes','shots'}:
                raise ValueError('Draft must contain only elements, scenes and shots arrays')
            for kind, records in proposal.items():
                if not isinstance(records, list) or len(records)>30:
                    raise ValueError('Use at most 30 draft items per collection')
                for record in records:
                    clean = clean_record(doc, kind, record)
                    doc[kind].append(dict(id=store.identifier(), created=time.time(), **clean))
        elif action == 'workflow':
            graph = data['value']
            name = str(data.get('name', '')).strip()
            if not name or not isinstance(graph, dict) or not isinstance(graph.get('nodes'), list) or not isinstance(graph.get('links'), list):
                raise ValueError('Import a named editable ComfyUI workflow JSON, not an API prompt')
            if len(graph['nodes'])>500:
                raise ValueError('Workflow has too many nodes')
            key = store.identifier()
            target = ROOT / 'Projects' / p['id'] / 'recipes' / (key+'.json')
            production.write(target,graph)
            doc.setdefault('workflows',[]).append(dict(id=key,name=name,file=production.relative(target),status='Imported · inspect models before running'))
        elif action in ('delete', 'restore'):
            if data['kind'] not in ('elements', 'scenes', 'shots', 'assets'):
                raise ValueError('Unknown collection')
            entry = next((a for a in doc[data['kind']] if a['id'] == data['id']), None)
            if entry is None:
                raise ValueError('Unknown item')
            entry['deleted'] = action == 'delete'
        elif action in ('import', 'upload'):
            if action == 'import':
                source = production.local_file(data['source'])
            else:
                name = Path(str(data['name'])).name
                target = ROOT / 'Projects' / p['id'] / 'imports' / (uuid.uuid4().hex + Path(name).suffix.lower())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base64.b64decode(data['base64'], validate=True))
                source = target
            doc['assets'].append(asset_record(doc, source, data.get('name')))
        elif action == 'timeline':
            timeline = data['value']
            if not isinstance(timeline.get('clips'), list) or len(timeline['clips']) > 24:
                raise ValueError('Use up to 24 clips')
            for clip in timeline['clips']:
                a = item(doc, 'assets', clip['asset'])
                start, end = float(clip['in']), float(clip['out'])
                if a['kind'] not in ('video', 'image') or not math.isfinite(start+end) or not 0 <= start < end <= a.get('duration', 120)+.05:
                    raise ValueError('Invalid clip or trim')
            if len(timeline.get('audio', [])) > 8:
                raise ValueError('Use at most eight audio layers')
            for track in timeline.get('audio', []):
                a = item(doc, 'assets', track['asset'])
                if not a.get('audio') or not 0 <= float(track['in']) < float(track['out']) <= a['duration']+.05:
                    raise ValueError('Invalid soundtrack media or trim')
            doc['timeline'] = timeline
        elif action == 'board':
            board = data['value']
            if not isinstance(board, dict) or len(board.get('nodes', []))>100 or len(board.get('edges', []))>200:
                raise ValueError('Board limit is 100 cards and 200 connections')
            ids = set()
            for node in board.get('nodes', []):
                if not re.fullmatch('[a-f0-9-]{12,40}',str(node.get('id',''))) or node['id'] in ids:
                    raise ValueError('Invalid or duplicate board card ID')
                ids.add(node['id'])
                if node['kind'] not in ('elements','scenes','shots','assets','note'):
                    raise ValueError('Unknown board card type')
                if node['kind']!='note':
                    item(doc,node['kind'],node['reference'])
                for axis in ('x','y'):
                    if not isinstance(node[axis],(int,float)) or not 0<=node[axis]<=5000:
                        raise ValueError('Card coordinates out of bounds')
                node['text'] = str(node.get('text',''))[:10000]
            for edge in board.get('edges', []):
                if edge['from'] not in ids or edge['to'] not in ids or edge['from']==edge['to']:
                    raise ValueError('Connection needs two different cards')
            doc['board'] = board
        elif action == 'captions':
            asset = item(doc, 'assets', data['asset'])
            result = production.save_captions(dict(source=asset['file'], cues=data['cues'], reviewed=data.get('reviewed') is True,
                                                   home=ROOT / 'Projects' / p['id'] / 'finishing'))
            record = dict(id=store.identifier(), asset=asset['id'], cues=data['cues'], reviewed=data.get('reviewed') is True,
                          downloads=result['downloads'], source_sha256=asset['sha256'])
            doc['captions'] = [c for c in doc['captions'] if c['asset'] != asset['id']] + [record]
        else:
            raise ValueError('Unknown studio action')
    updated = store.mutate(p['id'], revision, action, change)
    return dict(project=updated, message='Saved locally')
