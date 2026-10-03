# Portable Windows installation

1. Download and extract the GimmeStudio source ZIP, or clone the repository, into a writable folder such as `D:\GimmeStudio`. Avoid protected Windows folders and cloud-synced directories.
2. Double-click **Setup-GimmeStudio.cmd**. Internet is needed for setup. No administrator, installed Python, Git, Node, LM Studio or desktop Blender is required.
3. Double-click **GimmeStudio.cmd**. The bundled browser opens the local dashboard. Create your own project; personal example productions are not distributed.

The default setup downloads the pinned official NVIDIA ComfyUI portable runtime (about 2 GB compressed), Python dependencies, and Chromium. Allow at least 15 GB free for setup, plus space for models, caches and media. Windows x64 and a CUDA-13-compatible NVIDIA driver/GPU are required for the supplied generation runtime. Other GPU platforms are not validated by this installer. The dashboard itself does not require model weights.

Optional portable tools:

```powershell
.\Setup-GimmeStudio.ps1 -WithLocalAI -WithBlender
```

This adds the pinned llama.cpp CUDA runtime and Blender ZIP. It does not download models. Large chat/image/video models have individual hardware requirements and licenses. A preset existing in the UI does not mean its models are installed.

## Models and advanced features

Keep all weights inside `Models`. The lightweight chat profile expects `Models/llm/Qwen3-8B-Q4_K_M.gguf`. Normal and Heretic profiles are configured in `Studio/ai-models.json`; copy the example in `Config/ai-models.example.json`, set paths relative to the studio root, and mark `verified` true only after checking the source/hash. Consult the model publisher's license before use. Do not commit weights.

The included sanitized Krea/reference/H3 recipe templates retain the tested node settings and model filenames but contain no production assets or character canon. Install their required models and nodes before running them. See [the workflow handbook](guide/ComfyUI-workflows.md) and each model's upstream instructions. Optional speech, transcription, lip-sync, Laya, VNCCS and LoRA training dependencies are **not provisioned by this first installer**. Existing configured installations retain these integrations.

## Portable storage and moving

Runtimes, browser profiles, downloads, models, project databases and caches stay inside this directory. Windows and GPU drivers remain host prerequisites. Stop all studio services and close the bundled browser before moving or backing up the entire folder. Start with `GimmeStudio.cmd` at the new location; do not move a folder while processes use it. Files explicitly imported by users are copied into project assets.

## Reruns, updates and recovery

Setup preserves existing runtimes, projects, databases and configuration; it installs the pinned dashboard requirements and refreshes the authored Comfy bridge. It does not silently upgrade ComfyUI or third-party nodes. Back up `Projects`, `Studio`, `Models`, `User` and your custom workflows before updates. Downloaded archives are SHA-256 checked and cached in `Downloads`; interrupted `.partial` downloads are retried. If extraction fails, inspect the retained `Cache/setup-*` directory. Never run setup while generation is active.

Run the local diagnostic without starting GPU workers:

```powershell
. .\Environment.ps1
.\ComfyUI_windows_portable\python_embeded\python.exe -s Harness/doctor.py
```

Ports: dashboard 8190, ComfyUI 8188, local planner 8189. Keep these loopback services private. On failure inspect `Logs`. `-SkipBrowser` is intended for automated install testing and does not install the normal launcher browser.

Upstream packaging: [ComfyUI portable documentation](https://docs.comfy.org/installation/comfyui_portable_windows). Third-party tools and model weights retain their own licenses.
