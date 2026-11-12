import { ELIGIBILITY, eligibilityStatus } from '../../utils/eligibility.js';
export default function Badge({ children, color = '' }) {
  return <span className={`badge ${color}`}>{children}</span>;
}
export function EligibilityBadge({ patient }) {
  const status = eligibilityStatus(patient);
  return <Badge color={ELIGIBILITY[status]?.color || ''}>{ELIGIBILITY[status]?.label || status}</Badge>;
}
