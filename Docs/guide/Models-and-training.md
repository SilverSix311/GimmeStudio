# Models, VNCCS and LoRA training

Build a reviewed dataset and stage a compatible training experiment.

In GimmeStudio: **Help → Models, VNCCS and LoRA training**. Tool: `dataset`.

## Prepare the dataset

1. Create the character or object identity, then generate varied reference views with consistent design.
2. Review images in Assets. Assign each to the intended element and write an accurate, image-specific caption.
3. Separate train and validation images. Put related crops or versions of the same source in the same split.
4. Approve the useful images, then open LoRA workshop and select the element.
5. Export reviewed dataset. Resolve any duplicate-content, missing-caption or split-leakage errors.
6. Prepare SDXL training canvas stages the installed SDXL recipe. Inspect its settings in ComfyUI before running an experiment.
7. Evaluate a trained adapter on held-out views and new prompts before using it for production.

## Compatibility and readiness

- The installed training recipe targets SDXL. It is not a general trainer for Krea, Qwen or H3.
- No trained character LoRA is supplied just because a dataset or training canvas exists.
- Use Open VNCCS character tools to stage the registered character workflow, then inspect the available nodes and readiness notes.
- Keep model files under Models in the correct family directory. A LoRA must match its base architecture. Record source, version and usage terms with downloaded models.
- Tool catalog distinguishes installed, tested and experimental features.

## Continue learning

- [Assets, comparisons and review](Assets-and-review.md)
- [ComfyUI workflows and memory](ComfyUI-workflows.md)

[Handbook home](Home.md)
