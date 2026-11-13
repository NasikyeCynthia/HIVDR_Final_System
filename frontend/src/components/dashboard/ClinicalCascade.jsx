import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
// Committee decisions and their implementation (follows the process cascade).
export default function ClinicalCascade({ patients }) {
  const decided = patients.filter(p => p.decision);
  const n = decided.length;
  const rows = [
    ['Maintained', decided.filter(p => p.decision === 'Maintained').length, 'Maintained', 'linear-gradient(180deg,#34b27b,#1b7a52)'],
    ['Switched', decided.filter(p => p.decision === 'Switched').length, 'Switched', 'linear-gradient(180deg,#e0566a,#a3243a)'],
    ['Substituted', decided.filter(p => p.decision === 'Substituted').length, 'Substituted', 'linear-gradient(180deg,#f2a93b,#c27612)'],
    ['Implemented', decided.filter(p => p.implemented_at).length, 'implemented', 'linear-gradient(180deg,#9b6ad9,#5e3a9e)'],
  ];
  return <Card className="accent-clinical" title="Clinical cascade" subtitle={`${n.toLocaleString()} committee decisions`}>
    <div className="cascade">{rows.map(([label, count, filter, color]) => <Link key={label} className="bar-col" to={`/patients?filter=${filter}`} aria-label={`${label}: ${count} patients`}><span className="bar-value">{count}</span><span className="bar-percent">{n ? Math.round(count / n * 100) : 0}%</span><span className="bar" style={{ height: `${Math.max(1, n ? count / n * 155 : 1)}px`, background: color }} /></Link>)}</div>
    <div className="bar-labels">{rows.map(([label]) => <span key={label}>{label}</span>)}</div>
    <Link className="text-link" to="/patients?filter=awaiting-implementation">{decided.filter(p => !p.implemented_at).length} decisions await implementation →</Link>
  </Card>;
}
