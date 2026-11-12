import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
import { ELIGIBILITY, ELIGIBILITY_ORDER, eligibilityStatus } from '../../utils/eligibility.js';
// DR-test eligibility status as a simple list (MoH/WHO criteria).
export default function EligibilityChart({ patients }) {
  const counts = ELIGIBILITY_ORDER.map(status => [status, patients.filter(p => eligibilityStatus(p) === status).length]);
  return <Card title="DR-test eligibility" subtitle="MoH/WHO: 2 consecutive VL ≥1000 after 3 good IAC sessions">
    {counts.map(([status, n]) => <Link key={status} className="clinical-row" to={`/patients?filter=elig:${status}`}><span>{ELIGIBILITY[status].label}</span><span /><b>{n.toLocaleString()}</b></Link>)}
  </Card>;
}
