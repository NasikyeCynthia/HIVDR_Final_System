import { Link } from 'react-router-dom';
import Badge, { RiskBadge } from '../common/Badge.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
export default function PatientTable({ patients, tab = 'overview', datasetView = false, columns = [], recordFields = {} }) {
  const { user } = useAuth();
  const isNurse = user.role === 'nurse';
  if (datasetView) return <div className="table-wrap"><table><thead><tr><th>Patient ID / name</th>{columns.map(field=><th key={field}>{field}</th>)}<th>Profile completeness</th><th>Risk assessment</th>{!isNurse&&<th>Committee decision / implementation</th>}<th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    <td className="patient-cell">{patient.external_id}<small>{patient.name}</small></td>
    {columns.map(field=><td key={field}>{recordFields[patient.id]?.[field] || <span className="muted">—</span>}</td>)}
    <td><Badge color={patient.pre_complete ? 'green' : 'yellow'}>{patient.pre_complete ? 'Complete' : `Incomplete · ${patient.missing_pre?.length || 0} fields`}</Badge></td>
    <td><RiskBadge risk={patient.risk} /><div className="tiny muted">{patient.risk.total == null ? `${patient.risk.known_total||0}+ points (partial)` : `${patient.risk.total} points`}</div></td>
    {!isNurse&&<td>{patient.decision || (patient.reviewed_at ? 'Committee review' : 'No decision recorded')}<div><Badge color={patient.implemented_at ? 'green' : patient.decision ? 'yellow' : ''}>{patient.implemented_at ? 'Implemented' : patient.decision ? 'Awaiting implementation' : patient.reviewed_at ? 'Decision pending' : 'Not decided'}</Badge></div></td>}
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=${patient.pre_complete ? 'record' : 'profile'}`}>{patient.pre_complete ? 'Open →' : 'Complete profile →'}</Link></td>
  </tr>)}</tbody></table>{!patients.length && <div className="empty">No records match this view.</div>}</div>;
  if (tab === 'risk') return <div className="table-wrap"><table><thead><tr><th>Patient ID / name</th><th>ARV regimen</th><th>Treatment line</th><th>Viral load</th><th>Risk assessment</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    <td className="patient-cell">{patient.external_id}<small>{patient.name}</small></td>
    <td>{patient.regimen || 'Not recorded'}</td>
    <td>{patient.treatment_line ? `Line ${patient.treatment_line}` : 'Not recorded'}</td>
    <td>{patient.viral_load == null ? 'Not recorded' : Number(patient.viral_load).toLocaleString()}</td>
    <td><RiskBadge risk={patient.risk} /><div className="tiny muted">{patient.risk.total == null ? `${patient.risk.known_total||0}+ points (partial)` : `${patient.risk.total} points`}</div></td>
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=risk`}>Open →</Link></td>
  </tr>)}</tbody></table>{!patients.length && <div className="empty">No records match this view.</div>}</div>;
  return <div className="table-wrap"><table><thead><tr><th>Patient / ID</th><th>Regimen</th><th>Risk assessment</th>{!isNurse&&<th>Laboratory</th>}<th>Profile / care worker</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    <td className="patient-cell">{patient.name}<small>{patient.external_id} · {patient.source}</small></td>
    <td>{patient.regimen || 'Not recorded'}<div className="tiny muted">{patient.facility}</div></td>
    <td><RiskBadge risk={patient.risk} /><div className="tiny muted">{patient.risk.total == null ? `${patient.risk.known_total||0}+ points (partial)` : `${patient.risk.total} points`}</div></td>
    {!isNurse&&<td><Badge color={patient.status === 'Usable result' ? 'green' : patient.status === 'Unamplified' ? 'red' : ''}>{patient.status}</Badge><div className="tiny muted">{patient.sample_type || 'No sample'}</div></td>}
    <td><Badge color={patient.pre_complete ? 'green' : 'yellow'}>{patient.pre_complete ? 'Complete' : `Incomplete · ${patient.missing_pre?.length || 0} fields`}</Badge><div className="tiny muted">{patient.owner_name || 'Unassigned — needs allocation'}</div></td>
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=${!patient.pre_complete ? 'profile' : tab}`}>{!patient.pre_complete ? 'Complete profile →' : tab === 'laboratory' ? 'Enter / update result →' : 'Open →'}</Link></td>
  </tr>)}</tbody></table>{!patients.length && <div className="empty">No records match this view.</div>}</div>;
}
