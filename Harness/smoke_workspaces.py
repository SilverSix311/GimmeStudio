"""Exercise isolated origins and project stores on a running clean CI studio."""
import json
import urllib.error
import urllib.request
import workspaces


def api(port, endpoint, data=None):
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+endpoint,
        None if data is None else json.dumps(data).encode(), {'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=30))


normal=api(8190,'/api/studio')['projects'][0]['id']
api(8190,'/api/workspace/open',{'mode':'incognito'})
try:
    assert api(8290,'/api/workspace')['mode']=='incognito'
    private=api(8290,'/api/studio/command',{'action':'create','title':'Private workspace test'})['project']
    for port,key in ((8190,private['id']),(8290,normal)):
        try:
            api(port,'/api/studio/project/'+key)
        except urllib.error.HTTPError as error:
            assert error.code==400
        else:
            raise AssertionError('Cross-workspace project access')
    assert api(8290,'/api/workspace/open',{'mode':'sfw'})['url'].startswith('http://127.0.0.1:8190/')
    print('Independent project stores and workspace switching passed')
finally:
    process=workspaces.private_process()
    if process:
        process.terminate();process.wait(timeout=15)
