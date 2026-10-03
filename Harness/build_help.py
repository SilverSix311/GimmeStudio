"""Build repo documentation and GitHub Wiki pages from the in-app handbook."""
import json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build():
 data=json.loads((ROOT/'Docs/help.json').read_text(encoding='utf-8'))
 ids={p['id'] for p in data['pages']}
 assert len(ids)==len(data['pages'])
 for p in data['pages']:
  assert all(r in ids for r in p['related'])
 for directory,wiki in [('Docs/guide',False),('Publishing/wiki',True)]:
  folder=ROOT/directory;folder.mkdir(parents=True,exist_ok=True)
  suffix='' if wiki else '.md'
  link=lambda p:f'[{p["title"]}]({p["id"]}{suffix})'
  home='# GimmeStudio Handbook\n\nStart with '+link(data['pages'][0])+'.\n\n'+ '\n'.join('- '+link(p)+' — '+p['summary'] for p in data['pages'])+'\n\nUpdated '+data['updated']+'. These guides describe the current local implementation.\n'
  (folder/'Home.md').write_text(home,encoding='utf-8')
  for p in data['pages']:
   lines=['# '+p['title'],'',p['summary'],'',f'In GimmeStudio: **Help → {p["title"]}**. Tool: `{p["tool"]}`.','']
   for section in p['sections']:
    lines += ['## '+section['title'],'']
    if section['kind']=='code':lines+=['```text','\n'.join(section['items']),'```','']
    elif section['kind'] in ('steps','list'):lines += [(str(i+1)+'. ' if section['kind']=='steps' else '- ')+item for i,item in enumerate(section['items'])]+['']
    else:
     for item in section['items']:lines += [item,'']
   lines += ['## Continue learning','']+['- '+link(next(a for a in data['pages'] if a['id']==id)) for id in p['related']]+['','[Handbook home](Home'+suffix+')','']
   (folder/(p['id']+'.md')).write_text('\n'.join(lines),encoding='utf-8')
  if wiki:
   (folder/'_Sidebar.md').write_text('[Home](Home)\n\n'+'\n'.join('- '+link(p) for p in data['pages'])+'\n',encoding='utf-8')
   (folder/'_Footer.md').write_text('GimmeStudio · Local-first production · Sources maintained in Docs/help.json.\n',encoding='utf-8')
 out=ROOT/'Studio/help';out.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out/'GimmeStudio-wiki.zip','w',zipfile.ZIP_DEFLATED) as archive:
  for p in sorted((ROOT/'Publishing/wiki').glob('*.md')):archive.write(p,p.name)
 print(f'Built {len(data["pages"])} guides, repository handbook and GitHub Wiki ZIP')

if __name__=='__main__':build()
