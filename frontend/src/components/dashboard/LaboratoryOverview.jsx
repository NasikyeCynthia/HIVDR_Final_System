import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
export default function LaboratoryOverview({ patients }) {
  const metrics = [
    ['Plasma samples', patients.filter(p => p.sample_type === 'Plasma').length, 'Plasma'],
    ['DBS samples', patients.filter(p => p.sample_type === 'DBS').length, 'DBS'],
    ['Sample type blank', patients.filter(p => !p.sample_type).length, 'sample-type-blank'],
    ['Amplified · result (1)', patients.filter(p => p.amplified === 1).length, 'amplified'],
    ['Not amplified · no result (0)', patients.filter(p => p.amplified === 0).length, 'failed'],
    ['Amplified value blank', patients.filter(p => p.amplified == null).length, 'amplified-blank'],
  ];
  return <Card title="Laboratory dataset status" subtitle="Sample type and amplification are separate fields; blank values are counted explicitly"><div className="lab-breakdown wrap">{metrics.map(([title, value, filter]) => <Link className="lab-item" key={title} to={`/patients?filter=${filter}`}><b>{value}</b><span>{title}</span></Link>)}</div><p className="tiny muted">P = Plasma; D or DBS = DBS. Amplified 1 means a result is recorded; 0 means no result; blank means no result value is recorded.</p></Card>;
}
