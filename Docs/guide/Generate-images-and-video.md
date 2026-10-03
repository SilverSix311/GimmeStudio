# Generate images and video

Stage a workflow, inspect it visibly, run it, and collect the result.

In GimmeStudio: **Help → Generate images and video**. Tool: `cinema`.

## Generate a take

1. Start ComfyUI from the dashboard header. If AI Director has a model loaded, unload it first.
2. Use Generate design on a character or Generate take for a shot in Cinema Studio.
3. Choose a new Krea image, a reference-guided Krea image, or the H3 image-to-video recipe. Reference and video modes need an image asset.
4. Write a specific prompt. For a shot, fill in its action, framing, movement, lighting and palette as needed.
5. Stage the workflow. In ComfyUI canvas click Load studio shot. Your previous canvas is backed up before replacement.
6. Inspect models, prompt, reference, seed and output settings, then click the native Run button.
7. Wait for completion and choose Collect completed takes. Review the result in Asset library and select it for the shot if it is the take you want.

## Settings that matter

- Krea dimensions must be multiples of eight, at least 256 pixels, and at most 2.5 megapixels. Larger images use more memory.
- Reference-guided Krea uses a starting image and denoise strength. Higher denoise allows more change; it is not a semantic mask editor.
- The measured H3 draft preset is 608 × 352, 124 frames, 24 fps, with native audio. A shot duration field does not silently change that generation recipe.
- Camera controls describe prompt intent. They do not guarantee physically simulated camera behavior.
- A 1080p timeline can contain lower-resolution drafts; changing canvas size does not recover missing detail.

## Continue learning

- [ComfyUI workflows and memory](ComfyUI-workflows.md)
- [Masked image editing](Masked-image-editing.md)
- [Assets, comparisons and review](Assets-and-review.md)

[Handbook home](Home.md)
