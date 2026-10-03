"""Opt-in model downloads from the reviewed, pinned creative model manifest."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def install(name):
    entry=json.loads((ROOT/'Config/creative-models.json').read_text(encoding='utf-8'))[name]
    for record in entry['files']:
        target=ROOT/'Models'/record['local']
        if not target.resolve().is_relative_to((ROOT/'Models').resolve()):
            raise ValueError('Model destination leaves workspace')
        if target.exists():
            print('Preserved existing '+record['local'])
            continue
        target.parent.mkdir(parents=True,exist_ok=True)
        partial=target.with_suffix(target.suffix+'.part')
        urllib.request.urlretrieve(entry['source']+'/resolve/'+entry['revision']+'/'+record['remote'],partial)
        with partial.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=record['sha256']:
            raise ValueError('Model checksum mismatch: '+record['local'])
        partial.rename(target)
        print('Verified '+record['local'])
    for dependency in entry['requires']:
        if not (ROOT/'Models'/dependency).exists():
            print('Still required: '+dependency)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',choices=['anima','orbit'])
    install(parser.parse_args().model)
