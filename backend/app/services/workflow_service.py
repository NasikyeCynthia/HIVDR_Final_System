from ..core.database import connect
from ..core.errors import DomainError
from .patient_service import allowed

def load_patient(con, user, patient_id):
    row = con.execute('SELECT * FROM patients WHERE id=?', (patient_id,)).fetchone()
    if row is None or not allowed(user, row):
        raise DomainError('Patient not found', 404)
    episode = con.execute('SELECT * FROM episodes WHERE patient_id=?', (patient_id,)).fetchone()
    return dict(row), dict(episode)

def change_patient(patient_id, user, data, operation):
    with connect() as con:
        patient, episode = load_patient(con, user, patient_id)
        if user['role'] != 'admin' and user['facility'] != patient['facility']:
            raise DomainError('Cross-facility access is read-only. Edit patients at your assigned facility.', 403)
        if patient.get('archived_at'):raise DomainError('Restore this record before editing clinical data',409)
        operation(con, user, patient, episode, data)
        from .eligibility_service import refresh
        refresh(con, patient_id)
    return {'ok': True}
