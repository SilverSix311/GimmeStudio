# ComfyUI workflows and memory

Watch generation, import recipes and switch GPU workloads safely.

In GimmeStudio: **Help → ComfyUI workflows and memory**. Tool: `workflows`.

## Use the visible canvas

1. Open ComfyUI canvas or its full-size link at http://127.0.0.1:8188.
2. Choose a registered workflow and Stage workflow, or import a canvas JSON as a project recipe.
3. Click Load studio shot inside ComfyUI. Enable Follow new studio workflows if you want subsequent staged graphs to appear automatically.
4. Edit nodes and run through the frontend. Collect completed takes after completion.
5. Keep the canvas and exact execution record with the result; GimmeStudio collects these for project-tagged runs.

## Switch between AI and generation

- Use one heavy model worker at a time. Unload the local AI model before starting ComfyUI.
- Unload ComfyUI in the dashboard header to free its RAM and GPU allocations. Busy queues are protected.
- Speech, lip-sync and background Blender jobs stop idle owned servers before starting. They release their allocations after finishing.
- An interactive Blender window is under your control; avoid starting another heavy GPU render alongside it.
- An imported workflow is not automatically compatible. Read its model and custom-node requirements and the Tool catalog status.

## Continue learning

- [AI Director and Laya](AI-Director.md)
- [Troubleshooting and known limits](Troubleshooting.md)
- [Models, VNCCS and LoRA training](Models-and-training.md)

[Handbook home](Home.md)
