import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
import { percentage } from '../../utils/format.js';
export default function ProcessCascade({ patients }) {
  const total = patients.length;
  const stages = [
    ['Registered', total, ''], ['Referred', patients.filter(p => p.referred_at).length, 'referred'],
    ['Sample collected', patients.filter(p => p.sample_at).length, 'collected'],
    ['Report received', patients.filter(p => p.report_at).length, 'received'],
    ['Usable result', patients.filter(p => p.status === 'Usable result').length, 'usable'],
  ];
  const gaps = [
    ['Referred, not collected', patients.filter(p => p.referred_at && !p.sample_at).length, patients.filter(p => p.referred_at).length],
    ['Collected, no report', patients.filter(p => p.sample_at && !p.report_at).length, patients.filter(p => p.sample_at).length],
    ['Report, no usable result', patients.filter(p => p.report_at && p.status !== 'Usable result').length, patients.filter(p => p.report_at).length],
  ];
  return <Card title="Process cascade" subtitle="Recorded milestones · click a bar to inspect">
    <div className="cascade">{stages.map(([label, count, filter]) => <Link className="bar-col" key={label} to={`/patients?filter=${filter}`} aria-label={`${label}: ${count}`}><span className="bar-value">{count}</span><span className="bar-percent">{percentage(count, total)}%</span><span className="bar" style={{ height: `${Math.max(1, percentage(count, total)) * 1.55}px` }} /></Link>)}</div>
    <div className="bar-labels">{stages.map(([label]) => <span key={label}>{label}</span>)}</div>
    <div className="cascade-gaps">{gaps.map(([label, count, denominator]) => <div key={label}><span>{label}</span><b>{count} <small>({percentage(count, denominator)}%)</small></b></div>)}</div>
    <p className="tiny muted">Bars use registered records as the denominator. Gaps use their preceding milestone. High-risk eligibility awaits the overall scoring rule; sample type is tracked separately.</p>
  </Card>;
}
