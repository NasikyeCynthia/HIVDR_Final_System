// Use the existing completeness flags for the patient's current review stage.
export const PROFILE_STATES = {
  'before-incomplete': { label: 'Before review · incomplete', color: 'red' },
  'after-incomplete': { label: 'After review · incomplete', color: 'orange' },
  'before-complete': { label: 'Before review · complete', color: 'blue' },
  'after-complete': { label: 'After review · complete', color: 'green' },
};

export function profileState(patient) {
  const reviewed = Boolean(patient.reviewed_at || patient.decision || patient.discussion_status === 'Done');
  const complete = reviewed ? patient.post_complete : patient.pre_complete;
  return `${reviewed ? 'after' : 'before'}-${complete ? 'complete' : 'incomplete'}`;
}
