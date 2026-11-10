from .migrations import migrate
from ..services.record_service import repair_existing
import csv
import secrets
from .config import ROOT, DB, SCHEMA
from .database import connect
from .security import password_hash
from ..services.import_service import import_rows

def initialize():
    DB.parent.mkdir(exist_ok=True)
    with connect() as con:
        con.executescript(SCHEMA.read_text(encoding='utf-8'))
        migrate(con)
        repair_existing(con)
        if not con.execute('SELECT count(*) FROM users').fetchone()[0]:
            password = secrets.token_urlsafe(12)
            for username, name, role in [('admin', 'Demo Administrator', 'admin'), ('nurse', 'Ms. Cynthia Nasikye', 'nurse'), ('counsellor', 'Counsellor David', 'counsellor'), ('lab', 'Dr. Stephen', 'lab'), ('clinician', 'Dr. Daniel', 'clinician')]:
                salt = secrets.token_hex(16)
                con.execute('INSERT INTO users(username,name,role,facility,salt,password_hash) VALUES(?,?,?,?,?,?)', (username, name, role, 'Demo Facility', salt, password_hash(password, salt)))
            (ROOT / 'data' / 'local_login.txt').write_text('LOCAL DEMO ACCOUNTS\nUsernames: admin, nurse, counsellor, lab, clinician\nPassword: ' + password + '\n', encoding='utf-8')
        if not con.execute('SELECT count(*) FROM patients').fetchone()[0]:
            seed(con)

def seed(con):
    source = ROOT / 'data' / 'synthetic_patients.csv'
    if source.exists():
        with source.open(encoding='utf-8-sig', newline='') as file:
            rows = list(csv.DictReader(file))
        import_rows(con, rows, 'synthetic', {'name': 'System import', 'role': 'system'})
    else:
        for i in range(36):
            p = {'Patient No.': f'DEMO-{i + 1:04}', 'Facility': 'Demo Facility', 'Age(yrs)': 22 + i % 40, 'sex': 'F' if i % 2 else 'M', 'ART at sample collection(ART@VL@DR)': 'TDF-3TC-DTG', 'Treatment Line at Sample collection': ['First Line', 'Second Line', 'Third Line'][i % 3], 'VL Leading to DR': [45, 450, 1400, 23000][i % 4], 'Simulated Adherence (%)': [100, 96, 82][i % 3]}
            import_rows(con, [p], 'synthetic', {'name': 'System import', 'role': 'system'})
    for i, p in enumerate(con.execute('SELECT id FROM patients ORDER BY id').fetchall()):
        pid = p['id']
        if i % 6 == 0:
            continue
        sample_type = 'DBS' if i % 4 == 0 else 'Plasma'
        status = ['Pending', 'Usable result', 'Unamplified', 'Usable result', 'Usable result'][i % 5]
        reviewed = status == 'Usable result' and i % 3 != 0
        decision = ['Maintained', 'Substituted', 'Switched'][i % 3] if reviewed else None
        con.execute('UPDATE episodes SET referred_at=?,sample_at=?,sample_type=?,dbs_reason=?,lab_owner=4,status=?,report_at=?,amplified=?,failure_reason=?,reviewed_at=?,reviewer=?,decision=?,decision_at=?,decision_notes=?,implemented_at=?,implementation_notes=? WHERE patient_id=?', ('2026-10-01T09:00:00+00:00', '2026-10-03T09:00:00+00:00', sample_type, 'Demo: plasma transport unavailable' if sample_type == 'DBS' else '', status, '2026-10-15T09:00:00+00:00' if status != 'Pending' else None, 0 if status == 'Unamplified' else 1 if status == 'Usable result' else None, 'Demo: amplification unsuccessful; repeat sample needed' if status == 'Unamplified' else '', '2026-10-20T09:00:00+00:00' if reviewed else None, 5 if reviewed else None, decision, '2026-10-20T09:00:00+00:00' if reviewed else None, 'Synthetic workflow example' if reviewed else '', '2026-10-23T09:00:00+00:00' if reviewed and i % 2 else None, 'Demo implementation confirmed' if reviewed and i % 2 else '', pid))
