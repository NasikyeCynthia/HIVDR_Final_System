import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
import { percentage } from '../../utils/format.js';
export default function ClinicalCascade({ patients }) {
  const usable = patients.filter(p => p.status === 'Usable result').length;
  const reviewed = patients.filter(p => p.reviewed_at).length;
  const decisions = patients.filter(p => p.decision).length;
  const implemented = patients.filter(p => p.implemented_at).length;
  return <Card title="Clinical follow-through" subtitle="Usable results through to implemented care">
    {[['Usable results', usable, 'usable'], ['Reviewed', reviewed, 'reviewed'], ['Decision recorded', decisions, 'decision'], ['Implemented', implemented, 'implemented']].map(([label, count, filter]) => <Link className="clinical-row" to={`/patients?filter=${filter}`} key={label}><span>{label}</span><div className="track"><div className="fill" style={{ width: `${percentage(count, usable)}%` }} /></div><b>{count}</b></Link>)}
    <div className="notice info" style={{ marginTop: 25 }}>{usable - reviewed} await review · {decisions - implemented} decisions await implementation</div>
  </Card>;
}
