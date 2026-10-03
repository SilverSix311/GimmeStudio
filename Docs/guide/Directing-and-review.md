# Directing and reviewing shots

Camera previews, timed direction, take comparison and portable dependency records.

In GimmeStudio: **Help → Directing and reviewing shots**. Tool: `review`.

## Rehearse camera motion

- In 3D set workshop, arrange your objects and capture the camera angle.
- Add mannequin inserts simple head, torso, arms and legs. These are editable blocking shapes, not a rigged or animated character.
- Choose Still image, 90-degree orbit, Dolly in/out or Truck left/right, and a duration of 1–15 seconds. Save the scene.
- Render in Blender creates a local image or 24 fps video asset plus an editable scene.blend. Motion is eased and the camera looks at its saved target.
- These are blocking previews. H3 reference-video conditioning is a separate workflow and is not automatically applied.

## Plan shot direction

- In Cinema Studio choose Direction & cues. Add timed beats within the shot duration.
- Assign project assets as character, environment, motion, voice or timed guide references. Role compatibility is validated when saving.
- These records support review and handoff. They do not silently modify the generation graph.

## Review theatre

- Choose a shot and video takes A and B. Play together, scrub, or select Wipe comparison. Shorter takes hold their last frame.
- Audio is muted by default; listen to A or B. Timed shot beats highlight during playback.
- Record continuity checks and notes against take A. Use take A for this shot selects it without approving the asset.
- Capture frame from A saves the current video frame as a pending image asset, with its source video hash and timestamp. Frames from the same video share a dataset group to avoid train/validation leakage.
- Saved review notes retain the current playback selection. Asset approval remains in Asset library.

## ComfyUI director extensions

- Optional installer: run Harness/install_director_tools.py with the portable Python while both workspaces’ ComfyUI servers are stopped.
- Pinned GuideMaster and Genkai nodes are installed without changing the Torch stack. Search the ComfyUI node menu for MajoorH3GuideMaster or Genkai.
- GuideMaster requires positive conditioning and latents; image guides also need the video VAE and audio guides the audio VAE. Its reference filmstrip and waveform are preview-only.
- Genkai PromptSync connects a timed prompt and video source; its optional Save node requires VideoHelperSuite. Node registration was tested; model conditioning and every optional encoder are not certified.

## Portable handoff

- VISION ZIP exports include DIRECTION.json and DEPENDENCIES.json.
- Dependencies lists node types and model filenames from saved execution graphs and shot LoRAs. It does not include model weights or prove model hashes/compatibility.
- Direction records carry explicit timing, reference roles and review notes. conditioning_applied=false makes their planning status explicit.

## Continue learning

- [Start here: your first film](Start-here.md)

[Handbook home](Home.md)
