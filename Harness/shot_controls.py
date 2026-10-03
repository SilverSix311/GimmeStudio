"""Native-canvas and API graph edits for explicit, ordered shot LoRA stacks."""
import math
from pathlib import Path


def validate_stack(value):
    if not isinstance(value, list) or len(value) > 8:
        raise ValueError('Use at most eight LoRAs')
    result = []
    for entry in value:
        if not isinstance(entry, dict):
            raise ValueError('Invalid LoRA entry')
        name = entry.get('name', '')
        family = entry.get('family')
        strength = float(entry.get('strength', 1))
        if not isinstance(name, str) or not name or '\\' in name or ':' in name or '..' in Path(name).parts or name.startswith('/'):
            raise ValueError('Choose a relative LoRA filename from the library')
        if family not in ('krea2', 'minimax-h3', 'anima') or not math.isfinite(strength) or not -2 <= strength <= 2:
            raise ValueError('Choose a LoRA family and strength from -2 to 2')
        result.append(dict(name=name, family=family, strength=strength))
    return result


def inventory(root):
    rows = []
    seen = set()
    for base in (root / 'Models/loras', root / 'Models/Shared-SFW/loras'):
        if not base.exists():
            continue
        for file in sorted(base.rglob('*.safetensors')):
            name = file.relative_to(base).as_posix()
            if name in seen:
                continue
            seen.add(name)
            rows.append(dict(name=name, shared='Shared-SFW' in base.parts, bytes=file.stat().st_size))
    return rows


def node(canvas, key):
    return next(n for n in canvas['nodes'] if str(n['id']) == str(key))


def add_node(graph, canvas, kind, inputs, widgets, ports, outputs, title):
    key = max(int(k) for k in graph) + 1
    graph[str(key)] = dict(class_type=kind, inputs=inputs, _meta=dict(title=title))
    canvas['nodes'].append(dict(id=key, type=kind, title=title, pos=[400, 800 + (key % 8)*190],
        size=[340, 150], flags={}, order=len(canvas['nodes']), mode=0,
        inputs=[dict(name=name, type=typ, link=None) for name,typ in ports],
        outputs=[dict(name=typ, type=typ, links=[]) for typ in outputs],
        properties={'Node name for S&R':kind}, widgets_values=widgets))
    canvas['last_node_id'] = key
    return key


def connect(graph, canvas, source, target, input_name, typ, slot=0):
    target_node = node(canvas, target)
    target_slot = next(i for i,p in enumerate(target_node['inputs']) if p['name'] == input_name)
    port = target_node['inputs'][target_slot]
    old = port.get('link')
    if old is not None:
        link = next(l for l in canvas['links'] if l[0] == old)
        node(canvas, link[1])['outputs'][link[2]]['links'].remove(old)
        canvas['links'].remove(link)
    link_id = max([l[0] for l in canvas['links']] + [canvas.get('last_link_id', 0)]) + 1
    canvas['links'].append([link_id, int(source), slot, int(target), target_slot, typ])
    output = node(canvas, source)['outputs'][slot]
    output['links'] = (output.get('links') or []) + [link_id]
    port['link'] = link_id
    graph[str(target)]['inputs'][input_name] = [str(source), slot]
    canvas['last_link_id'] = link_id


def apply(graph, canvas, mode, stack, root, last_image=None):
    stack = validate_stack(stack)
    expected = 'minimax-h3' if mode == 'h3' else 'anima' if mode == 'anima' else 'krea2'
    available = {r['name'] for r in inventory(root)}
    for entry in stack:
        if entry['family'] != expected:
            raise ValueError('LoRA family does not match this workflow: ' + entry['name'])
        if entry['name'] not in available:
            raise ValueError('LoRA is not installed in this workspace: ' + entry['name'])
        if any(n['inputs'].get('lora_name') == entry['name'] for n in graph.values()):
            raise ValueError('This preset already includes that LoRA: ' + entry['name'])
    source = '2' if mode == 'h3' else '1'
    consumers = [(key,name) for key,n in graph.items() for name,value in n['inputs'].items()
                 if value == [source,0] and name == 'model']
    for entry in stack:
        added = add_node(graph, canvas, 'LoraLoaderModelOnly',
                         dict(lora_name=entry['name'], strength_model=entry['strength']),
                         [entry['name'],entry['strength']], [('model','MODEL')], ['MODEL'],
                         'Shot LoRA / ' + entry['name'])
        connect(graph, canvas, source, added, 'model', 'MODEL')
        source = str(added)
    for target,name in consumers:
        if stack:
            connect(graph, canvas, source, target, name, 'MODEL')
    if last_image:
        if mode != 'h3':
            raise ValueError('Last-frame conditioning requires MiniMax H3')
        added = add_node(graph, canvas, 'LoadImage', dict(image=last_image),
                         [last_image,'image'], [], ['IMAGE','MASK'], 'Last frame / GimmeStudio')
        connect(graph, canvas, added, '7', 'last_frame', 'IMAGE')


def configure(graph, canvas, mode, motion):
    """Do not combine turbo and orbit implicitly."""
    def widgets(key, values, inputs):
        graph[str(key)]['inputs'].update(inputs)
        target = node(canvas, key)
        target['widgets_values'] = values
        target.pop('widgets_values_named', None)
    if mode == 'anima':
        widgets(1, ['anima-turbo-v1.1.safetensors','default'], dict(unet_name='anima-turbo-v1.1.safetensors'))
        widgets(2, ['qwen_3_06b_base.safetensors','stable_diffusion','default'], dict(clip_name='qwen_3_06b_base.safetensors',type='stable_diffusion'))
        node(canvas, 1)['title'] = 'Anima Turbo v1.1'
    if motion == 'orbit':
        if mode != 'h3':
            raise ValueError('Orbit recipe requires MiniMax H3')
        name = 'minimax_h3_flf2v_lora_v1.safetensors'
        widgets(2, [name,1], dict(lora_name=name,strength_model=1))
        node(canvas, 2)['title'] = '360 orbit LoRA / no turbo'
        widgets(11, ['simple',28,1], dict(steps=28))
        port = next(p for p in node(canvas,15)['inputs'] if p['name']=='audio')
        old = port['link']
        canvas['links'] = [l for l in canvas['links'] if l[0] != old]
        node(canvas,14)['outputs'][0]['links'] = []
        port['link'] = None
        graph['15']['inputs'].pop('audio',None)
