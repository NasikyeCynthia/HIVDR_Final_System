import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
export default function LaboratoryOverview({ patients }) {
  const metrics = [
    ['Plasma', patients.filter(p => p.sample_type === 'Plasma').length, 'Plasma'],
    ['DBS', patients.filter(p => p.sample_type === 'DBS').length, 'DBS'],
    ['Unsuccessful', patients.filter(p => ['Unamplified', 'Sequencing failed'].includes(p.status)).length, 'failed'],
    ['Amplified', patients.filter(p => p.amplified === 1).length, 'amplified'],
    ['Pending', patients.filter(p => p.status === 'Pending').length, 'pending'],
  ];
  return <Card title="Laboratory overview" subtitle="Sample type and result availability are separate"><div className="lab-breakdown wrap">{metrics.map(([title, value, filter]) => <Link className="lab-item" key={title} to={`/patients?filter=${filter}`}><b>{value}</b><span>{title}</span></Link>)}</div></Card>;
}
