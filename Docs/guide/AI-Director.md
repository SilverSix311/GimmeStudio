# AI Director and Laya

Use local chat for drafts without spending cloud tokens.

In GimmeStudio: **Help → AI Director and Laya**. Tool: `ai`.

## Work with the local assistant

1. Unload ComfyUI, then open AI Director. Choose Normal, Heretic or Light and click Load model. Wait for it to load.
2. Ask for a specific task using the selected project, such as a shot plan or a clearer character description.
3. Review the draft. Saved chats remain attached to the project; use the history selector to reopen them.
4. For structured additions, choose Review structured draft and paste elements, scenes and/or shots JSON. Check the content before applying it.
5. Export transcript JSON when you want to keep a copy. Choose Unload model before switching to heavy generation.

## Example prompts

- Suggest three different five-second actions for this character. Keep the design and location consistent.
- Rewrite this shot prompt with a clear subject, action, framing, lighting and background.
- Review the scene for continuity problems and identify the smallest local test for each.

## Laya and edits

Classify next request with Laya is a local CPU routing experiment. Its answer is advisory. Chat drafts do not silently change designs or execute code; structured additions must pass the project command validation. Normal and Heretic profiles are alternative workers, not simultaneous models.

## Local AI agent and autonomy

1. Enable Local AI agent, choose the brain and generation limit, then Save autonomy settings. Settings belong to the selected project. The default is disabled with Ask for approval selected.
2. Ask for approval shows the complete plan, then requires approval for each step. Approve routine actions runs the reviewed plan after one approval. Full local autonomy validates and executes a bounded plan without waiting for approval.
3. Send a request in the normal message box. The agent loads the selected local model, creates a structured plan and validates it. Laya is optional advisory classification; it cannot grant permissions.
4. Review the summary, generation count and exact proposed parameters. Approve plan, Edit plan JSON, Revise request in plain language, or cancel.
5. The activity log shows executed steps and errors. Generation runs in a visible portable ComfyUI browser and collects outputs. The chat model unloads for generation; it will reload for the next agent request.
6. Pause or Stop waits for the current inference/render operation to finish. Changing permissions cancels an unstarted plan. A changed project revision prevents an old plan from overwriting newer edits.
7. Undo project edits restores pre-plan character/scene/shot/timeline records only when no later project changes conflict. Generated media and job evidence remain available.

## Agent capabilities and boundaries

The agent can create/edit world elements, scenes, shots and project direction; change timelines; run installed Krea/reference/H3 presets; render timelines; and transcribe existing assets. It has no shell, downloads, cloud spending/upload permissions, arbitrary workflow execution, asset-approval tool, visual quality judge, or training tool. Blender, mask painting and voice/lip-sync controls remain manual or assistant-operated. Full autonomy is a bounded plan of at most 12 actions and your selected generation budget (0–8); it is not an unlimited self-improvement loop. Invalid model plans get at most one correction attempt before stopping.

## Continue learning

- [ComfyUI workflows and memory](ComfyUI-workflows.md)
- [Assistant and API reference](Assistant-and-API.md)

[Handbook home](Home.md)
