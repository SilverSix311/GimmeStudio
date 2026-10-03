# Masked image editing

Change a selected area while preserving unpainted pixels.

In GimmeStudio: **Help → Masked image editing**. Tool: `masked`.

## Make an edit

1. Start ComfyUI and open Masked image editor. Choose a source image from the project.
2. Paint white over the area to change. Adjust Brush size; enable Erase to remove part of the mask. Clear mask starts over; Select all enables a full-image change.
3. Write an instruction such as: Change the shirt to turquoise while preserving the pose and fabric texture.
4. Set Feather pixels for a softer boundary. Feathering expands the affected region; keep it away from details you must preserve.
5. Choose Stage visible editing workflow. In ComfyUI click Load studio shot, inspect the mask and reference, then Run.
6. Collect the completed take and compare it with the source. Check both the edited area and the boundary.

## How it works

Qwen Image Edit 2511 sees the reference and instruction. A final mask composite puts the generated region over the original. This preserves pixels outside the feathered mask, but the model can still change shape or texture inside it. The recipe uses the matching four-step Lightning LoRA. This tool edits still images, not tracked regions in moving video.

## Continue learning

- [Generate images and video](Generate-images-and-video.md)
- [Assets, comparisons and review](Assets-and-review.md)

[Handbook home](Home.md)
