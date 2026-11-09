import json
import re
from ..models.constants import MISSING
from ..core.database import now
from .audit_service import audit

def present(value):
    return value is not None and str(value).strip().lower() not in MISSING

def number(value):
    if not present(value):
        return None
    match = re.search('\\d+(?:\\.\\d+)?', str(value).replace(',', ''))
    return float(match.group()) if match else None

def line_number(value):
    value = str(value or '').lower()
    for n, word in ((1, 'first'), (2, 'second'), (3, 'third')):
        if word in value or re.search('\\b' + str(n) + '(?:st|nd|rd)?\\b', value):
            return n
    return None

def import_rows(con, rows, source, user):
    added = skipped = 0
    for index, raw in enumerate(rows):
        if None in raw:
            raise ValueError('CSV contains rows with extra cells; import cancelled.')
        raw = {str(k): str(v or '').strip() for k, v in raw.items()}
        external_id = raw.get('Patient No.') or raw.get('patient_id')
        if not external_id:
            raise ValueError(f'Row {index + 2}: Patient No. is required.')
        vl = number(raw.get('VL Leading to DR'))
        adherence = number(raw.get('Adherence (%)') or raw.get('Simulated Adherence (%)'))
        if adherence is not None and (not 0 <= adherence <= 100):
            raise ValueError(f'Row {index + 2}: adherence must be 0–100.')
        owner = 2 if source == 'synthetic' and index % 7 else None
        facility = 'Demo Facility' if source == 'synthetic' else raw.get('Facility') or 'Unassigned'
        cur = con.execute('INSERT OR IGNORE INTO patients(external_id,source,name,facility,age,sex,regimen,treatment_line,viral_load,adherence,assigned_to,original_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (external_id, source, f'Synthetic patient {external_id}' if source == 'synthetic' else f'Patient {external_id}', facility, number(raw.get('Age(yrs)')), raw.get('sex'), raw.get('ART at sample collection(ART@VL@DR)'), line_number(raw.get('Treatment Line at Sample collection')), vl, adherence, owner, json.dumps(raw), now()))
        if cur.rowcount:
            pid = cur.lastrowid
            con.execute('INSERT INTO episodes(patient_id) VALUES(?)', (pid,))
            added += 1
        else:
            skipped += 1
    audit(con, user, 'import', source, after={'added': added, 'skipped': skipped})
    return {'added': added, 'skipped': skipped}
