# LoRA library, keyframes and timeline monitor

Use visual model management, ordered shot adapters and source-frame editing.

In GimmeStudio: **Help → LoRA library, keyframes and timeline monitor**. Tool: `loras`.

## Visual library

1. Start ComfyUI using the dashboard header. Open LoRA library → Open visual LoRA Manager.
2. Model weights stay in Models/loras. Manager settings, sidecars, example images and recipes live under User/lora-manager in each workspace. Shared SFW weights remain shared; manager move/delete operations affect the underlying file.
3. Fresh portable installs: run Harness/install_lora_manager.py with the project Python after unloading ComfyUI. It pins upstream source and constrains installed dependencies. No automatic model download is performed.

## Shot controls

1. In Cinema Studio, choose LoRAs & keyframes. Set first/last project-image references and add an ordered LoRA stack.
2. Select a family from each model card and choose model strength. GimmeStudio rejects declared family mismatches, missing files and duplicate preset LoRAs; it cannot guarantee adapter quality from the filename.
3. Generate take saves the same stack in both native canvas and API graph. Inspect it with Load studio shot before pressing Run.
4. Choose the separate 360-orbit recipe for matching endpoints, 768 square, 73 frames, 28 steps and silent output. It replaces the preset turbo adapter. The community motion recipe remains experimental for new subjects.

## Character studies

- Krea 2 new-image and image-to-image remain available. LoRA library offers turnaround, expression and prop prompt starters.
- Anima Turbo is available in Generate locally: 8 steps, CFG 1, Euler/simple, using its own Qwen 0.6B encoder and the existing Qwen image VAE. Use 512–1536 pixels per side. Oversized UI selections become 1024 square.
- Optional model installers: project Python Harness/install_creative_models.py anima or orbit. Sources, revisions and checksums live in Config/creative-models.json. Base H3 and Qwen VAE prerequisites are separate.
- Review generated sheets before approving references or exporting a training dataset. A shared prompt does not guarantee identity consistency.

## Timeline monitor

1. Add stills or videos in Timeline & sound. Scrub the assembly monitor or jump to a clip using its time button.
2. Change source In/Out handles and reorder using the arrows. Save timeline persists the edit.
3. The monitor displays source frames and uses the edit overlap for placement. It does not simulate dissolves, grading or layered audio live. Render local preview produces the composed result with those effects.

## Primary references

- https://github.com/willmiao/ComfyUI-Lora-Manager
- https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA
- https://huggingface.co/circlestone-labs/Anima

## Continue learning

- [Models, VNCCS and LoRA training](Models-and-training.md)
- [Start here: your first film](Start-here.md)

[Handbook home](Home.md)
