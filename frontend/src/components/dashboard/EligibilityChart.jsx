import PieChart from './PieChart.jsx';
import { ELIGIBILITY, ELIGIBILITY_ORDER, eligibilityStatus } from '../../utils/eligibility.js';
export default function EligibilityChart({ patients }) {
  const items = ELIGIBILITY_ORDER.map(status => ({ label: ELIGIBILITY[status].label, filter: `elig:${status}`, value: patients.filter(p => eligibilityStatus(p) === status).length, color: ELIGIBILITY[status].chart }));
  return <PieChart title="DR-testing eligibility" subtitle="MoH/WHO: 2 consecutive VL ≥1000 after 3 good IAC sessions" items={items} />;
}
