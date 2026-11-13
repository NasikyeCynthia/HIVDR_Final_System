import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {useAuth,useCan} from '../../contexts/AuthContext.jsx';
import {operationsService} from '../../services/operationsService.js';
import {decisionService} from '../../services/decisionService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import {formatDate} from '../../utils/format.js';
import {ACTION_LABELS,reviewStage} from '../../utils/discussion.js';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';
import ViewOnly from '../common/ViewOnly.jsx';
const COLORS={1:'green',2:'yellow',3:'yellow',4:'red',5:'red'};

export function SuggestionCard({suggestion}) {
  return <Card title="System-generated draft action" subtitle="System draft using Stanford resistance evidence; clinician approval required.">
    {suggestion?.action?<p><Badge color={suggestion.action==='Maintained'?'green':'yellow'}>{ACTION_LABELS[suggestion.action]}</Badge>{suggestion.alternative&&<span> · alternative for review: {ACTION_LABELS[suggestion.alternative]}</span>}</p>:<p className="notice info">{suggestion?'Individual clinician assessment required; no automatic action was selected.':'A draft will appear after Stanford analysis is saved.'}</p>}
    {(suggestion?.rationale||[]).map(r=><p key={r}>{r}</p>)}
    {suggestion?.current_regimen?.length>0&&<div className="table-wrap"><table><thead><tr><th>Drug in regimen ({suggestion.regimen})</th><th>Resistance evidence</th></tr></thead><tbody>{suggestion.current_regimen.map(d=><tr key={d.drug}><td>{d.drug}</td><td><Badge color={COLORS[d.level]||''}>{d.label}</Badge></td></tr>)}</tbody></table></div>}
    {suggestion?.fully_active_drugs?.length>0&&<p className="tiny">Drugs reported susceptible or with potential low-level resistance: {suggestion.fully_active_drugs.join(', ')}. This list does not define a complete replacement regimen.</p>}
    {suggestion&&<p className="tiny muted">Evidence: {suggestion.evidence_source||'No interpretation'} · Draft rule version: {suggestion.version}. {suggestion.notice}</p>}
    <Link className="text-link tiny" to="/help#clinical-decision-support">Sources and review guidance</Link>
  </Card>;
}

export default function DecisionForm({patient,onSaved}) {
  const {user}=useAuth(),can=useCan(),approval=usePatientAction(onSaved);
  const suggestion=patient.suggestion,stage=reviewStage(patient);
  const [decision,setDecision]=useState(''),[regimen,setRegimen]=useState(''),[notes,setNotes]=useState(''),[acknowledged,setAcknowledged]=useState(false);
  useEffect(()=>{setDecision(suggestion?.action||'');setRegimen(suggestion?.action==='Maintained'?patient.regimen||'':'');setNotes('');setAcknowledged(false);},[patient.id,patient.version,patient.data_version,suggestion?.action]);
  const ready=Boolean(patient.interpretation)&&stage.key!=='processing'&&patient.pre_complete&&!(patient.approval_blockers?.length);
  function approve(event) {
    event.preventDefault();
    approval.run(()=>decisionService.approve(patient.id,{decision,recommended_regimen:regimen,decision_notes:notes,evidence_reviewed:acknowledged,expected_version:patient.version,expected_data_version:patient.data_version}),
      'Clinician approval saved. The nurse or counsellor can now record implementation.');
  }
  return <>
    {(!patient.decision||suggestion)&&<SuggestionCard suggestion={suggestion}/>}
    <Card title="Clinician approval" subtitle="Approve the draft or record a different clinical decision. No treatment change is implemented automatically.">
      <Feedback error={approval.error} success={approval.success}/>
      {patient.decision?<><p className="notice info"><b>{ACTION_LABELS[patient.decision]||patient.decision}</b> approved by {patient.reviewer_name||'the clinician'} · {formatDate(patient.decision_at)}</p><dl className="resistance-context"><div><dt>Approved regimen</dt><dd>{patient.recommended_regimen||'Not recorded'}</dd></div><div><dt>Clinical rationale</dt><dd>{patient.decision_notes||'Not recorded'}</dd></div><div><dt>Implementation</dt><dd>{patient.implemented_at?'Recorded':'Awaiting nurse / counsellor'}</dd></div></dl></>:<>
        {patient.approval_blockers?.length>0&&<div className="notice"><b>Approval prerequisites</b><ul>{patient.approval_blockers.map(b=><li key={b}>{b}</li>)}</ul></div>}
        {!can('review_and_decide',patient)?<ViewOnly action="review_and_decide"/>:<form onSubmit={approve}><fieldset disabled={!ready||approval.busy}><div className="form-grid">
          <div className="field"><label htmlFor="clinical-action">Decision for approval</label><select id="clinical-action" required value={decision} onChange={e=>{const next=e.target.value;setDecision(next);if(next==='Maintained')setRegimen(patient.regimen||'');else if(decision==='Maintained')setRegimen('');}}><option value="">Select the clinician decision…</option>{Object.entries(ACTION_LABELS).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></div>
          <div className="field"><label htmlFor="clinical-regimen">Regimen approved by the clinician</label><input id="clinical-regimen" required maxLength={300} value={regimen} onChange={e=>setRegimen(e.target.value)} placeholder="Enter the complete regimen"/></div>
          <div className="field full"><label htmlFor="clinical-rationale">Clinical rationale (explain any change from the draft)</label><textarea id="clinical-rationale" required minLength={20} maxLength={5000} value={notes} onChange={e=>setNotes(e.target.value)}/></div>
          <label className="checkbox field full"><input type="checkbox" required checked={acknowledged} onChange={e=>setAcknowledged(e.target.checked)}/>I reviewed the latest Stanford interpretation, treatment/exposure history, adherence and relevant clinical context.</label>
        </div><div className="form-actions"><button className="btn">{approval.busy?'Saving approval…':decision===suggestion?.action?'Approve draft action':'Approve clinician decision'}</button></div></fieldset></form>}
      </>}
    </Card>
    {user.role==='clinician'&&(patient.decision||patient.reviewed_at)&&<Card title="Amend a reviewed decision"><p>The previous decision and implementation history are retained when the episode is reopened.</p><form onSubmit={e=>{e.preventDefault();approval.run(()=>operationsService.amend(patient.id,new FormData(e.currentTarget).get('reason')),'Audited amendment opened.');}}><label htmlFor="amend-reason">Reason for amendment</label><textarea id="amend-reason" name="reason" required minLength={10}/><button className="btn secondary" disabled={approval.busy}>Open amendment</button></form></Card>}
  </>;
}
