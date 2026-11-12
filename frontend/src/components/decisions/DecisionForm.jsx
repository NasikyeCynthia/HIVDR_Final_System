import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import { operationsService } from '../../services/operationsService.js';
import { decisionService } from '../../services/decisionService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import { formatDate } from '../../utils/format.js';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import FormField from '../common/FormField.jsx';
import Feedback from '../common/Feedback.jsx';
import ViewOnly from '../common/ViewOnly.jsx';

const LEVEL_COLOR = { 1: 'green', 2: 'green', 3: 'yellow', 4: 'red', 5: 'red' };

export function SuggestionCard({ suggestion }) {
  if (!suggestion) return null;
  return <Card title="Suggested committee action" subtitle="Decision support from the Stanford levels for the current regimen, WHO 2021 and MoH guidance">
    {suggestion.action ? <p><Badge color={suggestion.action === 'Maintained' ? 'green' : 'red'}>{suggestion.action}</Badge>{suggestion.alternative && <span className="tiny muted"> · alternative: {suggestion.alternative}</span>}{suggestion.followed !== undefined && <span className="tiny muted"> · {suggestion.followed ? 'followed by the clinician' : 'clinician chose differently'}</span>}</p> : null}
    {(suggestion.rationale || []).map(r => <p key={r}>{r}</p>)}
    {suggestion.current_regimen?.length > 0 && <div className="table-wrap"><table><thead><tr><th>Drug in current regimen ({suggestion.regimen})</th><th>Resistance</th></tr></thead><tbody>
      {suggestion.current_regimen.map(d => <tr key={d.drug}><td>{d.drug}</td><td><Badge color={LEVEL_COLOR[d.level] || ''}>{d.label}</Badge></td></tr>)}</tbody></table></div>}
    {suggestion.fully_active_drugs?.length > 0 && <p className="tiny">Predicted fully active (susceptible or potential low-level): {suggestion.fully_active_drugs.join(', ')}</p>}
    <p className="tiny muted">{suggestion.notice} Evidence: {suggestion.evidence_source || 'none recorded'}. This rule set agreed with 78.5% of 11,105 past Ugandan committee decisions.</p>
  </Card>;
}

export default function DecisionForm({ patient, onSaved }) {
  const { user } = useAuth();
  const can = useCan();
  const approval = usePatientAction(onSaved);
  const canDecide = can('review_and_decide', patient);
  const suggestion = patient.suggestion;
  function approve(event) { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); approval.run(() => decisionService.approve(patient.id, data), 'Committee decision approved; it is now visible to the nurse/counsellor for implementation'); }
  return <>
    <SuggestionCard suggestion={suggestion} />
    <Card title="Committee decision" subtitle="Approved by a clinician; the nurse or counsellor then implements it">
      <Feedback error={approval.error} success={approval.success} />
      {patient.decision ? <><div className="notice info">Approved decision: <b>{patient.decision}</b> · {formatDate(patient.decision_at)}</div><div className="detail-list"><div><label>Intended regimen</label>{patient.recommended_regimen || 'Missing'}</div><div><label>Committee rationale</label>{patient.decision_notes || 'Missing'}</div></div></> : <>
        {patient.approval_blockers?.length > 0 && <div className="notice"><b>A decision cannot be approved yet</b><ul>{patient.approval_blockers.map(b => <li key={b}>{b}</li>)}</ul></div>}
        {!canDecide && <ViewOnly action="review_and_decide" />}
        {canDecide && <form onSubmit={approve}><fieldset disabled={patient.status !== 'Usable result' || !patient.pre_complete || approval.busy}><div className="form-grid">
          <FormField label="Committee decision" name="decision"><select id="decision" name="decision" required defaultValue={suggestion?.action || ''}><option value="">Choose decision…</option>{['Maintained', 'Substituted', 'Switched'].map(value => <option key={value}>{value}</option>)}</select></FormField>
          <FormField label="Intended regimen" name="recommended_regimen" required defaultValue={suggestion?.action === 'Maintained' ? patient.regimen || '' : ''} />
          <FormField label="Committee rationale (explain if different from the suggestion)" name="decision_notes" full><textarea id="decision_notes" name="decision_notes" required maxLength="5000" /></FormField>
        </div><div className="form-actions"><button className="btn">Approve decision</button></div></fieldset></form>}
      </>}
    </Card>
    {user.role === 'clinician' && user.facility === patient.facility && (patient.decision || patient.reviewed_at) && <Card title="Correct a reviewed record"><p className="tiny muted">Reopening archives the previous decision and implementation state. The record returns to review so laboratory evidence and the committee decision can be corrected.</p><form onSubmit={e => { e.preventDefault(); const reason = new FormData(e.currentTarget).get('reason'); approval.run(() => operationsService.amend(patient.id, reason), 'Amendment opened; previous state retained'); }}><label htmlFor="amend-reason">Reason for correction</label><textarea id="amend-reason" name="reason" required minLength={10} /><button className="btn secondary" disabled={approval.busy} style={{ marginTop: 12 }}>Open audited amendment</button></form></Card>}
  </>;
}
