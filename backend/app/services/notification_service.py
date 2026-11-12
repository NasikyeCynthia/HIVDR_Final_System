from datetime import date


def notifications(patients, follow_ups=None):
    """Outstanding work per patient. follow_ups: {patient_id: next due date (ISO)}."""
    follow_ups = follow_ups or {}
    today = date.today().isoformat()
    result = []
    for patient in patients:
        reasons = []
        eligibility = (patient.get('eligibility') or {}).get('status')
        risk = patient.get('risk') or {}
        if eligibility == 'eligible' and not patient.get('referred_at'):
            reasons.append('Eligible for a DR test (MoH/WHO criteria): laboratory to request the test')
        if risk.get('flagged') and eligibility != 'eligible' and not patient.get('referred_at'):
            reasons.append('High risk of drug resistance: complete IAC and the repeat viral load')
        if patient.get('amplified') == 1 and patient.get('discussion_status') == 'Pending' and patient['missing_pre']:
            reasons.append('Missing profile: ' + ', '.join(patient['missing_pre']))
        if patient['status'] in ('Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'):
            reasons.append('Unsuccessful laboratory test: ' + (patient['failure_reason'] or 'reason missing') + ' — request a repeat sample')
        if patient.get('vl_pending'):
            reasons.append('Viral load result awaited: record it on the Viral load tab when it returns')
        if patient.get('repeat_requested_at') and patient['status'] == 'Not collected':
            reasons.append('Repeat sample requested by the laboratory (' + (patient.get('repeat_reason') or 'no reason given')
                           + '): bring the patient back for a new sample')
        lab = patient.get('lab') or {}
        if lab.get('stage') == 'At DR laboratory' and patient.get('received_at') and (date.today() - date.fromisoformat(patient['received_at'][:10])).days > 30:
            contact = f" — contact {patient.get('officer_name')} ({patient.get('officer_phone')})" if patient.get('officer_phone') else ''
            reasons.append('DR result overdue (over 30 days)' + contact)
        if patient['status'] == 'Usable result' and patient.get('discussion_status') == 'Pending' and not patient['decision']:
            reasons.append('Usable result awaits clinician review')
        if patient['decision'] and not patient['implemented_at']:
            reasons.append('Approved decision awaits implementation')
        due = follow_ups.get(patient['id'])
        if due and due <= today:
            reasons.append(f'6-monthly follow-up assessment due ({due})')
        if reasons:
            result.append({'patient_id': patient['id'], 'patient_name': patient['name'], 'owner': patient['owner_name'], 'reasons': reasons})
    return result
