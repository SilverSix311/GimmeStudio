"""Serialize our API graphs into editable ComfyUI canvas workflows."""
def canvas(graph, catalog, title):
    positions={'1':[40,100],'8':[40,470],'2':[440,40],'3':[440,480],
               '4':[440,920],'5':[940,100],'6':[1320,100],'7':[1660,100]}
    labels={'1':'Model','8':'Optional style LoRA','2':'Shot + character direction',
            '3':'Avoid','4':'Storyboard frame size','5':'Render settings',
            '6':'Decode image','7':'Save + preview'}
    nodes=[]; links=[]; indexed={}
    for key, spec in graph.items():
        info=catalog[spec['class_type']]; widgets=[]; inputs=[]
        for name, definition in info['input']['required'].items():
            value=spec['inputs'][name]
            if isinstance(value,list):
                inputs.append({'name':name,'type':definition[0],'link':None})
            else:
                widgets.append(value)
                if len(definition)>1 and isinstance(definition[1],dict) and definition[1].get('control_after_generate'):
                    widgets.append('fixed')
        node={'id':int(key),'type':spec['class_type'],'pos':positions.get(key,[40,100]),
              'size':[380,320] if key in ('2','3') else [300,300],
              'flags':{},'order':len(nodes),'mode':0,'inputs':inputs,
              'outputs':[{'name':n,'type':t,'links':[]} for n,t in zip(info['output_name'],info['output'])],
              'properties':{'Node name for S&R':spec['class_type']},'widgets_values':widgets,
              'title':labels.get(key,spec['class_type'])}
        nodes.append(node);indexed[key]=node
    for key,spec in graph.items():
        for slot,inp in enumerate(indexed[key]['inputs']):
            source,outslot=spec['inputs'][inp['name']]; link_id=len(links)+1
            links.append([link_id,int(source),outslot,int(key),slot,inp['type']])
            inp['link']=link_id;indexed[source]['outputs'][outslot]['links'].append(link_id)
    return {'last_node_id':max(n['id'] for n in nodes),'last_link_id':len(links),
            'nodes':nodes,'links':links,'groups':[],'config':{},
            'extra':{'ds':{'scale':0.65,'offset':[40,80]},'local_story_studio':{'title':title}},'version':0.4}
