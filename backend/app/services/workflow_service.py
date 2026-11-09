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
        operation(con, user, patient, episode, data)
    return {'ok': True}
