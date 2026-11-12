import { useEffect, useState } from 'react';
import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import ViewOnly from '../common/ViewOnly.jsx';
import { labService } from '../../services/labService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';

// Staged HIVDR sample workflow: collection → dispatch → CPHL receipt → DR-lab result.
// Rules are enforced by the backend (app/services/lab_service.py); this form only collects input.
const STAGES = ['Not collected', 'Collected at facility', 'In transit', 'At CPHL', 'At DR laboratory', 'Result released'];
const LEVEL = { error: 'red', warning: 'yellow', info: '' };
const when = v => v ? new Date(v).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
const day = v => v ? new Date(v).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
const nowLocal = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16); };
const numbers = (data, keys) => { for (const k of keys) data[k] = data[k] === '' || data[k] == null ? null : Number(data[k]); return data; };

function Field({ label, children, full }) { return <div className={`field ${full ? 'full' : ''}`}><label>{label}{children}</label></div>; }

export default function LaboratoryForm({ patient, onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  const [options, setOptions] = useState(null);
  const [kind, setKind] = useState('Plasma');
  const [outcome, setOutcome] = useState('Referred to DR lab');
  const [result, setResult] = useState('Usable result');
  useEffect(() => { labService.options().then(setOptions).catch(() => setOptions(null)); }, []);
  const lab = patient.lab || { stage: 'Not collected', flags: [], tat: {} };
  const can = useCan();
  const canEdit = can('record_lab', patient) && !patient.reviewed_at && !patient.decision;
  const max = nowLocal();
  const stageIndex = STAGES.indexOf(lab.stage);
  const submit = (fn, message, numeric = []) => event => {
    event.preventDefault();
    const data = numbers(Object.fromEntries(new FormData(event.currentTarget)), numeric);
    for (const k of Object.keys(data)) if (data[k] === '') delete data[k];
    action.run(() => fn(patient.id, data), message);
  };
  const eligibility = patient.eligibility || {};
  const indication = patient.referred_at || eligibility.eligible || eligibility.sample_due;

  return <>
    <Card title="HIVDR sample" subtitle={`Attempt ${lab.attempt}${lab.dr_lab ? ` · DR laboratory: ${lab.dr_lab}` : ''}`}>
      <div className="lab-stages" aria-label="Sample progress">{STAGES.map((s, i) => <span key={s} className={i < stageIndex ? 'done' : i === stageIndex ? 'current' : ''}>{s}</span>)}</div>
      {lab.stage === 'Returned to facility' && <p className="notice error">{patient.status === 'Rejected' ? 'Rejected at CPHL' : 'Deferred to facility'}: {patient.cphl_reason || patient.failure_reason}</p>}
      {lab.flags.map((f, i) => <p key={i} className={`notice ${f.level === 'info' ? 'info' : f.level === 'error' ? 'error' : ''}`}><Badge color={LEVEL[f.level]}>{f.level === 'error' ? 'Problem' : f.level === 'warning' ? 'Check' : 'Note'}</Badge> {f.text} <span className="tiny muted">({lab.sources?.[f.source]})</span></p>)}
      <div className="detail-list">
        <div><label>Laboratory officer in charge</label>{lab.officer?.name || '—'}{lab.officer?.phone ? <div><a className="text-link" href={`tel:${lab.officer.phone}`}>{lab.officer.phone}</a></div> : null}</div>
        <div><label>Sample type</label>{patient.sample_type || '—'}{patient.dbs_reason ? <div className="tiny muted">{patient.dbs_reason}</div> : null}</div>
        <div><label>Collected</label>{when(patient.sample_at)}</div>
        <div><label>Plasma separated</label>{when(patient.centrifuged_at)}</div>
        <div><label>Tubes / whole blood / storage</label>{[patient.tubes != null && `${patient.tubes} PPT`, patient.whole_blood_ml != null && `${patient.whole_blood_ml} mL`, patient.storage_temp].filter(Boolean).join(' · ') || '—'}</div>
        <div><label>Dispatched (hub pick-up)</label>{day(patient.dispatched_at)}</div>
        <div><label>Received at CPHL</label>{day(patient.received_at)}{patient.plasma_volume_ml != null ? ` · ${patient.plasma_volume_ml} mL plasma` : ''}</div>
        <div><label>Tested / released</label>{day(patient.tested_at)} / {day(patient.report_at)}</div>
        <div><label>Turnaround</label>{lab.tat.lab_days != null ? `${lab.tat.lab_days} days from CPHL receipt` : lab.tat.waiting_days != null ? `Waiting ${lab.tat.waiting_days} days` : '—'}{lab.tat.total_days != null ? <div className="tiny muted">{lab.tat.total_days} days from collection</div> : null}</div>
        <div><label>Outcome</label>{patient.status}{patient.failure_reason && patient.status !== 'Usable result' ? <div className="tiny muted">{patient.failure_reason}</div> : null}</div>
        <div><label>Mutations recorded</label>{patient.mutations || '—'}</div>
      </div>
      {!canEdit && (patient.reviewed_at || patient.decision ? <p className="notice info" style={{ marginTop: 16 }}>This episode has been reviewed; the laboratory record is locked. Use the amendment workflow to correct it.</p> : <ViewOnly action="record_lab" />)}
      <Feedback error={action.error} success={action.success} />
    </Card>

    {canEdit && options && lab.stage === 'Not collected' && <Card title="1. Record collection" subtitle="Plasma is the recommended sample: 5–8 mL whole blood in two PPT tubes, separated within 6 hours">
      {!indication && <p className="notice">No DR-test indication yet. {eligibility.next_step}</p>}
      {patient.repeat_requested_at && <p className="notice info">Repeat sample requested {day(patient.repeat_requested_at)}.</p>}
      <form onSubmit={submit(labService.collection, 'Collection recorded', ['tubes', 'whole_blood_ml'])}><fieldset disabled={action.busy || !indication}><div className="form-grid">
        <Field label="Sample type"><select name="sample_type" value={kind} onChange={e => setKind(e.target.value)}><option>Plasma</option><option>DBS</option></select></Field>
        <Field label="Collected (date and time)"><input name="collected_at" type="datetime-local" max={max} required /></Field>
        <Field label="Laboratory officer in charge"><input name="officer_name" defaultValue={user.name} required maxLength="200" /></Field>
        <Field label="Officer phone (for delayed results)"><input name="officer_phone" type="tel" required placeholder="07XX XXX XXX" maxLength="30" /></Field>
        {kind === 'Plasma' ? <>
          <Field label="Centrifuged (date and time)"><input name="centrifuged_at" type="datetime-local" max={max} required /></Field>
          <Field label="Number of PPT tubes"><input name="tubes" type="number" min="0" max="6" defaultValue="2" /></Field>
          <Field label="Whole blood collected (mL)"><input name="whole_blood_ml" type="number" min="0" max="30" step="0.5" /></Field>
          <Field label="Storage until pick-up"><select name="storage_temp" defaultValue={options.storage[0]}>{options.storage.map(s => <option key={s}>{s}</option>)}</select></Field>
        </> : <>
          <Field label="Why DBS instead of plasma" full><select name="dbs_reason" required defaultValue=""><option value="" disabled>Choose a reason…</option>{options.dbs_reasons.map(s => <option key={s}>{s}</option>)}</select></Field>
          <Field label="Explanation" full><input name="dbs_note" maxLength="3000" /></Field>
        </>}
      </div><div className="form-actions"><button className="btn">Record collection</button></div></fieldset></form>
    </Card>}

    {canEdit && options && lab.stage === 'Collected at facility' && <Card title="2. Record hub pick-up" subtitle="Target: picked up within 2 days, kept at 4–8 °C">
      <form onSubmit={submit(labService.dispatch, 'Dispatch recorded')}><fieldset disabled={action.busy}><div className="form-grid">
        <Field label="Picked up / dispatched"><input name="dispatched_at" type="date" max={max.slice(0, 10)} required /></Field>
      </div><div className="form-actions"><button className="btn">Record dispatch</button></div></fieldset></form>
    </Card>}

    {canEdit && options && ['Collected at facility', 'In transit'].includes(lab.stage) && <Card title="3. Record receipt at CPHL" subtitle={`Viable samples go to ${patient.sample_type === 'DBS' ? 'UVRI (DBS)' : 'JCRC (plasma)'}; others are deferred or rejected`}>
      {eligibility.status === 'suppressed' && <p className="notice">The latest recorded viral load is not above 1000 copies/mL. If that is the repeat VL, defer as “Below threshold for HIVDR testing”.</p>}
      <form onSubmit={submit(labService.receipt, 'CPHL receipt recorded', ['plasma_volume_ml'])}><fieldset disabled={action.busy}><div className="form-grid">
        <Field label="Received at CPHL"><input name="received_at" type="date" max={max.slice(0, 10)} required /></Field>
        <Field label="Plasma volume received (mL)"><input name="plasma_volume_ml" type="number" min="0" max="20" step="0.1" /></Field>
        <Field label="Decision"><select name="outcome" value={outcome} onChange={e => setOutcome(e.target.value)}><option>Referred to DR lab</option><option>Deferred to facility</option><option>Rejected</option></select></Field>
        {outcome !== 'Referred to DR lab' && <Field label="Reason"><select name="reason" required defaultValue=""><option value="" disabled>Choose…</option>{(outcome === 'Rejected' ? options.rejection_reasons : options.deferral_reasons).map(s => <option key={s}>{s}</option>)}</select></Field>}
        {outcome !== 'Referred to DR lab' && <Field label="Explanation" full><input name="note" maxLength="3000" /></Field>}
      </div><div className="form-actions"><button className="btn">Record receipt</button></div></fieldset></form>
    </Card>}

    {canEdit && options && lab.stage === 'At DR laboratory' && <Card title="4. Record DR-lab result" subtitle={`Turnaround target ${options.tat_days} days from CPHL receipt`}>
      <form onSubmit={submit(labService.result, 'Result recorded')}><fieldset disabled={action.busy}><div className="form-grid">
        <Field label="Outcome"><select name="outcome" value={result} onChange={e => setResult(e.target.value)}><option>Usable result</option><option>Unamplified</option><option>Sequencing failed</option></select></Field>
        <Field label="Tested on"><input name="tested_at" type="date" max={max.slice(0, 10)} required /></Field>
        <Field label="Result released on"><input name="released_at" type="date" max={max.slice(0, 10)} required /></Field>
        {result !== 'Usable result' && <Field label="Reason the test was unsuccessful" full><textarea name="failure_reason" required maxLength="3000" /></Field>}
        {result === 'Usable result' && <>
          <Field label="Mutations from the genotype report, with gene (e.g. RT:M184V RT:K103N IN:R263K)" full><textarea name="mutations" maxLength="15000" placeholder="Write “none” if the report lists no mutations" /></Field>
          <Field label="Or paste the pol nucleotide sequence (FASTA)" full><textarea name="sequence" maxLength="100000" /></Field>
          <p className="tiny muted field full">HIVDR testing in Uganda is genotypic: the lab sequences the pol gene (protease, reverse transcriptase, integrase) and reports mutations. Phenotypic testing is not used. Either the mutation list or the sequence is needed for the Stanford interpretation.</p>
        </>}
      </div><div className="form-actions"><button className="btn">Record result</button></div></fieldset></form>
    </Card>}

    {canEdit && ['Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'].includes(patient.status) && <Card title="Repeat sample">
      <p className="tiny muted">Starts attempt {(lab.attempt || 1) + 1}. The current attempt is kept in the laboratory history.</p>
      <button className="btn" disabled={action.busy} onClick={() => action.run(() => labService.requestRepeat(patient.id), 'Repeat sample requested')}>Request a repeat sample</button>
    </Card>}
  </>;
}
