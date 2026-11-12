// Shown wherever the signed-in role can read but not change a step.
const WHO = {
  edit_patient_record: 'a nurse or counsellor', record_iac: 'a nurse or counsellor', record_psychosocial: 'a nurse or counsellor',
  request_dr_test: 'laboratory staff', refer_on_clinical_indication: 'laboratory staff', record_lab: 'laboratory staff',
  interpret_resistance: 'laboratory staff', review_and_decide: 'a clinician', implement_decision: 'the assigned nurse or counsellor',
  record_follow_up: 'a nurse or counsellor', discuss: 'a clinician',
};
export default function ViewOnly({ action, children }) {
  return <p className="notice info view-only"><b>View only.</b> {children || `This step is recorded by ${WHO[action] || 'another role'}.`}</p>;
}
