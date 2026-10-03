# Assistant and API reference

Use the same revisioned commands as the dashboard.

In GimmeStudio: **Help → Assistant and API reference**. Tool: `ai`.

## Read the current state

```text
ComfyUI_windows_portable/python_embeded/python.exe Harness/studio_cli.py list
ComfyUI_windows_portable/python_embeded/python.exe Harness/studio_cli.py get PROJECT_ID
ComfyUI_windows_portable/python_embeded/python.exe Harness/studio_cli.py services
```

## Apply a reviewed command

```text
{
  "action": "put",
  "project": "PROJECT_ID",
  "revision": 1,
  "kind": "elements",
  "value": {"name": "Iris", "kind": "character", "description": "A friendly robot", "references": []}
}
```

## Command rules

- Save the JSON to a workspace file and pass it to Harness/studio_cli.py command command.json, or use - for JSON stdin. Replace PROJECT_ID and revision with the current values.
- GET /api/studio lists operation names; GET /api/studio/project/ID reads a project; GET /api/studio/history/ID reads revision summaries.
- POST /api/studio/command is the shared mutation surface. Existing-project changes require project and current revision. Stale edits are rejected.
- Image generation is staged for visible frontend execution by default. Do not bypass review by silently approving generated outputs.
- Harness/studio_api.py validates ordinary commands. advanced_studio.py, masked_edit.py and cloud_handoff.py validate their tool-specific fields.

## Advanced actions

- masked-edit: image asset ID, PNG mask data URL, prompt, seed and feather pixels.
- advanced/scene-save, advanced/blender-render, advanced/blender-open, advanced/blender-rerender and advanced/blender-launch control local 3D work.
- advanced/voice-save, advanced/speak and advanced/lipsync control saved voices and portrait speech.
- cloud/plan is local-only. cloud/upload requires approved asset IDs and explicit confirm_upload=true.

## Agent control API

- GET /api/agent/state/PROJECT_ID returns settings, current plan and activity; private undo snapshots are omitted.
- POST /api/agent/settings takes project and settings: enabled, mode (ask/routine/full), model (normal/heretic/light), max_generations (0–8), use_laya.
- POST /api/agent/plan takes project and prompt. POST /api/agent/approve takes project and the displayed run ID. Additional controls: pause, cancel, edit (unstarted plan), undo.
- Agent operations are stored under Projects/ID/agent. A restart marks unfinished agent work failed instead of automatically replaying it. Inspect Jobs before retrying.

## Continue learning

- [AI Director and Laya](AI-Director.md)
- [ComfyUI workflows and memory](ComfyUI-workflows.md)

[Handbook home](Home.md)
