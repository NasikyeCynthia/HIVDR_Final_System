export function matchesFilter(patient, filter) {
  if (filter.startsWith('line:')) return String(patient.treatment_line ?? '') === filter.slice(5);
  if (filter.startsWith('regimen:')) return String(patient.regimen ?? '') === filter.slice(8);
  switch (filter) {
    case 'eligible': return patient.risk.eligible || Boolean(patient.referred_at);
    case 'missing-pre': return !patient.pre_complete;
    case 'missing-post': return patient.reviewed_at && !patient.post_complete;
    case 'failed': return ['Unamplified', 'Sequencing failed'].includes(patient.status);
    case 'awaiting-review': return patient.status === 'Usable result' && !patient.reviewed_at;
    case 'awaiting-implementation': return patient.decision && !patient.implemented_at;
    case 'usable': return patient.status === 'Usable result';
    case 'referred': return Boolean(patient.referred_at);
    case 'collected': return Boolean(patient.sample_at);
    case 'received': return Boolean(patient.report_at);
    case 'reviewed': return Boolean(patient.reviewed_at);
    case 'decision': return Boolean(patient.decision);
    case 'implemented': return Boolean(patient.implemented_at);
    case 'amplified': return patient.amplified === 1;
    case 'pending': return patient.status === 'Pending';
    case 'Plasma': case 'DBS': return patient.sample_type === filter;
    case 'Maintained': case 'Substituted': case 'Switched': return patient.decision === filter;
    case 'Incomplete': case 'Rule unresolved': case 'High': case 'Intermediate': case 'Moderate': case 'Low': return patient.risk.category === filter;
    default: return true;
  }
}
