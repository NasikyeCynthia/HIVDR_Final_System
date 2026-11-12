ROLES = ('admin', 'nurse', 'counsellor', 'lab', 'clinician')
MISSING = {'', 'unknown', 'not applicable', 'not tested', 'not performed', 'left blank', 'none', 'pending', 'not applicable - no dr review simulated'}
# Only patient fields actually present in the surveillance profile are required.
# Adherence comes from IAC pill counts; a psychosocial assessment is also required (MoH patient page).
PROFILE_FIELDS = ('name', 'age', 'sex', 'facility', 'regimen', 'treatment_line', 'viral_load', 'adherence')
CLINICAL_FIELDS = {'name', 'age', 'sex', 'regimen', 'treatment_line', 'viral_load', 'adherence', 'notes'}
