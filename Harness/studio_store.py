"""Project documents with transactional revisions; shared by UI and agent API."""
import copy
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'Studio/gimmestudio.sqlite3'


@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS revisions (project TEXT, revision INTEGER, action TEXT, body TEXT, at REAL, PRIMARY KEY(project, revision))')
    try:
        with db:
            yield db
    finally:
        db.close()


def identifier():
    return uuid.uuid4().hex[:12]


def blank(title):
    title = str(title).strip()
    if not title or len(title) > 160:
        raise ValueError('Project title must contain 1–160 characters')
    return dict(id=identifier(), title=title, brief='', style='', revision=1,
                created=time.time(), updated=time.time(), elements=[], scenes=[], shots=[],
                assets=[], jobs=[], captions=[], exports=[], folders=[],
                timeline=dict(clips=[], audio=[], fps=24, width=1920, height=1080,
                              transition='fade', transition_seconds=.5))


def insert(project):
    with connection() as db:
        body = json.dumps(project)
        db.execute('INSERT INTO projects VALUES (?, ?)', (project['id'], body))
        db.execute('INSERT INTO revisions VALUES (?, ?, ?, ?, ?)',
                   (project['id'], project['revision'], 'create', body, time.time()))
    return project


def get(key):
    with connection() as db:
        row = db.execute('SELECT body FROM projects WHERE id=?', (key,)).fetchone()
    if not row:
        raise ValueError('Unknown project')
    return json.loads(row[0])


def listing():
    with connection() as db:
        items = [json.loads(row[0]) for row in db.execute('SELECT body FROM projects')]
    return sorted([dict(id=p['id'], title=p['title'], revision=p['revision'], updated=p['updated'],
                        assets=len(p['assets']), shots=len(p['shots'])) for p in items
                   if not p.get('archived')], key=lambda p:p['updated'], reverse=True)


def mutate(key, revision, action, callback):
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT body FROM projects WHERE id=?', (key,)).fetchone()
        if not row:
            raise ValueError('Unknown project')
        p = json.loads(row[0])
        if revision is not None and p['revision'] != revision:
            raise ValueError('This project changed in another window. Reload before saving your changes.')
        callback(p)
        p['revision'] += 1
        p['updated'] = time.time()
        body = json.dumps(p)
        db.execute('UPDATE projects SET body=? WHERE id=?', (body, key))
        db.execute('INSERT INTO revisions VALUES (?, ?, ?, ?, ?)',
                   (key, p['revision'], action, body, p['updated']))
    return p


def history(key):
    get(key)
    with connection() as db:
        return [dict(revision=r[0], action=r[1], at=r[2]) for r in db.execute(
            'SELECT revision, action, at FROM revisions WHERE project=? ORDER BY revision DESC LIMIT 100', (key,))]


def migrate():
    """Copy legacy work once. Original files remain untouched."""
    marker = ROOT / 'Studio/project-migration.json'
    if marker.exists():
        return
    existing = {p['id'] for p in listing()}
    migrated = []
    for file in (ROOT / 'Projects').glob('*/episode.json'):
        old = json.loads(file.read_text(encoding='utf-8'))
        if file.parent.name in existing:
            continue
        p = blank(old.get('title', 'Imported production'))
        p.update(id=file.parent.name, brief=old.get('characters', ''), style=old.get('style', ''), legacy=True)
        characters = ROOT / 'Studio/characters.json'
        if characters.exists():
            for c in json.loads(characters.read_text(encoding='utf-8')):
                p['elements'].append(dict(c, id=identifier(), kind='character', references=[], notes=''))
        for shot in old.get('shots', []):
            p['shots'].append(dict(shot, id=identifier(), name=shot['id'], elements=[], scene='', takes=[], selected='', notes=''))
        insert(p)
        migrated.append(p['id'])
    if not listing():
        p = insert(blank('My first production'))
        migrated.append(p['id'])
    marker.write_text(json.dumps(dict(projects=migrated, at=time.time()), indent=2), encoding='utf-8')


def recover_jobs():
    # A finishing thread cannot survive a process restart. Keep its intent and error.
    for summary in listing():
        p = get(summary['id'])
        if any(j['status'] == 'running' for j in p['jobs']):
            def recover(doc):
                for job in doc['jobs']:
                    if job['status'] == 'running':
                        job.update(status='interrupted', error='Studio restarted during finishing. Inspect existing outputs before retrying.')
            mutate(p['id'], None, 'recover-interrupted-jobs', recover)
