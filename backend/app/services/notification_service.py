def notifications(patients):
    result = []
    for patient in patients:
        reasons = []
        if patient['missing_pre']:
            reasons.append('Missing profile: ' + ', '.join(patient['missing_pre']))
        if patient['status'] in ('Unamplified', 'Sequencing failed'):
            reasons.append('Unsuccessful laboratory test: ' + (patient['failure_reason'] or 'reason missing'))
        if patient['status'] == 'Usable result' and not patient['reviewed_at']:
            reasons.append('Usable result awaits clinician review')
        if patient['decision'] and not patient['implemented_at']:
            reasons.append('Approved decision awaits implementation')
        if reasons:
            result.append({'patient_id': patient['id'], 'patient_name': patient['name'], 'owner': patient['owner_name'], 'reasons': reasons})
    return result
