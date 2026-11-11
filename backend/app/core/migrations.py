import json
from ..services.discussion_status import classify_discussion


def migrate(con):
    additions = {'users': {'can_access_all': 'INTEGER DEFAULT 0'},
                 'patients': {'psychosocial_json': "TEXT DEFAULT '{}'", 'source_overrides_json': "TEXT DEFAULT '{}'", 'data_version': 'INTEGER DEFAULT 0', 'archived_at': 'TEXT', 'archive_reason': "TEXT DEFAULT ''", 'dataset_source': 'TEXT'},
                 'episodes': {'interpretation_json': 'TEXT', 'interpreted_at': 'TEXT', 'review_notes': "TEXT DEFAULT ''", 'discussion_status': "TEXT DEFAULT ''"}}
    discussion_status_added = False
    for table, columns in additions.items():
        existing = {row[1] for row in con.execute('PRAGMA table_info(' + table + ')')}
        for name, spec in columns.items():
            if name not in existing:
                con.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + name + ' ' + spec)
                if table == 'episodes' and name == 'discussion_status':
                    discussion_status_added = True
    if discussion_status_added:
        rows = con.execute('SELECT e.patient_id,e.decision,e.amplified,p.original_json,p.source_overrides_json FROM episodes e JOIN patients p ON p.id=e.patient_id').fetchall()
        for row in rows:
            raw = json.loads(row['original_json'] or '{}')
            raw.update(json.loads(row['source_overrides_json'] or '{}'))
            stage = classify_discussion(raw.get('decision Category'), row['decision'] or raw.get('Decision'), row['amplified'])
            con.execute('UPDATE episodes SET discussion_status=? WHERE patient_id=?', (stage, row['patient_id']))

    con.execute('CREATE TABLE IF NOT EXISTS lab_attempts(id INTEGER PRIMARY KEY,patient_id INTEGER,actor_id INTEGER,created_at TEXT,snapshot_json TEXT)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_audit_entity_action ON audit(entity,action)')
    con.execute('CREATE TABLE IF NOT EXISTS episode_revisions(id INTEGER PRIMARY KEY,patient_id INTEGER,actor_id INTEGER,reason TEXT,snapshot_json TEXT,created_at TEXT)')
