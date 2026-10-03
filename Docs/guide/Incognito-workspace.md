# Incognito and SFW workspaces

Keep private/NSFW productions separate while reusing model weights.

In GimmeStudio: **Help → Incognito and SFW workspaces**. Tool: `overview`.

## Switch workspaces

1. Use SFW - Open Incognito in the header. Finish or pause jobs first; idle model workers unload when switching.
2. Incognito opens on port 8290, with its own ComfyUI on 8288 and planner on 8289. A persistent banner identifies the mode.
3. Create private characters, projects and assets here. Use Incognito ON - Return to SFW to return. Existing SFW projects are not moved.

## Storage and shared weights

- SFW data remains in Projects, Studio, Input, Output, User and Cache. Incognito data, chats, logs, browser selections and workflows live in their own workspace under Incognito.
- Place private model weights in Incognito/Models and private LoRAs in Incognito/Models/loras. Shared SFW weights remain in Models; ComfyUI reads them through an extra model-path configuration, with no duplicate downloads.
- Use distinct filenames for private and shared models. Private paths take precedence when filenames overlap. Inspect the loaded workflow before generating.
- Incognito inherits SFW chat-model profiles. Override or add profiles in Incognito/Studio/ai-models.json using paths relative to Incognito, such as Models/llm/example.gguf. Shared files appear under Models/Shared-SFW.
- The shared model directory is a link for reading/reuse, not an OS write-protected mount. Editing or deleting shared weights affects both workspaces.
- Incognito is persistent organization, not encryption, anonymous browsing or automatic deletion. The application does not detect or classify NSFW content. Choose the correct mode before importing or generating.
- Cloud credentials and handoff records are separate. Only explicitly importing or exporting a project transfers content across workspaces. Back up Incognito separately; it is excluded from published source.
- Generation workers are checked across workspaces to avoid competing heavy jobs. Close obsolete ComfyUI tabs when switching; each canvas stays tied to its own workspace.

## Continue learning

- [Models, VNCCS and LoRA training](Models-and-training.md)
- [Backups and portable exports](Backups-and-export.md)
- [AI Director and Laya](AI-Director.md)

[Handbook home](Home.md)
