import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
import { percentage } from '../../utils/format.js';
export default function ProfileCompleteness({ patients }) {
  const preDiscussion = patients.filter(p => p.amplified === 1 && p.discussion_status === 'Pending');
  const postDecision = patients.filter(p => p.discussion_status === 'Done');
  const rows = [
    ['Pre-discussion', preDiscussion.filter(p => p.pre_complete).length, preDiscussion.length, 'missing-pre'],
    ['Post-decision', postDecision.filter(p => p.post_complete).length, postDecision.length, 'missing-post'],
  ];
  return <Card title="Profile completeness" subtitle="Select either stage to open the patients who need follow-up"><div className="completeness">{rows.map(([title, count, total, filter]) => <Link className="complete-box" key={title} to={`/patients?filter=${filter}`}><span>{title}</span><strong>{percentage(count, total)}<span>% complete</span></strong><div className="track"><div className="fill" style={{ width: `${percentage(count, total)}%` }} /></div><span>{count} of {total} {title === 'Post-decision' ? 'decided' : 'amplified, pending discussion'} records</span></Link>)}</div></Card>;
}
