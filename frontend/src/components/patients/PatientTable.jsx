import { Link } from 'react-router-dom';
import Badge, { RiskBadge } from '../common/Badge.jsx';
export default function PatientTable({ patients, tab = 'overview' }) {
  return <div className="table-wrap"><table><thead><tr><th>Patient / ID</th><th>Regimen</th><th>Risk assessment</th><th>Laboratory</th><th>Profile / care worker</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    <td className="patient-cell">{patient.name}<small>{patient.external_id} · {patient.source}</small></td>
    <td>{patient.regimen || 'Not recorded'}<div className="tiny muted">{patient.facility}</div></td>
    <td><RiskBadge risk={patient.risk} /><div className="tiny muted">{patient.risk.total == null ? 'Incomplete' : `${patient.risk.total} points`}</div></td>
    <td><Badge color={patient.status === 'Usable result' ? 'green' : patient.status === 'Unamplified' ? 'red' : ''}>{patient.status}</Badge><div className="tiny muted">{patient.sample_type || 'No sample'}</div></td>
    <td><Badge color={patient.pre_complete ? 'green' : 'yellow'}>{patient.pre_complete ? 'Complete' : `${patient.missing_pre.length} fields missing`}</Badge><div className="tiny muted">{patient.owner_name || 'Unassigned — needs allocation'}</div></td>
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=${tab}`}>Open →</Link></td>
  </tr>)}</tbody></table>{!patients.length && <div className="empty">No records match this view.</div>}</div>;
}
