"""Reference-conditioned Qwen edit followed by an exact protected-area composite."""
import base64,io,json,shutil,time,urllib.request
from PIL import Image,ImageFilter
import studio_store as store
import production
ROOT=store.ROOT

def native_canvas(graph,catalog):
 nodes=[];links=[];index={}
 for key,spec in graph.items():
  info=catalog[spec['class_type']];inputs=[];widgets=[]
  definitions={**info['input'].get('required',{}),**info['input'].get('optional',{})}
  for name,definition in definitions.items():
   value=spec['inputs'].get(name)
   primitive=isinstance(definition[0],list) or definition[0] in ('STRING','INT','FLOAT','BOOLEAN','COMBO')
   if not primitive:
    inputs.append(dict(name=name,type=definition[0],link=None))
   elif value is not None:
    widgets.append(value)
    if len(definition)>1 and definition[1].get('control_after_generate'):widgets.append('fixed')
  if spec['class_type']=='LoadImage':widgets.append('image')
  idx=len(nodes)
  n=dict(id=int(key),type=spec['class_type'],pos=[(idx//4)*380,(idx%4)*330],size=[340,270],flags={},order=idx,mode=0,inputs=inputs,outputs=[dict(name=n,type=t,links=[]) for n,t in zip(info['output_name'],info['output'])],properties={'Node name for S&R':spec['class_type']},widgets_values=widgets,title=spec.get('_meta',{}).get('title',spec['class_type']))
  nodes.append(n);index[key]=n
 for key,spec in graph.items():
  for slot,inp in enumerate(index[key]['inputs']):
   value=spec['inputs'].get(inp['name'])
   if value is None:continue
   source,out=value;lid=len(links)+1;links.append([lid,int(source),out,int(key),slot,inp['type']]);inp['link']=lid;index[source]['outputs'][out]['links'].append(lid)
 return dict(last_node_id=max(n['id'] for n in nodes),last_link_id=len(links),nodes=nodes,links=links,groups=[],config={},extra={'ds':{'scale':.5,'offset':[20,20]}},version=.4)

def stage(p,data):
 import studio_api as api
 with api.STAGE:
  source=api.source_of(p,data['image']);a=api.item(p,'assets',data['image'])
  if a['kind']!='image' or a['width']*a['height']>10000000:raise ValueError('Choose an image under 10 MP')
  prompt=str(data.get('prompt','')).strip();seed=int(data.get('seed',42))
  if not prompt or len(prompt)>10000 or not 0<=seed<2**53:raise ValueError('Enter an edit instruction and valid seed')
  raw=base64.b64decode(data['mask'].split(',')[-1],validate=True)
  if len(raw)>10000000:raise ValueError('Mask is too large')
  mask=Image.open(io.BytesIO(raw)).convert('L')
  if mask.size!=(a['width'],a['height']) or not mask.getbbox():raise ValueError('Paint an edit region on the source image')
  feather=int(data.get('feather',8))
  if not 0<=feather<=64:raise ValueError('Feather must be 0–64 pixels')
  mask=mask.filter(ImageFilter.GaussianBlur(feather))
  key=store.identifier();folder=ROOT/'Input/gimmestudio'/p['id']/key;folder.mkdir(parents=True)
  shutil.copy2(source,folder/('source'+source.suffix));mask.save(folder/'mask.png')
  relative=lambda path:path.relative_to(ROOT/'Input').as_posix()
  def node(kind,**inputs):return dict(class_type=kind,inputs=inputs)
  width=max(256,round(a['width']/16)*16);height=max(256,round(a['height']/16)*16)
  ratio=min(1,(1048576/(width*height))**.5);width=round(width*ratio/16)*16;height=round(height*ratio/16)*16
  g={
   '1':node('UNETLoader',unet_name='qwen_image_edit_2511_fp8mixed.safetensors',weight_dtype='default'),
   '2':node('LoraLoaderModelOnly',model=['1',0],lora_name='Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors',strength_model=1),
   '3':node('ModelSamplingAuraFlow',model=['2',0],shift=3.1),
   '4':node('CFGNorm',model=['3',0],strength=1,pre_cfg=False),
   '5':node('CLIPLoader',clip_name='qwen_2.5_vl_7b_fp8_scaled.safetensors',type='qwen_image',device='default'),
   '6':node('VAELoader',vae_name='qwen_image_vae.safetensors'),
   '7':node('LoadImage',image=relative(folder/('source'+source.suffix))),
   '8':node('ImageScale',image=['7',0],upscale_method='lanczos',width=width,height=height,crop='disabled'),
   '9':node('TextEncodeQwenImageEditPlus',clip=['5',0],prompt=prompt,vae=['6',0],image1=['8',0]),
   '10':node('TextEncodeQwenImageEditPlus',clip=['5',0],prompt='',vae=['6',0],image1=['8',0]),
   '11':node('VAEEncode',pixels=['8',0],vae=['6',0]),
   '12':node('KSampler',model=['4',0],positive=['9',0],negative=['10',0],latent_image=['11',0],seed=seed,steps=4,cfg=1,sampler_name='euler',scheduler='simple',denoise=1),
   '13':node('VAEDecode',samples=['12',0],vae=['6',0]),
   '14':node('ImageScale',image=['13',0],upscale_method='lanczos',width=a['width'],height=a['height'],crop='disabled'),
   '15':node('LoadImage',image=relative(folder/'mask.png')),
   '16':node('ImageToMask',image=['15',0],channel='red'),
   '17':node('ImageCompositeMasked',destination=['7',0],source=['14',0],mask=['16',0],x=0,y=0,resize_source=False),
   '18':node('SaveImage',images=['17',0],filename_prefix=f'gimmestudio/{p["id"]}/{key}/masked-edit')}
  with urllib.request.urlopen('http://127.0.0.1:8188/object_info',timeout=20) as response:catalog=json.load(response)
  canvas=native_canvas(g,catalog);canvas['extra']['gimmestudio']=dict(project=p['id'],job=key)
  home=ROOT/'Projects'/p['id']/'workflows'/key
  production.write(home/'canvas.json',canvas);production.write(home/'prompt.json',g)
  job=dict(id=key,type='masked-edit',status='staged',created=time.time(),reference=a['id'],prompt=prompt,seed=seed,mask=production.relative(folder/'mask.png'),canvas=production.relative(home/'canvas.json'),graph=production.relative(home/'prompt.json'))
  updated=store.mutate(p['id'],data['revision'],'stage-masked-edit',lambda doc:doc['jobs'].append(job))
  production.write(ROOT/'Harness/staged-workflow.json',dict(title=p['title']+' / masked edit',stage_id=key,workflow=canvas))
  return dict(project=updated,message='Qwen edit staged. Load studio shot in ComfyUI, inspect the mask composite, then Run.')
