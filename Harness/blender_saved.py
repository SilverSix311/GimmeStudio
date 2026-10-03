"""Render an explicitly selected saved scene, with automatic Python disabled."""
import bpy,json,sys
from pathlib import Path
folder=Path(sys.argv[sys.argv.index('--')+1])
scene=bpy.context.scene
if scene.camera is None:raise ValueError('Set an active camera in Blender before rendering')
if scene.render.resolution_x*scene.render.resolution_y>3840*2160:raise ValueError('Use a render size of 4K or below')
# Imported compositor file-output nodes must not write to arbitrary external paths.
if scene.use_nodes:
 for node in scene.node_tree.nodes:
  if node.type=='OUTPUT_FILE':node.mute=True
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(folder/'render.png')
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'scene.blend'))
bpy.ops.render.render(write_still=True)
(folder/'result.json').write_text(json.dumps(dict(file=str(folder/'render.png'),blend=str(folder/'scene.blend'),version=bpy.app.version_string)),encoding='utf-8')
