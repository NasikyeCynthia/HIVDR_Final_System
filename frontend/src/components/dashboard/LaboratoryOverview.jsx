import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
// Dataset status (sample type and amplification) plus the staged sample pipeline (MoH Participants' Manual §5.2, §7.3.1).
export default function LaboratoryOverview({ patients }) {
  const dataset = [
    ['Plasma samples', patients.filter(p => p.sample_type === 'Plasma').length, 'Plasma'],
    ['DBS samples', patients.filter(p => p.sample_type === 'DBS').length, 'DBS'],
    ['Sample type blank', patients.filter(p => !p.sample_type).length, 'sample-type-blank'],
    ['Amplified · result (1)', patients.filter(p => p.amplified === 1).length, 'amplified'],
    ['Not amplified · no result (0)', patients.filter(p => p.amplified === 0).length, 'failed'],
    ['Amplified value blank', patients.filter(p => p.amplified == null).length, 'amplified-blank'],
  ];
  const pipeline = [
    ['Collected, not yet at CPHL', patients.filter(p => p.status === 'Pending' && !p.cphl_outcome).length, 'awaiting-receipt'],
    ['At DR laboratory', patients.filter(p => p.lab?.stage === 'At DR laboratory').length, 'at-dr-lab'],
    ['Rejected or deferred at CPHL', patients.filter(p => ['Rejected', 'Deferred'].includes(p.status)).length, 'returned'],
    ['Sample quality problems', patients.filter(p => p.lab?.flag_count).length, 'lab-problem'],
  ];
  const tile = ([title, value, filter]) => <Link className="lab-item" key={title} to={`/patients?filter=${filter}`}><b>{value}</b><span>{title}</span></Link>;
  return <Card title="Laboratory dataset status" subtitle="Sample type and amplification are separate fields; blank values are counted explicitly">
    <div className="lab-breakdown wrap">{dataset.map(tile)}</div>
    <h3 style={{ marginTop: 20 }}>Sample pipeline</h3>
    <div className="lab-breakdown wrap">{pipeline.map(tile)}</div>

  </Card>;
}
