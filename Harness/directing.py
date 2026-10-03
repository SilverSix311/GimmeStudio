"""Validated shot direction and portable dependency reports; no model execution."""
import math
from pathlib import Path


ROLES = {'character': {'image'}, 'environment': {'image'}, 'motion': {'video'},
         'voice': {'audio', 'video'}, 'guide': {'image', 'audio'}}


def validate(value, shot, assets):
    if not isinstance(value, dict) or set(value) - {'cues', 'references', 'checks', 'notes', 'reviewed_asset'}:
        raise ValueError('Direction requires cues, references, checks and notes')
    result = {'cues': [], 'references': [], 'checks': {}, 'notes': value.get('notes', '')}
    if not isinstance(result['notes'], str) or len(result['notes']) > 20000:
        raise ValueError('Direction notes are too long')
    live = {a['id']: a for a in assets if not a.get('deleted')}
    cues, references = value.get('cues', []), value.get('references', [])
    if not isinstance(cues, list) or len(cues) > 100 or not isinstance(references, list) or len(references) > 50:
        raise ValueError('Use at most 100 cues and 50 references')
    duration = float(shot.get('duration', 5))
    for cue in cues:
        if not isinstance(cue, dict):
            raise ValueError('Invalid timed cue')
        start, end = cue.get('start'), cue.get('end')
        if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in (start, end)) or not 0 <= start < end <= duration:
            raise ValueError('Cue times must fit inside the shot')
        text = cue.get('text', '')
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError('Each cue needs 1–4000 characters')
        result['cues'].append(dict(start=start, end=end, text=text.strip()))
    result['cues'].sort(key=lambda c: (c['start'], c['end']))
    for ref in references:
        if not isinstance(ref, dict) or ref.get('role') not in ROLES:
            raise ValueError('Choose a supported reference role')
        asset = live.get(ref.get('asset'))
        if not asset or asset['kind'] not in ROLES[ref['role']]:
            raise ValueError('Reference must be a compatible asset in this project')
        at = ref.get('at', 0)
        if isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or not 0 <= at <= duration:
            raise ValueError('Reference time must fit inside the shot')
        result['references'].append(dict(asset=asset['id'], role=ref['role'], at=at))
    checks = value.get('checks', {})
    allowed = {'identity', 'wardrobe', 'props', 'eyelines', 'motion', 'audio', 'seam'}
    if not isinstance(checks, dict) or set(checks)-allowed or any(v not in ('unchecked', 'pass', 'issue') for v in checks.values()):
        raise ValueError('Invalid continuity checks')
    reviewed = value.get('reviewed_asset', '')
    if reviewed and (reviewed not in live or live[reviewed]['kind'] != 'video'):
        raise ValueError('Reviewed take must be a project video')
    result['reviewed_asset'] = reviewed
    result['checks'] = checks
    return result


def packet(project):
    """Keep roles and timing explicit; these are direction, not executed conditioning."""
    return {'schema': 'gimmestudio-direction/1', 'project': project['id'],
            'revision': project['revision'], 'conditioning_applied': False,
            'shots': [dict(id=s['id'], name=s['name'], duration=s.get('duration', 5),
                           prompt=s.get('prompt', ''), direction=s.get('direction', {}))
                      for s in project['shots'] if not s.get('deleted')]}


def dependencies(project, root):
    """Read saved API graphs only. Never execute or import an untrusted workflow."""
    import json
    models, nodes, warnings = set(), set(), []
    keys = {'ckpt_name', 'unet_name', 'clip_name', 'clip_name1', 'clip_name2', 'vae_name', 'lora_name'}
    for job in project.get('jobs', []):
        if not job.get('graph'):
            continue
        path = (root / job['graph']).resolve()
        if not path.is_relative_to((root / 'Projects' / project['id']).resolve()):
            warnings.append('Skipped graph outside this project: ' + job['id'])
            continue
        try:
            if path.stat().st_size > 10_000_000:
                raise ValueError('Graph exceeds 10 MB')
            graph = json.loads(path.read_text(encoding='utf-8'))
            for node in graph.values():
                if not isinstance(node, dict):
                    continue
                if isinstance(node.get('class_type'), str):
                    nodes.add(node['class_type'])
                for key, name in node.get('inputs', {}).items():
                    if key in keys and isinstance(name, str):
                        models.add(name)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            warnings.append(f"Could not inspect graph {job['id']}: {exc}")
    for shot in project.get('shots', []):
        if not shot.get('deleted'):
            models.update(r['name'] for r in shot.get('loras', []))
    return dict(schema='gimmestudio-dependencies/1', project=project['id'], revision=project['revision'],
                node_types=sorted(nodes), model_filenames=sorted(models), warnings=warnings,
                scope='Saved execution graphs and shot LoRAs; filenames are not content hashes.',
                weights_included=False)
