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
        if patient['status'] == 'Usable result' and not patient['decision']:
            if patient.get('interpretation_status')=='failed':reasons.append('Stanford analysis failed: retry the saved laboratory result')
            elif patient.get('interpretation_status')=='needs_input':reasons.append('Laboratory input needed for Stanford: review the genotype or sequence')
            elif patient.get('has_interpretation'):reasons.append('Usable result awaits clinician review')
            elif patient.get('interpretation_status') not in ('pending','running'):reasons.append('Stanford analysis required for the saved laboratory result')
        if patient['decision'] and not patient['implemented_at']:
            reasons.append('Approved decision awaits implementation')
        due = follow_ups.get(patient['id'])
        if due and due <= today:
            reasons.append(f'6-monthly follow-up assessment due ({due})')
        if reasons:
            result.append({'patient_id': patient['id'], 'patient_name': patient['name'], 'patient_no':patient.get('external_id'),
                           'source':(patient.get('dataset_source') or 'original') if patient.get('source')=='manual' else patient.get('source'),
                           'facility':patient.get('facility'),'occurred_at':patient.get('decision_at') or patient.get('report_at') or patient.get('created_at'),
                           'owner': patient['owner_name'], 'reasons': reasons})
    return result
