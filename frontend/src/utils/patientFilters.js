import { eligibilityStatus } from './eligibility.js';
export function matchesFilter(patient, filter) {
  if (filter.startsWith('elig:')) return eligibilityStatus(patient) === filter.slice(5);
  if (filter.startsWith('risk:')) return (patient.risk?.category || 'Not assessed') === filter.slice(5);
  if (filter === 'flagged') return Boolean(patient.risk?.flagged);
  if (filter.startsWith('line:')) return String(patient.treatment_line ?? '') === filter.slice(5);
  if (filter.startsWith('regimen:')) return String(patient.regimen ?? '') === filter.slice(8);
  switch (filter) {
    case 'eligible': return eligibilityStatus(patient) === 'eligible' || Boolean(patient.referred_at || patient.sample_at);
    case 'missing-pre': return patient.amplified === 1 && patient.discussion_status === 'Pending' && !patient.pre_complete;
    case 'missing-post': return patient.discussion_status === 'Done' && !patient.post_complete;
    case 'discussion-pending': return patient.discussion_status === 'Pending';
    case 'discussion-done': return patient.discussion_status === 'Done';
    case 'discussion-blank': return !patient.discussion_status;
    case 'failed': return ['Unamplified', 'Sequencing failed'].includes(patient.status);
    case 'returned': return ['Rejected', 'Deferred'].includes(patient.status);
    case 'lab-problem': return Boolean(patient.lab?.flag_count);
    case 'at-dr-lab': return patient.cphl_outcome === 'Referred to DR lab' && patient.status === 'Pending';
    case 'awaiting-receipt': return patient.status === 'Pending' && !patient.cphl_outcome;
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
    case 'amplified-blank': return patient.amplified == null;
    case 'sample-type-blank': return !patient.sample_type;
    case 'pending': return patient.status === 'Pending';
    case 'Plasma': case 'DBS': return patient.sample_type === filter;
    case 'Maintained': case 'Substituted': case 'Switched': return patient.decision === filter;
    default: return true;
  }
}
