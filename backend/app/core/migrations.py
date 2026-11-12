import json
from ..services.discussion_status import classify_discussion


def migrate(con):
    additions = {'users': {'can_access_all': 'INTEGER DEFAULT 0'},
                 'patients': {'psychosocial_json': "TEXT DEFAULT '{}'", 'source_overrides_json': "TEXT DEFAULT '{}'", 'data_version': 'INTEGER DEFAULT 0', 'archived_at': 'TEXT', 'archive_reason': "TEXT DEFAULT ''", 'dataset_source': 'TEXT'},
                 'episodes': {'interpretation_json': 'TEXT', 'interpreted_at': 'TEXT', 'review_notes': "TEXT DEFAULT ''", 'discussion_status': "TEXT DEFAULT ''",
                              'eligibility_status': 'TEXT', 'eligibility_json': 'TEXT', 'referral_basis': "TEXT DEFAULT ''",
                              'centrifuged_at': 'TEXT', 'tubes': 'INTEGER', 'whole_blood_ml': 'REAL', 'storage_temp': 'TEXT', 'workflow_collection': 'INTEGER DEFAULT 0',
                              'dispatched_at': 'TEXT', 'received_at': 'TEXT', 'plasma_volume_ml': 'REAL', 'cphl_outcome': 'TEXT', 'cphl_reason': "TEXT DEFAULT ''",
                              'dr_lab': 'TEXT', 'dr_referred_at': 'TEXT', 'tested_at': 'TEXT', 'attempt_no': 'INTEGER DEFAULT 1',
                              'risk_category': 'TEXT', 'risk_flagged': 'INTEGER DEFAULT 0', 'risk_json': 'TEXT',
                              'officer_name': "TEXT DEFAULT ''", 'officer_phone': "TEXT DEFAULT ''", 'sequence': "TEXT DEFAULT ''",
                              'suggestion_json': 'TEXT', 'started_regimen': "TEXT DEFAULT ''", 'start_date': 'TEXT', 'previous_stop_date': 'TEXT'}}
    discussion_status_added = False
    lab_stages_added = False
    for table, columns in additions.items():
        existing = {row[1] for row in con.execute('PRAGMA table_info(' + table + ')')}
        for name, spec in columns.items():
            if name not in existing:
                con.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + name + ' ' + spec)
                if table == 'episodes' and name == 'cphl_outcome':
                    lab_stages_added = True
                if table == 'episodes' and name == 'discussion_status':
                    discussion_status_added = True
    if discussion_status_added:
        rows = con.execute('SELECT e.patient_id,e.decision,e.amplified,p.original_json,p.source_overrides_json FROM episodes e JOIN patients p ON p.id=e.patient_id').fetchall()
        for row in rows:
            raw = json.loads(row['original_json'] or '{}')
            raw.update(json.loads(row['source_overrides_json'] or '{}'))
            stage = classify_discussion(raw.get('decision Category'), row['decision'] or raw.get('Decision'), row['amplified'])
            con.execute('UPDATE episodes SET discussion_status=? WHERE patient_id=?', (stage, row['patient_id']))

    if lab_stages_added:
        backfill_lab_stages(con)
    con.execute('CREATE TABLE IF NOT EXISTS follow_ups(id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES patients(id),due_date TEXT,assessed_on TEXT,vl_copies REAL,vl_date TEXT,regimen TEXT,care_status TEXT,psychosocial TEXT DEFAULT \'\',clinical_status TEXT DEFAULT \'\',notes TEXT DEFAULT \'\',actor_id INTEGER REFERENCES users(id),created_at TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS lab_attempts(id INTEGER PRIMARY KEY,patient_id INTEGER,actor_id INTEGER,created_at TEXT,snapshot_json TEXT)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_audit_entity_action ON audit(entity,action)')
    con.execute('CREATE TABLE IF NOT EXISTS iac_sessions(id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES patients(id),session_date TEXT NOT NULL,adherence_pct REAL,method TEXT,barriers TEXT DEFAULT \'\',actor_id INTEGER REFERENCES users(id),created_at TEXT)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_iac_patient ON iac_sessions(patient_id,session_date)')
    con.execute('CREATE TABLE IF NOT EXISTS episode_revisions(id INTEGER PRIMARY KEY,patient_id INTEGER,actor_id INTEGER,reason TEXT,snapshot_json TEXT,created_at TEXT)')


def backfill_lab_stages(con):
    """Map the CPHL extract's lab dates onto the staged workflow (documented values only)."""
    from ..services.history_service import date
    rows = con.execute("SELECT e.patient_id,e.sample_type,e.status,p.original_json,p.source_overrides_json FROM episodes e JOIN patients p ON p.id=e.patient_id").fetchall()
    for row in rows:
        raw = json.loads(row['original_json'] or '{}')
        raw.update(json.loads(row['source_overrides_json'] or '{}'))
        referred = date(raw.get('Date referred to DR Lab'))
        tested = date(raw.get('dateTestedForDR'))
        lab = {'Plasma': 'JCRC', 'DBS': 'UVRI'}.get(row['sample_type']) if referred else None
        con.execute('UPDATE episodes SET dr_referred_at=?,tested_at=?,cphl_outcome=?,dr_lab=? WHERE patient_id=?',
                    (referred, tested, 'Referred to DR lab' if referred else None, lab, row['patient_id']))
