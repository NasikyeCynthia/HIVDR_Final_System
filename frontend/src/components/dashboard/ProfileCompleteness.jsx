import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
import { percentage } from '../../utils/format.js';
export default function ProfileCompleteness({ patients }) {
  const reviewed = patients.filter(p => p.reviewed_at);
  const rows = [
    ['Pre-discussion', patients.filter(p => p.pre_complete).length, patients.length, 'missing-pre'],
    ['Post-discussion', reviewed.filter(p => p.post_complete).length, reviewed.length, 'missing-post'],
  ];
  return <Card title="Profile completeness" subtitle="Click to find missing fields and responsible care workers"><div className="completeness">{rows.map(([title, count, total, filter]) => <Link className="complete-box" key={title} to={`/patients?filter=${filter}`}><span>{title}</span><strong>{percentage(count, total)}<span>% complete</span></strong><div className="track"><div className="fill" style={{ width: `${percentage(count, total)}%` }} /></div><span>{count} of {total} {title === 'Post-discussion' ? 'reviewed' : 'registered'} records</span></Link>)}</div></Card>;
}
