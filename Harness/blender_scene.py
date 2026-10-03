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
scene.render.filepath=str(folder/'render.png')
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'))
bpy.ops.render.render(write_still=True)
(folder/'result.json').write_text(json.dumps({'file':str(folder/'render.png'),'blend':str(folder/'scene.blend'),'version':bpy.app.version_string}),encoding='utf-8')
