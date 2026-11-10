def migrate(con):
    additions = {'users': {'can_access_all': 'INTEGER DEFAULT 0'},
                 'patients': {'psychosocial_json': "TEXT DEFAULT '{}'",'source_overrides_json': "TEXT DEFAULT '{}'",'data_version':'INTEGER DEFAULT 0','archived_at':'TEXT','archive_reason':"TEXT DEFAULT ''",'dataset_source':'TEXT'},
                 'episodes': {'interpretation_json': 'TEXT', 'interpreted_at': 'TEXT', 'review_notes': "TEXT DEFAULT ''"}}
    for table, columns in additions.items():
        existing = {row[1] for row in con.execute('PRAGMA table_info('+table+')')}
        for name, spec in columns.items():
            if name not in existing:
                con.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+spec)
    con.execute('CREATE TABLE IF NOT EXISTS lab_attempts(id INTEGER PRIMARY KEY,patient_id INTEGER,actor_id INTEGER,created_at TEXT,snapshot_json TEXT)')

    con.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity_action ON audit(entity,action)")

    con.execute("CREATE TABLE IF NOT EXISTS episode_revisions(id INTEGER PRIMARY KEY,patient_id INTEGER,actor_id INTEGER,reason TEXT,snapshot_json TEXT,created_at TEXT)")
