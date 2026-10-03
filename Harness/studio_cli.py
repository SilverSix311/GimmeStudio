"""Use GimmeStudio's same local command API from the portable Python runtime."""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('operation',choices=['list','get','history','command','services'])
parser.add_argument('value',nargs='?',help='Project ID or JSON command file; use - for stdin')
args=parser.parse_args()
base='http://127.0.0.1:8190'
data=None
if args.operation=='command':
    if not args.value:
        parser.error('command needs a JSON file or - for stdin')
    payload=json.loads(sys.stdin.read() if args.value=='-' else Path(args.value).read_text(encoding='utf-8'))
    data=json.dumps(payload).encode()
    path='/api/studio/command'
elif args.operation in ('get','history'):
    if not args.value:
        parser.error('Provide a project ID')
    path='/api/studio/'+('project' if args.operation=='get' else 'history')+'/'+args.value
else:
    path='/api/studio'+('/services' if args.operation=='services' else '')
try:
    request=urllib.request.Request(base+path,data,{'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=1800) as response:
        print(json.dumps(json.load(response),indent=2,ensure_ascii=False))
except urllib.error.HTTPError as error:
    print(error.read().decode(),file=sys.stderr)
    sys.exit(1)
