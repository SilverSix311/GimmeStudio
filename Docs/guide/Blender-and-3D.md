# Blender and the 3D set workshop

Block out a set, render it locally, and continue editing in portable Blender.

In GimmeStudio: **Help → Blender and the 3D set workshop**. Tool: `sets3d`.

## Create a blockout

1. Open 3D set workshop. Name the scene and add cubes, spheres, cylinders, cones or planes.
2. Select an object and edit its name, color, position, scale and rotation. Enter X, Y, Z numbers separated by commas. Rotation uses degrees.
3. Drag the viewport to orbit, scroll to zoom, and right-drag to pan. Choose Use this camera angle when the framing is right.
4. Set lens, render size and key-light power. Save scene.
5. Choose Render in Blender. Watch Jobs & history; the result appears in Assets with a saved editable .blend file.

## Continue in native Blender

1. Reload the project after the render, then find its render card in 3D set workshop.
2. Choose Edit in portable Blender. Make changes and save the .blend in Blender.
3. Back in GimmeStudio choose Re-render saved Blender edits for that card. The new render is collected as another asset.
4. Use that image as a reference for a generation or add it to an animatic.

## Choose the right render button

Render in Blender rebuilds the blockout from the saved dashboard scene. Re-render saved Blender edits renders the native .blend you edited, retaining those Blender changes. Open portable Blender launches the bundled application. Preferences and worker outputs stay inside this installation.

## Continue learning

- [Assets, comparisons and review](Assets-and-review.md)
- [ComfyUI workflows and memory](ComfyUI-workflows.md)

[Handbook home](Home.md)
