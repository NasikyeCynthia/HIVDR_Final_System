"""Single source of truth for who may change what. Everyone signed in may view
records at their facility (or all facilities if granted); only these roles may edit."""
from .errors import DomainError

ACTIONS = {
    'register_patient': ('nurse', 'counsellor'),
    'edit_patient_record': ('nurse', 'counsellor'),
    'record_iac': ('nurse', 'counsellor'),
    'record_psychosocial': ('nurse', 'counsellor'),
    # DR-test requests are made by laboratory staff, so one named person is accountable for the
    # sample and its results, and records why a previous test failed.
    'request_dr_test': ('lab',),
    'refer_on_clinical_indication': ('lab',),
    'record_lab': ('lab',),
    'interpret_resistance': ('lab',),
    'discuss': ('clinician',),
    'review_and_decide': ('clinician',),
    'implement_decision': ('nurse', 'counsellor'),
    'record_follow_up': ('nurse', 'counsellor'),
    'manage_accounts': ('admin',),
    'manage_data': ('admin',),
}

LABELS = {
    'register_patient': 'Register patients', 'edit_patient_record': 'Complete and correct patient records',
    'record_iac': 'Record IAC sessions', 'record_psychosocial': 'Record psychosocial assessments',
    'request_dr_test': 'Request a DR test', 'refer_on_clinical_indication': 'Request a DR test outside the automated criteria',
    'record_lab': 'Record samples and laboratory results', 'interpret_resistance': 'Run Stanford interpretation',
    'discuss': 'Write in the committee discussion', 'review_and_decide': 'Review and approve committee decisions',
    'implement_decision': 'Implement approved decisions', 'record_follow_up': 'Record 6-monthly follow-up',
    'manage_accounts': 'Manage staff accounts', 'manage_data': 'Import data and change the active dataset',
}


def can(user, action):
    return user.get('role') in ACTIONS[action]


def require(user, action, patient=None):
    if not can(user, action):
        roles = ' or '.join(ACTIONS[action])
        raise DomainError(f'View only: {LABELS[action].lower()} requires a {roles} account.', 403)
    if patient is not None and user.get('role') != 'admin' and user.get('facility') != patient.get('facility'):
        raise DomainError('View only: changes must be made by staff at the patient’s facility.', 403)


def for_user(user):
    return sorted(action for action, roles in ACTIONS.items() if user.get('role') in roles)
