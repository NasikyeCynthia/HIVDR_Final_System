import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
export default function DiscussionStatus({patients}) {
 const total=patients.length;
 const rows=[
  ['Pending',patients.filter(p=>p.discussion_status==='Pending').length,'discussion-pending','#d8a510'],
  ['Done',patients.filter(p=>p.discussion_status==='Done').length,'discussion-done','#27845d'],
  ['Blank',patients.filter(p=>!p.discussion_status).length,'discussion-blank','#8b9aa2'],
 ];
 return <Card title="Discussion status" subtitle="From the dataset’s decision category: pending, completed, or blank"><div className="cascade">{rows.map(([label,count,filter,color])=><Link key={label} className="bar-col" to={`/patients?filter=${filter}`} aria-label={`${label}: ${count} patients`}><span className="bar-value">{count}</span><span className="bar-percent">{total?Math.round(count/total*100):0}%</span><span className="bar" style={{height:`${Math.max(1,total?count/total*155:1)}px`,background:color}}/></Link>)}</div><div className="bar-labels">{rows.map(([label])=><span key={label}>{label}</span>)}</div><p className="tiny muted">Pending uses “Pending Discussion”; Done means a committee decision is recorded. Blank means no discussion category is recorded. Select a bar to see patient IDs and names.</p><Link className="text-link" to="/patients?filter=awaiting-implementation">{patients.filter(p=>p.decision&&!p.implemented_at).length} decisions await implementation →</Link></Card>;
}
