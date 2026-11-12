// Display vocabulary for the MoH DR-testing eligibility statuses (backend: eligibility_service.py).
export const ELIGIBILITY = {
  eligible: { label: 'Eligible for DR testing', color: 'red', chart: '#c34351' },
  needs_documentation: { label: 'Criteria met, documentation incomplete', color: 'yellow', chart: '#d8a510' },
  not_yet: { label: 'Not yet eligible', color: 'teal', chart: '#4361a6' },
  in_process: { label: 'Referred / in DR process', color: 'green', chart: '#27845d' },
  suppressed: { label: 'Suppressed — not eligible', color: '', chart: '#9aa8ae' },
  insufficient_data: { label: 'Insufficient data', color: '', chart: '#c9d1d5' },
};
export const ELIGIBILITY_ORDER = ['eligible', 'needs_documentation', 'not_yet', 'in_process', 'suppressed', 'insufficient_data'];
export const eligibilityStatus = patient => patient?.eligibility?.status || 'insufficient_data';
export const eligibilityLabel = status => ELIGIBILITY[status]?.label || status;
