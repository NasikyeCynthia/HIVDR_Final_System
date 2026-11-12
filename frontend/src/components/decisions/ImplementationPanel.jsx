import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import { decisionService } from '../../services/decisionService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import { formatDate } from '../../utils/format.js';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';
import ViewOnly from '../common/ViewOnly.jsx';

// MoH HIVDR database flow (Participants' Manual §7.3.3–7.3.4): start on the assigned regimen,
// then assess every 6 months (viral load, regimen, psychosocial issues, care status).
const CARE = ['Alive and on treatment', 'Lost to follow up/Dropped out of care (90  days)', 'Lost (<90 days)', 'Transferred out', 'Stopped', 'Died'];
const today = () => new Date().toISOString().slice(0, 10);

export default function ImplementationPanel({ patient, followUps = [], onSaved }) {
  const { user } = useAuth();
  const { users = [] } = useWorkspace();
  const can = useCan();
  const impl = usePatientAction(onSaved);
  const follow = usePatientAction(onSaved);
  const assignedOk = Boolean(user.edit_any_facility) || !patient.assigned_to || patient.assigned_to === user.id;
  const canImplement = can('implement_decision', patient) && assignedOk;
  const changesRegimen = ['Switched', 'Substituted'].includes(patient.decision);
  const due = followUps.find(f => !f.assessed_on);
  const done = followUps.filter(f => f.assessed_on);
  const submit = (fn, action, message, numeric = []) => event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    for (const k of numeric) data[k] = data[k] === '' ? null : Number(data[k]);
    for (const k of Object.keys(data)) if (data[k] === '') delete data[k];
    action.run(() => fn(patient.id, data), message);
  };
  if (!patient.decision) return <Card title="Implementation"><p className="muted">No committee decision has been approved yet. Once a clinician approves it, it appears here for the nurse or counsellor to implement.</p></Card>;
  return <>
    <Card title="Approved decision to implement" subtitle={`Approved ${formatDate(patient.decision_at)}`}>
      <div className="detail-list"><div><label>Decision</label><Badge color={patient.decision === 'Maintained' ? 'green' : 'red'}>{patient.decision}</Badge></div><div><label>Intended regimen</label>{patient.recommended_regimen}</div><div><label>Rationale</label>{patient.decision_notes}</div><div><label>Care worker</label>{users.find(u => u.id === patient.assigned_to)?.name || 'Unassigned — the first nurse/counsellor to record implementation is assigned'}</div></div>
    </Card>
    <Card title="Implementation">
      <Feedback error={impl.error} success={impl.success} />
      {patient.implemented_at ? <div className="detail-list"><div><label>Started</label>{formatDate(patient.start_date)}</div><div><label>Regimen started</label>{patient.started_regimen || patient.regimen}</div><div><label>Previous regimen stopped</label>{formatDate(patient.previous_stop_date)}</div><div><label>How it was confirmed</label>{patient.implementation_notes}</div></div> : <>
        {!canImplement && <ViewOnly action="implement_decision" />}
        {canImplement && <form onSubmit={submit(decisionService.implement, impl, 'Implementation recorded; 6-month follow-up scheduled')}><div className="form-grid">
          {changesRegimen ? <>
            <div className="field"><label>Date started on the new regimen<input name="start_date" type="date" max={today()} required /></label></div>
            <div className="field"><label>Regimen actually started<input name="started_regimen" defaultValue={patient.recommended_regimen} required maxLength="300" /></label></div>
            <div className="field"><label>Previous regimen stop date<input name="previous_stop_date" type="date" max={today()} /></label></div>
          </> : <div className="field"><label>Date the decision was communicated<input name="start_date" type="date" max={today()} defaultValue={today()} /></label></div>}
          <div className="field full"><label>How implementation was confirmed (e.g. drugs dispensed, patient counselled)<textarea name="implementation_notes" required maxLength="5000" /></label></div>
        </div><div className="form-actions"><button className="btn">{changesRegimen ? 'Record start on regimen' : 'Confirm decision received'}</button></div></form>}
      </>}
    </Card>
    {patient.implemented_at && <Card title="6-monthly follow-up" subtitle={due ? `Next assessment due ${formatDate(due.due_date)}${due.due_date <= today() ? ' — due now' : ''}` : 'No assessment scheduled'}>
      <Feedback error={follow.error} success={follow.success} />
      {done.length > 0 && <div className="table-wrap"><table><thead><tr><th>Due</th><th>Assessed</th><th>Viral load</th><th>Care status</th><th>Psychosocial issues</th></tr></thead><tbody>
        {done.map(f => <tr key={f.id}><td>{formatDate(f.due_date)}</td><td>{formatDate(f.assessed_on)}</td><td>{f.vl_copies == null ? '—' : `${f.vl_copies.toLocaleString()} (${formatDate(f.vl_date)})`}{f.vl_copies != null && <div><Badge color={f.vl_copies >= 1000 ? 'red' : 'green'}>{f.vl_copies >= 1000 ? 'Not suppressed' : 'Suppressed'}</Badge></div>}</td><td>{f.care_status}</td><td>{f.psychosocial || '—'}</td></tr>)}
      </tbody></table></div>}
      {due && (can('record_follow_up', patient) ? <form onSubmit={submit(decisionService.followUp, follow, 'Follow-up assessment recorded', ['vl_copies'])}><div className="form-grid">
        <div className="field"><label>Care status<select name="care_status" defaultValue={CARE[0]}>{CARE.map(c => <option key={c}>{c}</option>)}</select></label></div>
        <div className="field"><label>Most recent viral load (copies/mL)<input name="vl_copies" type="number" min="0" /></label></div>
        <div className="field"><label>Viral load date<input name="vl_date" type="date" max={today()} /></label></div>
        <div className="field"><label>Regimen at assessment<input name="regimen" defaultValue={patient.started_regimen || patient.regimen || ''} /></label></div>
        <div className="field full"><label>Psychosocial issues<input name="psychosocial" maxLength="3000" /></label></div>
        <div className="field full"><label>Clinical status / notes<input name="clinical_status" maxLength="3000" /></label></div>
      </div><div className="form-actions"><button className="btn">Record assessment</button></div></form> : <ViewOnly action="record_follow_up" />)}
    </Card>}
  </>;
}
