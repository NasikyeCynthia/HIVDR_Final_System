import { Link } from 'react-router-dom';
import Badge, { EligibilityBadge } from '../common/Badge.jsx';
import { RiskBadge } from '../risk/RiskScoreCard.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
function displayDatasetValue(field, value) {
  if (field === 'Sample Type') {
    const code = String(value || '').trim().toUpperCase();
    if (code === 'P' || code === 'PLASMA') return 'P · Plasma';
    if (code === 'D' || code === 'DBS') return code === 'D' ? 'D · DBS' : 'DBS';
    return 'No sample recorded';
  }
  if (field === 'amplified') {
    if (String(value).trim() === '1') return '1 · Result recorded';
    if (String(value).trim() === '0') return '0 · No result';
    return 'Blank · No result';
  }
  return value || '—';
}

export default function PatientTable({ patients, tab = 'overview', datasetView = false, columns = [], recordFields = {} }) {
  const { user } = useAuth();
  const isNurse = false; // all roles may view every column; editing is per role
  if (datasetView) return <div className="table-wrap"><table><thead><tr><th>Patient ID / name</th>{columns.map(field=><th key={field}>{field}</th>)}<th>Profile completeness</th><th>Risk / DR-test eligibility</th>{!isNurse&&<th>Committee decision / implementation</th>}<th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    <td className="patient-cell">{patient.external_id}<small>{patient.name}</small></td>
    {columns.map(field=><td key={field}>{displayDatasetValue(field, recordFields[patient.id]?.[field])}</td>)}
    <td><Badge color={patient.pre_complete ? 'green' : 'yellow'}>{patient.pre_complete ? 'Complete' : `Incomplete · ${patient.missing_pre?.length || 0} fields`}</Badge></td>
    <td><RiskBadge risk={patient.risk} /><div style={{ marginTop: 5 }}><EligibilityBadge patient={patient} /></div></td>
    {!isNurse&&<td>{patient.decision || patient.discussion_status || 'Blank'}<div><Badge color={patient.implemented_at ? 'green' : patient.discussion_status === 'Pending' ? 'yellow' : patient.discussion_status === 'Done' ? 'green' : ''}>{patient.implemented_at ? 'Implemented' : patient.discussion_status || 'Blank'}</Badge></div></td>}
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=${patient.pre_complete ? 'record' : 'profile'}`}>{patient.pre_complete ? 'Open →' : 'Complete profile →'}</Link></td>
  </tr>)}</tbody></table>{!patients.length && <div className="empty">No records match this view.</div>}</div>;
  const empty = !patients.length && <div className="empty">No records match this view.</div>;
  const id = patient => <td className="patient-cell">{patient.external_id}<small>{patient.name}</small></td>;
  // Risk assessment: only the variables used for risk and DR-test eligibility.
  if (tab === 'risk') return <div className="table-wrap"><table><thead><tr><th>Patient ID / name</th><th>Viral load</th><th>Adherence</th><th>Treatment line</th><th>Risk score</th><th>DR-test eligibility</th><th>Resistance estimate</th><th>Time to failure</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    {id(patient)}
    <td>{patient.viral_load == null ? '—' : Number(patient.viral_load).toLocaleString()}</td>
    <td>{patient.adherence == null ? '—' : `${patient.adherence}%`}</td>
    <td>{patient.treatment_line ? `Line ${patient.treatment_line}` : '—'}</td>
    <td><RiskBadge risk={patient.risk} />{patient.risk?.total != null && <div className="tiny muted">{patient.risk.total} points</div>}</td>
    <td><EligibilityBadge patient={patient} /></td>
    <td>{patient.risk?.ml == null ? '—' : <Badge color={patient.risk.ml >= 0.64 ? 'red' : ''}>{Math.round(patient.risk.ml * 100)}%</Badge>}</td>
    <td>{Array.isArray(patient.ttf) ? `${patient.ttf[0].toFixed(0)} months` : '—'}</td>
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=risk`}>Open →</Link></td>
  </tr>)}</tbody></table>{empty}</div>;
  // Laboratory: only sample and result variables.
  const cleanMutations = text => [...new Set(String(text || '').split(/[;,•]/).map(t => t.replace(/\(\d+(\.\d+)?%\)/g, '').trim()).filter(t => t && !/^none$/i.test(t)))].join(', ');
  if (tab === 'laboratory') return <div className="table-wrap"><table><thead><tr><th>Patient ID / name</th><th>Sample</th><th>Testing lab</th><th>Stage / outcome</th><th>Result</th><th>Days</th><th>Lab officer</th><th /></tr></thead><tbody>{patients.map(patient => {
    const waiting = patient.status === 'Pending' && patient.received_at ? Math.floor((Date.now() - new Date(patient.received_at)) / 86400000) : null;
    const failed = ['Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'].includes(patient.status);
    const mutations = cleanMutations(patient.mutations);
    const action = patient.eligibility?.status === 'eligible' && !patient.referred_at ? ['risk', 'Request DR test →'] : patient.status === 'Not collected' ? ['laboratory', 'Record sample →'] : failed ? ['laboratory', 'Request repeat →'] : ['laboratory', patient.status === 'Pending' ? 'Update →' : 'View →'];
    return <tr key={patient.id}>
      {id(patient)}
      <td>{patient.sample_type || '—'}{patient.sample_type === 'DBS' && <div className="tiny muted">{patient.dbs_reason || 'Reason not recorded'}</div>}</td>
      <td>{patient.dr_lab || (patient.sample_type ? { Plasma: 'JCRC', DBS: 'UVRI' }[patient.sample_type] + ' (planned)' : '—')}</td>
      <td><Badge color={patient.status === 'Usable result' ? 'green' : failed ? 'red' : ''}>{patient.status === 'Usable result' ? 'Amplified' : patient.status}</Badge><div className="tiny muted">{patient.lab?.stage}</div>{patient.lab?.flag_count ? <div><Badge color="red">{patient.lab.flag_count} quality problem(s)</Badge></div> : null}</td>
      <td className="result-cell">{patient.status === 'Usable result' ? (mutations ? <span title={mutations}>{mutations.length > 70 ? mutations.slice(0, 70) + '…' : mutations}</span> : <span className="muted">No mutations listed</span>) : failed ? <span>{patient.failure_reason || 'Reason missing'}</span> : patient.repeat_requested_at && patient.status === 'Not collected' ? <span>Repeat requested: {patient.repeat_reason || '—'}</span> : '—'}</td>
      <td>{waiting != null ? <Badge color={waiting > 30 ? 'red' : 'yellow'}>{waiting} at lab</Badge> : patient.report_at && (patient.received_at || patient.sample_at) ? <span>{Math.max(0, Math.round((new Date(patient.report_at) - new Date(patient.received_at || patient.sample_at)) / 86400000))} days<div className="tiny muted">from {patient.received_at ? 'CPHL receipt' : 'collection'} to result</div></span> : '—'}</td>
      <td>{patient.officer_name || patient.lab_owner_name || '—'}{patient.officer_phone ? <div className="tiny muted">{patient.officer_phone}</div> : null}</td>
      <td><Link className="text-link" to={`/patients/${patient.id}?tab=${action[0]}`}>{action[1]}</Link></td>
    </tr>; })}</tbody></table>{empty}</div>;
  // Discussion: only what the committee needs to decide and follow up.
  if (tab === 'discussion') return <div className="table-wrap"><table><thead><tr><th>Patient ID / name</th><th>Regimen</th><th>Laboratory result</th><th>Profile</th><th>Decision</th><th>Implementation</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    {id(patient)}
    <td>{patient.regimen || '—'}<div className="tiny muted">{patient.treatment_line ? `Line ${patient.treatment_line}` : ''}</div></td>
    <td><Badge color={patient.status === 'Usable result' ? 'green' : ''}>{patient.status}</Badge></td>
    <td><Badge color={patient.pre_complete ? 'green' : 'yellow'}>{patient.pre_complete ? 'Complete' : `Incomplete · ${patient.missing_pre?.length || 0}`}</Badge></td>
    <td>{patient.decision ? <Badge color={patient.decision === 'Maintained' ? 'green' : 'red'}>{patient.decision}</Badge> : <span className="muted">{patient.discussion_status || 'Not discussed'}</span>}</td>
    <td>{patient.decision ? <Badge color={patient.implemented_at ? 'green' : 'yellow'}>{patient.implemented_at ? 'Implemented' : 'Awaiting'}</Badge> : '—'}</td>
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=discussion`}>Open →</Link></td>
  </tr>)}</tbody></table>{empty}</div>;
  return <div className="table-wrap"><table><thead><tr><th>Patient / ID</th><th>Regimen</th><th>Risk / DR-test eligibility</th>{!isNurse&&<th>Laboratory</th>}<th>Profile / care worker</th><th /></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}>
    <td className="patient-cell">{patient.name}<small>{patient.external_id} · {patient.source}</small></td>
    <td>{patient.regimen || 'Not recorded'}<div className="tiny muted">{patient.facility}</div></td>
    <td><RiskBadge risk={patient.risk} /><div style={{ marginTop: 5 }}><EligibilityBadge patient={patient} /></div></td>
    {!isNurse&&<td><Badge color={patient.status === 'Usable result' ? 'green' : ['Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'].includes(patient.status) ? 'red' : ''}>{patient.status}</Badge><div className="tiny muted">{patient.lab?.stage || patient.sample_type || 'No sample'}{patient.lab?.flag_count ? ` · ${patient.lab.flag_count} problem(s)` : ''}</div></td>}
    <td><Badge color={patient.pre_complete ? 'green' : 'yellow'}>{patient.pre_complete ? 'Complete' : `Incomplete · ${patient.missing_pre?.length || 0} fields`}</Badge><div className="tiny muted">{patient.owner_name || 'Unassigned — needs allocation'}</div></td>
    <td><Link className="text-link" to={`/patients/${patient.id}?tab=${!patient.pre_complete ? 'profile' : tab}`}>{!patient.pre_complete ? 'Complete profile →' : tab === 'laboratory' ? 'Enter / update result →' : 'Open →'}</Link></td>
  </tr>)}</tbody></table>{!patients.length && <div className="empty">No records match this view.</div>}</div>;
}
