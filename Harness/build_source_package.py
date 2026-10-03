"""Prepare an explicit source-only publication bundle. Never copy runtime/user data."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODULES='server studio_store studio_api studio_cli studio advanced help production local_ai local_agent agent agent_canvas comfy_service visible_workflow advanced_studio masked_edit cloud_handoff media_worker blender_scene blender_saved portable_browser laya_decision build_help build_source_package initialize_portable doctor runtime_paths setup_unix launch_studio smoke_portable workspaces smoke_workspaces'.split()

def build():
 files=[ROOT/name for name in ('README.md','Environment.ps1','GimmeStudio.cmd','Start-GimmeStudio.ps1','Stop-Local-Studio.ps1','Setup-GimmeStudio.cmd','Setup-GimmeStudio.ps1','Docs/INSTALL.md','NOTICE.md','.gitattributes','Environment.sh','Setup-GimmeStudio.sh','GimmeStudio.sh','GimmeStudio.command')]
 for folder in ('Config','Integrations','.github'):
  files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and (p.suffix in ('.json','.txt','.py','.js','.yml','.md','.png') or p.name=='LICENSE') and '__pycache__' not in p.parts]
 for name in MODULES:
  files += [p for ext in ('.py','.js','.html','.css') if (p:=ROOT/'Harness'/(name+ext)).is_file()]
 files += list((ROOT/'Harness').glob('test_*.py'))
 files += [ROOT/'Harness/advanced-requirements.txt',ROOT/'Harness/dashboard.html',ROOT/'Harness/index.html',ROOT/'Harness/lab.html']
 files += [ROOT/'Docs/help.json']+list((ROOT/'Docs/guide').glob('*.md'))
 files += [ROOT/'Studio/help/GimmeStudio-wiki.zip']
 # The local ComfyUI bridge is authored here; upstream ComfyUI and its installed nodes are excluded.
 destination=ROOT/'Publishing/source';destination.mkdir(parents=True,exist_ok=True)
 manifest=[]
 for source in sorted(set(files)):
  relative=source.relative_to(ROOT);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
  # A public install uses the gradient; personal wallpaper is not distributed.
  if relative.as_posix() == 'Harness/studio.css':
   target.write_text(target.read_text(encoding='utf-8').replace(",url('/studio-file/Studio/brand/wallpaper.jpeg') center/cover", ''),encoding='utf-8')
  manifest.append(dict(file=relative.as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size))
 (destination/'.gitignore').write_text('/Incognito/\n/Models/\n/Tools/\n/Downloads/\n/Cache/\n/Logs/\n/User/\n/Projects/\n/Input/\n/Output/\n/Publishing/\n/Studio/\n/Workflows/\n/Harness/staged-workflow.json\n__pycache__/\n*.pyc\n.env*\n/ComfyUI_windows_portable/\n',encoding='utf-8')
 (destination/'SOURCE-PACKAGE.txt').write_text('GimmeStudio portable source release. Run Setup-GimmeStudio.cmd to provision its runtime.\nExcluded: credentials, models, binaries, chats, projects, rendered media, private configuration, character canon and personal wallpaper. The GimmeStudio logo is intentionally included.\nSetup provisions pinned core runtimes. Optional models and advanced adapters keep their own licenses; see Docs/INSTALL.md.\nExisting portable installations should retain their local configuration and workflow library.\nDocumentation source: Docs/help.json. Build with Harness/build_help.py.\nGitHub destination and visibility must be selected before publication.\n',encoding='utf-8')
 (ROOT/'Publishing/source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 with zipfile.ZipFile(ROOT/'Publishing/GimmeStudio-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
  for entry in manifest:archive.write(destination/entry['file'],entry['file'])
  for name in ('.gitignore','SOURCE-PACKAGE.txt'):archive.write(destination/name,name)
 print(f'Prepared {len(manifest)} explicit source/documentation files; runtime and private data excluded')

if __name__=='__main__':build()
