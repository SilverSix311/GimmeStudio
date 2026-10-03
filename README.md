# GimmeStudio

A local production studio for project planning, character design, image/video workflows, 3D blockouts, voice drafts, timeline editing and reviewed cloud handoff.

## Install on Windows, Linux or macOS

Download and extract the repository ZIP, then double-click **Setup-GimmeStudio.cmd**. After setup, run **GimmeStudio.cmd**. No administrator privileges or preinstalled Python, Git, Node, LM Studio or Blender are required. All application files stay in the extracted folder.

The installer provisions the pinned NVIDIA ComfyUI portable runtime, dashboard dependencies and Chromium. Models and specialized adapters are separate. Optional portable llama.cpp and Blender: `Setup-GimmeStudio.ps1 -WithLocalAI -WithBlender`.

On Linux or macOS, run `bash Setup-GimmeStudio.sh --core-only`, then `bash GimmeStudio.sh`. This installs a project-managed Python and browser without using an installed Python. Omit `--core-only` to install ComfyUI too; choose `--backend cpu`, `--backend cuda` (Linux NVIDIA), or `--backend mps` (Apple Silicon). Model and GPU workflows require platform-specific validation.

See [installation, model setup and backup instructions](Docs/INSTALL.md). Windows NVIDIA generation is locally tested; Linux/macOS core setup is tested in CI. GPU generation support depends on the selected model and nodes. This is an early portable release, not a claim of complete Higgsfield parity.

## Start the existing portable installation

Run **GimmeStudio.cmd**, then open http://127.0.0.1:8190. Choose **Help** in the header or **Help & tutorials** in the sidebar for the searchable handbook.

- [Start here: your first film](Docs/guide/Start-here.md)
- [Complete handbook](Docs/guide/Home.md)
- [Troubleshooting](Docs/guide/Troubleshooting.md)
- [Assistant and API reference](Docs/guide/Assistant-and-API.md)

## Local workflow

Create a project → design characters and scenes → stage a visible ComfyUI workflow → run and review takes → edit the timeline → review subtitles → export a VISION package.

The installation uses its own portable Python, ComfyUI, llama.cpp, browser and Blender. Windows and the NVIDIA driver are host prerequisites. Use one heavy model worker at a time. The dashboard stays available when models are unloaded.

## Documentation maintenance

`Docs/help.json` is the shared source for in-app Help and the documentation. Run the bundled Python with `Harness/build_help.py` after editing it. This builds `Docs/guide`, `Publishing/wiki` and `Studio/help/GimmeStudio-wiki.zip`. GitHub Wiki files include Home, a sidebar and a footer.

## Source and runtime boundaries

Source control should contain application code, launchers, documentation and reviewed configuration templates. Models, installed third-party tools, caches, logs, browser profiles, credentials, private projects and rendered media belong outside published source. A source checkout is not the fully provisioned portable installation; model and tool provisioning is separate.

## Current limits

See the in-app Tool catalog for validation status. Portrait lip-sync remains experimental on stylized faces. Whole-project Higgsfield synchronization, moving-video mask replacement, automatic face tracking and dedicated music generation are not completed integrations. Cloud asset upload requires a developer account and explicit action; no cloud generation runs automatically.

## Incognito workspace

The header toggle opens a separate persistent workspace for private/NSFW productions. Its projects, assets, history and chat settings stay under `Incognito/`. It reuses shared SFW models/LoRAs without copying weights and supports its own model library. This is content organization, not encryption or automatic NSFW detection. See [workspace separation](Docs/guide/Incognito-workspace.md).
