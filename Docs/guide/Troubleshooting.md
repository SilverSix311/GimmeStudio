# Troubleshooting and known limits

Recover from common setup, model and workflow problems.

In GimmeStudio: **Help → Troubleshooting and known limits**. Tool: `jobs`.

## The dashboard will not open

- Run GimmeStudio.cmd from this installation. Check Logs/harness.err.log if port 8190 does not become available.
- Do not launch an unrelated installed application to repair this portable setup. Use its own tools and launchers.

## A model will not start or memory is full

- Check Jobs & history and the service indicator. Finish the current queue before switching workers.
- Unload AI Director before starting ComfyUI. Unload ComfyUI before loading a large chat model.
- Reduce image dimensions or use the measured draft preset. Avoid several heavy workers at once.

## The workflow did not appear or results are missing

- Click Load studio shot inside ComfyUI; staging alone does not run it.
- Check for missing models or custom nodes before clicking Run.
- Wait for completion, then Collect completed takes. Only project-tagged workflows are automatically matched to this production.
- Reload the project after background work. Jobs & history shows errors and worker logs.

## The output looks wrong

- A seed does not guarantee identity. Compare references, prompt changes and denoise settings.
- For masks, inspect brush coverage and feathering; the model may alter geometry within the edited area.
- For lip-sync, use a clear frontal face and a tightly selected forehead-to-chin rectangle. Cartoon results remain experimental.
- Read Tool catalog before assuming support: masked video replacement, automatic moving-face tracking, dedicated music generation and native whole-project cloud synchronization are not installed capabilities.

## Report a useful issue

- Include the page, steps to reproduce, exact error and relevant worker log excerpt.
- Include model/workflow names and dimensions, and whether another worker was running.
- Do not share API credentials, the User directory, private chats or a whole project database in a public report.

## Continue learning

- [ComfyUI workflows and memory](ComfyUI-workflows.md)
- [Backups and portable exports](Backups-and-export.md)

[Handbook home](Home.md)
