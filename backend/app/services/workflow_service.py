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
    queued=None
    with connect() as con:
        patient, episode = load_patient(con, user, patient_id)
        from ..core.permissions import any_facility
        if not any_facility(user) and user['facility'] != patient['facility']:
            raise DomainError('Cross-facility access is read-only. Edit patients at your assigned facility.', 403)
        if patient.get('archived_at'):raise DomainError('Restore this record before editing clinical data',409)
        operation(con, user, patient, episode, data)
        from .eligibility_service import refresh
        refresh(con, patient_id)
        lab_change=operation.__name__ in ('record_result','record_mutations')
        if operation.__name__=='update_fields':
            from .record_service import section
            lab_change=any(section(key)=='Laboratory' for key in data.get('fields',{}))
        if lab_change:
            from .auto_interpretation import enqueue
            queued=enqueue(con,user,patient_id)
    if queued:
        from .auto_interpretation import schedule
        schedule(patient_id)
    return {'ok': True}
