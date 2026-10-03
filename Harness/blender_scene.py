"""Executed by the bundled Blender, with validated scene JSON only."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

config=Path(sys.argv[sys.argv.index('--')+1])
data=json.loads(config.read_text(encoding='utf-8'))
folder=config.parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=data['width'];scene.render.resolution_y=data['height']
scene.render.resolution_percentage=100
scene.world.color=(.15,.15,.15)
scene.view_settings.view_transform='AgX'
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))+(1,)
 m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color
 m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.65
 return m
for record in data['objects']:
 kind=record['type']
 if kind=='cube':bpy.ops.mesh.primitive_cube_add(size=1)
 elif kind=='sphere':bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.5)
 elif kind=='cylinder':bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.5,depth=1)
 elif kind=='cone':bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.5,depth=1)
 elif kind=='plane':bpy.ops.mesh.primitive_plane_add(size=1)
 obj=bpy.context.object;obj.name=record['name'];obj.location=record['position'];obj.scale=record['scale']
 obj.rotation_euler=[math.radians(v) for v in record['rotation']]
 obj.data.materials.append(material(record['name'],record['color']))
 if kind!='plane':
  bevel=obj.modifiers.new('Soft edges','BEVEL');bevel.width=.04;bevel.segments=3
for record in data['lights']:
 light=bpy.data.lights.new(record['name'],'AREA');light.energy=record['power'];light.shape='DISK';light.size=record['size']
 light.color=tuple(int(record['color'][i:i+2],16)/255 for i in (1,3,5))
 obj=bpy.data.objects.new(record['name'],light);scene.collection.objects.link(obj);obj.location=record['position']
 obj.rotation_euler=(Vector(record['target'])-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Studio camera');obj=bpy.data.objects.new('Studio camera',camera);scene.collection.objects.link(obj)
scene.camera=obj;camera.lens=data['camera']['lens'];obj.location=data['camera']['position']
obj.rotation_euler=(Vector(data['camera']['target'])-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.image_settings.file_format='PNG'
motion=data.get('motion',{'preset':'still','seconds':5})
preset=motion['preset']
scene.render.fps=24
scene.render.film_transparent=False
frames=1 if preset=='still' else round(motion['seconds']*24)
scene.frame_start=1;scene.frame_end=frames
start=Vector(data['camera']['position']);target=Vector(data['camera']['target'])
# Bake eased camera positions so the editable blend matches the rendered preview.
for frame in range(1,frames+1):
 t=(frame-1)/max(1,frames-1);ease=t*t*(3-2*t);offset=start-target
 if preset=='orbit':
  angle=math.radians(90)*ease;c=math.cos(angle);s=math.sin(angle)
  pos=target+Vector((offset.x*c-offset.y*s,offset.x*s+offset.y*c,offset.z))
 elif preset in ('dolly-in','dolly-out'):
  pos=target+offset*(1+(-.35 if preset=='dolly-in' else .35)*ease)
 elif preset in ('truck-left','truck-right'):
  right=offset.cross(Vector((0,0,1))).normalized()
  pos=start+right*(2*ease*(1 if preset=='truck-right' else -1))
 else:pos=start
 obj.location=pos;obj.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler()
 if frames>1:
  obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='rotation_euler',frame=frame)
scene.frame_set(1)
if frames>1:
 (folder/'frames').mkdir(exist_ok=True)
 scene.render.filepath=str(folder/'frames')+'/'
else:scene.render.filepath=str(folder/'render.png')
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'))
if frames>1:bpy.ops.render.render(animation=True)
else:bpy.ops.render.render(write_still=True)
(folder/'result.json').write_text(json.dumps({'file':str(folder/'render.png'),'blend':str(folder/'scene.blend'),'version':bpy.app.version_string,'frames':frames if frames>1 else 0,'fps':24}),encoding='utf-8')
