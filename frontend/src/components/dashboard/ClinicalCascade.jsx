import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
// Committee decisions and their implementation (follows the process cascade).
export default function ClinicalCascade({ patients }) {
  const decided = patients.filter(p => p.decision);
  const n = decided.length;
  const rows = [
    ['Maintained', decided.filter(p => p.decision === 'Maintained').length, 'Maintained', '#27845d'],
    ['Switched', decided.filter(p => p.decision === 'Switched').length, 'Switched', '#c34351'],
    ['Substituted', decided.filter(p => p.decision === 'Substituted').length, 'Substituted', '#d8a510'],
    ['Implemented', decided.filter(p => p.implemented_at).length, 'implemented', '#4361a6'],
  ];
  return <Card title="Clinical cascade" subtitle={`${n.toLocaleString()} committee decisions`}>
    <div className="cascade">{rows.map(([label, count, filter, color]) => <Link key={label} className="bar-col" to={`/patients?filter=${filter}`} aria-label={`${label}: ${count} patients`}><span className="bar-value">{count}</span><span className="bar-percent">{n ? Math.round(count / n * 100) : 0}%</span><span className="bar" style={{ height: `${Math.max(1, n ? count / n * 155 : 1)}px`, background: color }} /></Link>)}</div>
    <div className="bar-labels">{rows.map(([label]) => <span key={label}>{label}</span>)}</div>
    <p className="tiny muted">Percentages are of all committee decisions. Implemented = the nurse/counsellor has recorded that the decision was carried out.</p>
    <Link className="text-link" to="/patients?filter=awaiting-implementation">{decided.filter(p => !p.implemented_at).length} decisions await implementation →</Link>
  </Card>;
}
