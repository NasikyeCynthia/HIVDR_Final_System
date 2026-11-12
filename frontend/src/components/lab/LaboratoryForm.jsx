import { useEffect, useState } from 'react';
import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import ViewOnly from '../common/ViewOnly.jsx';
import { labService } from '../../services/labService.js';
import { riskService } from '../../services/riskService.js';
import { Link } from 'react-router-dom';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';

// HIVDR laboratory steps in the MoH order (HIVDR Participants' Manual §5 and §7.3):
// 1 request (request form) → 2 sample collection → 3 hub transport → 4 CPHL receipt (acceptance checks,
// repeat viral load, refer/defer/reject) → 5 DR-lab genotype result → 6 Stanford interpretation; repeat if failed.
// Rules are enforced by the backend (app/services/lab_service.py); this form only collects input.
const STAGES = ['Not requested', 'Requested', 'Collected at facility', 'In transit', 'At CPHL', 'At DR laboratory', 'Result released'];
const CHECKS = [['id_matches', 'ART number on the sample matches the request form'], ['form_has_id', 'Request form has the patient’s ART or other number'],
  ['not_haemolysed', 'Plasma is not haemolysed'], ['tube_not_empty', 'Plasma preparation tube is not empty'], ['volume_ok', 'At least 1 mL of plasma']];
const LEVEL = { error: 'red', warning: 'yellow', info: '' };
const when = v => v ? new Date(v).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
const day = v => v ? new Date(v).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
const nowLocal = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16); };
const local = v => v ? String(v).slice(0, 16) : '';
const dateOnly = v => v ? String(v).slice(0, 10) : '';
const numbers = (data, keys) => { for (const k of keys) data[k] = data[k] === '' || data[k] == null ? null : Number(data[k]); return data; };

function Field({ label, children, full }) { return <div className={`field ${full ? 'full' : ''}`}><label>{label}{children}</label></div>; }

export default function LaboratoryForm({ patient, onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  const [options, setOptions] = useState(null);
  const [kind, setKind] = useState('Plasma');
  const [outcome, setOutcome] = useState('Referred to DR lab');
  const [result, setResult] = useState('Usable result');
  const [checks, setChecks] = useState(Object.fromEntries(CHECKS.map(([k]) => [k, true])));
  const [repeatVl, setRepeatVl] = useState('');
  const [correcting, setCorrecting] = useState(null); // 'collection' | 'dispatch' | 'receipt' | 'result'
  useEffect(() => { setCorrecting(null); }, [patient.version, patient.status]);
  useEffect(() => { if (correcting === 'collection') setKind(patient.sample_type || 'Plasma'); }, [correcting, patient.sample_type]);
  const failedCheck = CHECKS.some(([k]) => !checks[k]);
  const lowVl = repeatVl !== '' && Number(repeatVl) < 1000;
  useEffect(() => { labService.options().then(setOptions).catch(() => setOptions(null)); }, []);
  const lab = patient.lab || { stage: 'Not requested', flags: [], tat: {} };
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
  const indication = patient.referred_at || patient.repeat_requested_at || eligibility.sample_due;
  const requestForm = event => {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const body = { basis: f.get('basis'), reason: f.get('reason') || '', weight_kg: Number(f.get('weight_kg')), on_rifampicin: f.get('on_rifampicin') === 'Yes', biorepository_consent: f.get('biorepository_consent') };
    action.run(() => riskService.refer(patient.id, body), 'DR test requested; you are the accountable laboratory officer for this patient');
  };

  return <>
    <Card title="HIVDR sample" subtitle={`Attempt ${lab.attempt}${lab.dr_lab ? ` · DR laboratory: ${lab.dr_lab}` : ''}`}>
      <div className="lab-stages" aria-label="Sample progress">{STAGES.map((s, i) => <span key={s} className={i < stageIndex ? 'done' : i === stageIndex ? 'current' : ''}>{s}</span>)}</div>
      {lab.stage === 'Returned to facility' && <p className="notice error">{patient.status === 'Rejected' ? 'Rejected at CPHL' : 'Deferred to facility'}: {patient.cphl_reason || patient.failure_reason}</p>}
      {lab.flags.map((f, i) => <p key={i} className={`notice ${f.level === 'info' ? 'info' : f.level === 'error' ? 'error' : ''}`}><Badge color={LEVEL[f.level]}>{f.level === 'error' ? 'Problem' : f.level === 'warning' ? 'Check' : 'Note'}</Badge> {f.text} <span className="tiny muted">({lab.sources?.[f.source]})</span></p>)}
      <div className="detail-list">
        <div><label>DR test requested</label>{day(patient.referred_at)}{patient.referral_basis ? <div className="tiny muted">{patient.referral_basis}</div> : null}</div>
        <div><label>Request form</label>{patient.weight_kg != null ? `${patient.weight_kg} kg · ${patient.on_rifampicin ? 'on rifampicin' : 'not on rifampicin'} · storage consent: ${patient.biorepository_consent || '—'}` : '—'}</div>
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
        <div><label>Repeat viral load (CPHL)</label>{patient.cphl_vl != null ? `${Number(patient.cphl_vl).toLocaleString()} copies/mL · ${day(patient.cphl_vl_date)}` : '—'}</div>
        <div><label>Mutations recorded</label>{patient.mutations || '—'}</div>
        <div><label>HIV subtype</label>{patient.subtype || '—'}</div>
      </div>
      {!canEdit && (patient.reviewed_at || patient.decision ? <p className="notice info" style={{ marginTop: 16 }}>This episode has been reviewed; the laboratory record is locked. Use the amendment workflow to correct it.</p> : <ViewOnly action="record_lab" />)}
      <Feedback error={action.error} success={action.success} />
    </Card>

    {canEdit && options && <CorrectionPicker patient={patient} lab={lab} correcting={correcting} setCorrecting={setCorrecting} />}

    {canEdit && options && !patient.referred_at && !patient.repeat_requested_at && patient.status === 'Not collected' && <Card title="1. Request the DR test" subtitle="The DR section of the MoH/CPHL request form; you become the accountable laboratory officer">
      <p><b>{eligibility.label || 'Eligibility not assessed'}</b>{eligibility.indication ? ` · ${eligibility.indication}` : ''}. {eligibility.next_step}</p>
      <form onSubmit={requestForm}><fieldset disabled={action.busy}><div className="form-grid">
        <Field label="Basis"><select name="basis" defaultValue={eligibility.eligible ? 'guideline' : 'clinician_override'}><option value="guideline" disabled={!eligibility.eligible}>Meets MoH/WHO criteria</option><option value="clinician_override">Other indication (explain)</option></select></Field>
        <Field label="Body weight (kg)"><input name="weight_kg" type="number" min="0.5" max="250" step="0.1" required /></Field>
        <Field label="Patient on rifampicin?"><select name="on_rifampicin" required defaultValue=""><option value="" disabled>Choose…</option><option>No</option><option>Yes</option></select></Field>
        <Field label="Biospecimen storage consent"><select name="biorepository_consent" required defaultValue=""><option value="" disabled>Choose…</option><option>Accept</option><option>Decline</option></select></Field>
        <Field label="Indication / note (required for other indications: e.g. infant of a mother failing treatment, clinician’s request)" full><input name="reason" maxLength="5000" /></Field>
      </div><div className="form-actions"><button className="btn">Request DR test</button></div></fieldset></form>
    </Card>}

    {canEdit && options && ((['Not requested', 'Requested'].includes(lab.stage) && patient.status === 'Not collected' && indication) || correcting === 'collection') && <Card title={correcting === 'collection' ? 'Correct: sample collection' : '2. Record sample collection'} subtitle="Plasma is the recommended sample: 5–8 mL whole blood in two PPT tubes (one for the repeat viral load, one for HIVDR), separated within 6 hours">
      {patient.repeat_requested_at && <p className="notice info">Repeat sample requested {day(patient.repeat_requested_at)}{patient.repeat_reason ? ` — ${patient.repeat_reason}` : ''}. The nurse/counsellor has been asked to bring the patient back.</p>}
      <form key={correcting === 'collection' ? 'fix' : 'new'} onSubmit={submit(labService.collection, correcting === 'collection' ? 'Collection corrected' : 'Collection recorded', ['tubes', 'whole_blood_ml'])}><fieldset disabled={action.busy}>
        {correcting === 'collection' && <Reason />}<div className="form-grid">
        <Field label="Sample type"><select name="sample_type" value={kind} onChange={e => setKind(e.target.value)}><option>Plasma</option><option>DBS</option></select></Field>
        <Field label="Collected (date and time)"><input name="collected_at" type="datetime-local" max={max} required defaultValue={correcting === 'collection' ? local(patient.sample_at) : ''} /></Field>
        <Field label="Laboratory officer in charge"><input name="officer_name" defaultValue={(correcting === 'collection' && patient.officer_name) || user.name} required maxLength="200" /></Field>
        <Field label="Officer phone (for delayed results)"><input name="officer_phone" type="tel" required placeholder="07XX XXX XXX" maxLength="30" defaultValue={correcting === 'collection' ? patient.officer_phone || '' : ''} /></Field>
        {kind === 'Plasma' ? <>
          <Field label="Centrifuged (date and time)"><input name="centrifuged_at" type="datetime-local" max={max} required defaultValue={correcting === 'collection' ? local(patient.centrifuged_at) : ''} /></Field>
          <Field label="Number of PPT tubes"><input name="tubes" type="number" min="0" max="6" defaultValue={correcting === 'collection' && patient.tubes != null ? patient.tubes : 2} /></Field>
          <Field label="Whole blood collected (mL)"><input name="whole_blood_ml" type="number" min="0" max="30" step="0.5" defaultValue={correcting === 'collection' ? patient.whole_blood_ml ?? '' : ''} /></Field>
          <Field label="Storage until pick-up"><select name="storage_temp" defaultValue={options.storage[0]}>{options.storage.map(s => <option key={s}>{s}</option>)}</select></Field>
        </> : <>
          <Field label="Why DBS instead of plasma" full><select name="dbs_reason" required defaultValue=""><option value="" disabled>Choose a reason…</option>{options.dbs_reasons.map(s => <option key={s}>{s}</option>)}</select></Field>
          <Field label="Explanation" full><input name="dbs_note" maxLength="3000" /></Field>
        </>}
      </div><div className="form-actions"><button className="btn">{correcting === 'collection' ? 'Save correction' : 'Record collection'}</button></div></fieldset></form>
    </Card>}

    {canEdit && options && (lab.stage === 'Collected at facility' || correcting === 'dispatch') && <Card title={correcting === 'dispatch' ? 'Correct: hub pick-up' : '3. Record hub pick-up'} subtitle="Target: picked up within 2 days, kept at 4–8 °C">
      <form key={correcting || 'new'} onSubmit={submit(labService.dispatch, correcting === 'dispatch' ? 'Pick-up corrected' : 'Dispatch recorded')}><fieldset disabled={action.busy}>{correcting === 'dispatch' && <Reason />}<div className="form-grid">
        <Field label="Picked up / dispatched"><input name="dispatched_at" type="date" max={max.slice(0, 10)} required defaultValue={correcting === 'dispatch' ? dateOnly(patient.dispatched_at) : ''} /></Field>
      </div><div className="form-actions"><button className="btn">{correcting === 'dispatch' ? 'Save correction' : 'Record dispatch'}</button></div></fieldset></form>
    </Card>}

    {canEdit && options && (['Collected at facility', 'In transit'].includes(lab.stage) || correcting === 'receipt') && <Card title={correcting === 'receipt' ? 'Correct: CPHL receipt' : '4. Record receipt at CPHL'} subtitle={`a) check the sample · b) record the repeat viral load · c) refer to ${patient.sample_type === 'DBS' ? 'UVRI (DBS)' : 'JCRC (plasma)'}, defer or reject`}>
      <form onSubmit={event => { event.preventDefault(); const data = numbers(Object.fromEntries(new FormData(event.currentTarget)), ['plasma_volume_ml', 'repeat_vl']); for (const k of Object.keys(data)) if (data[k] === '' || data[k] == null) delete data[k]; for (const [k] of CHECKS) delete data[k]; data.checks = checks; action.run(() => labService.receipt(patient.id, data), correcting === 'receipt' ? 'CPHL receipt corrected' : 'CPHL receipt recorded'); }}><fieldset disabled={action.busy}>
        {correcting === 'receipt' && <Reason />}
        <h3 className="ttf-heading">a) Sample acceptance checks (MoH rejection criteria)</h3>
        <div className="check-grid">{CHECKS.map(([k, label]) => <label className="checkbox" key={k}><input type="checkbox" checked={checks[k]} onChange={e => { const next = { ...checks, [k]: e.target.checked }; setChecks(next); if (!e.target.checked) setOutcome('Rejected'); }} />{label}</label>)}</div>
        {failedCheck && <p className="notice error">A check failed: the sample must be rejected and recollected.</p>}
        <h3 className="ttf-heading">b) Repeat viral load from the same blood draw</h3>
        <div className="form-grid">
          <Field label="Repeat viral load (copies/mL)"><input name="repeat_vl" type="number" min="0" value={repeatVl} onChange={e => { setRepeatVl(e.target.value); if (e.target.value !== '' && Number(e.target.value) < 1000 && !failedCheck) setOutcome('Deferred to facility'); }} /></Field>
          <Field label="Viral load date"><input name="repeat_vl_date" type="date" max={max.slice(0, 10)} required={repeatVl !== ''} /></Field>
        </div>
        {lowVl && <p className="notice">Below 1000 copies/mL: the DR test does not go ahead. Defer as “Below threshold for HIVDR testing”.</p>}
        <h3 className="ttf-heading">c) Decision</h3>
        <div className="form-grid">
        <Field label="Received at CPHL"><input name="received_at" type="date" max={max.slice(0, 10)} required defaultValue={correcting === 'receipt' ? dateOnly(patient.received_at) : ''} /></Field>
        <Field label="Plasma volume received (mL)"><input name="plasma_volume_ml" type="number" min="0" max="20" step="0.1" defaultValue={correcting === 'receipt' ? patient.plasma_volume_ml ?? '' : ''} /></Field>
        <Field label="Decision"><select name="outcome" value={outcome} onChange={e => setOutcome(e.target.value)}><option disabled={failedCheck || lowVl}>Referred to DR lab</option><option disabled={failedCheck}>Deferred to facility</option><option>Rejected</option></select></Field>
        {outcome !== 'Referred to DR lab' && <Field label="Reason"><select name="reason" required key={outcome + lowVl} defaultValue={outcome === 'Deferred to facility' && lowVl ? 'Below threshold for HIVDR testing' : ''}><option value="" disabled>Choose…</option>{(outcome === 'Rejected' ? options.rejection_reasons : options.deferral_reasons).map(s => <option key={s}>{s}</option>)}</select></Field>}
        {outcome !== 'Referred to DR lab' && <Field label="Explanation" full><input name="note" maxLength="3000" /></Field>}
      </div><div className="form-actions"><button className="btn">{correcting === 'receipt' ? 'Save correction' : 'Record receipt'}</button></div></fieldset></form>
    </Card>}

    {canEdit && options && (lab.stage === 'At DR laboratory' || correcting === 'result') && <Card title={correcting === 'result' ? 'Correct: genotype result' : '5. Record the genotype result'} subtitle={`Turnaround target ${options.tat_days} days from CPHL receipt`}>
      <form key={correcting || 'new'} onSubmit={event => { event.preventDefault(); const f = new FormData(event.currentTarget); const data = {}; const levels = {};
        for (const [k, v] of f.entries()) { if (k.startsWith('level:')) { if (v) levels[k.slice(6)] = v; } else if (v !== '') data[k] = v; }
        data.drug_levels = levels; action.run(() => labService.result(patient.id, data), correcting === 'result' ? 'Result corrected' : 'Result recorded'); }}><fieldset disabled={action.busy}>{correcting === 'result' && <Reason />}<div className="form-grid">
        <Field label="Outcome"><select name="outcome" value={result} onChange={e => setResult(e.target.value)}><option>Usable result</option><option>Unamplified</option><option>Sequencing failed</option></select></Field>
        <Field label="Tested on"><input name="tested_at" type="date" max={max.slice(0, 10)} required defaultValue={correcting === 'result' ? dateOnly(patient.tested_at) : ''} /></Field>
        <Field label="Result released on"><input name="released_at" type="date" max={max.slice(0, 10)} required defaultValue={correcting === 'result' ? dateOnly(patient.report_at) : ''} /></Field>
        {result !== 'Usable result' && <Field label="Reason the test was unsuccessful" full><textarea name="failure_reason" required maxLength="3000" /></Field>}
        {result === 'Usable result' && <>
          <p className="field full tiny"><b>Mutations by drug class, as on the genotype report</b> — write them separated by spaces or commas, e.g. M184V K65R.</p>
          <Field label="NRTI mutations"><input name="nrti" placeholder="e.g. M184V K65R" /></Field>
          <Field label="NNRTI mutations"><input name="nnrti" placeholder="e.g. K103N G190A" /></Field>
          <Field label="PI major mutations"><input name="pi_major" placeholder="e.g. I50V" /></Field>
          <Field label="PI minor mutations"><input name="pi_minor" /></Field>
          <Field label="INSTI mutations"><input name="insti" placeholder="e.g. R263K G118R" /></Field>
          <Field label="Other / accessory mutations"><input name="other" /></Field>
          <Field label={correcting === 'result' ? 'Current mutation list (edit here, or clear it and re-enter by drug class above)' : 'Or one list with genes (e.g. RT:M184V IN:R263K); write “none” if no mutations'} full><textarea name="mutations" maxLength="15000" defaultValue={correcting === 'result' ? patient.mutations || '' : ''} /></Field>
          <Field label="Or paste the pol nucleotide sequence (FASTA)" full><textarea name="sequence" maxLength="100000" /></Field>
          <Field label="HIV-1 subtype (from the report or Stanford, e.g. A1, D, C)"><input name="subtype" maxLength="40" defaultValue={correcting === 'result' ? patient.subtype || '' : ''} /></Field>
          <details className="field full"><summary>Drug resistance levels as printed on the report (optional — Stanford fills these when run)</summary>
            <div className="form-grid" style={{ marginTop: 10 }}>{(options.drugs || []).map(d => <Field key={d} label={d}><select name={`level:${d}`} defaultValue=""><option value="">Not reported</option>{(options.levels || []).map(l => <option key={l}>{l}</option>)}</select></Field>)}</div>
          </details>
          <p className="tiny muted field full">HIVDR testing in Uganda is genotypic: the lab sequences the pol gene (protease, reverse transcriptase, integrase) and reports mutations. Phenotypic testing is not used. Either the mutation list or the sequence is needed for the Stanford interpretation.</p>
        </>}
      </div><div className="form-actions"><button className="btn">{correcting === 'result' ? 'Save correction' : 'Record result'}</button></div></fieldset></form>
    </Card>}

    {patient.status === 'Usable result' && <Card title="6. Interpret the result" subtitle="Stanford HIVdb drug-level interpretation, then release to the facility">
      <p>Run the Stanford interpretation on the Resistance tab. The drug levels feed the committee’s suggested action.</p>
      <Link className="btn" to={`/patients/${patient.id}?tab=resistance`}>Open Resistance tab →</Link>
    </Card>}

    {canEdit && ['Pending', 'Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'].includes(patient.status) && <Card title="Request a new sample" subtitle={patient.status === 'Pending' ? 'For a sample lost, leaking, broken or unusable before a result' : 'After rejection, deferral or an unsuccessful test'}>
      <p className="tiny muted">Starts attempt {(lab.attempt || 1) + 1}. The current attempt is kept in the laboratory history.</p>
      <form onSubmit={e => { e.preventDefault(); const note = new FormData(e.currentTarget).get('note'); action.run(() => labService.requestRepeat(patient.id, note), 'Repeat sample requested; the nurse/counsellor has been notified'); }}>
        {patient.status !== 'Pending' && <p className="tiny">Reason recorded: <b>{patient.failure_reason || patient.cphl_reason || patient.status}</b>.</p>}<p className="tiny">The request goes to the patient’s nurse/counsellor, who brings the patient back.</p>
        <label htmlFor="repeat-note">{patient.status === 'Pending' ? 'Why is a new sample needed? (required)' : 'Instructions for the nurse/counsellor (optional)'}</label><input id="repeat-note" name="note" maxLength="3000" required={patient.status === 'Pending'} placeholder={patient.status === 'Pending' ? 'e.g. tube broke in transit' : 'e.g. collect 2 plasma tubes'} />
        <div className="form-actions"><button className="btn" disabled={action.busy}>Request a new sample</button></div>
      </form>
    </Card>}
  </>;
}

function Reason() {
  return <div className="field full" style={{ marginBottom: 12 }}><label>Reason for the correction (kept in the audit trail)<input name="correction_reason" required minLength={10} maxLength={3000} placeholder="e.g. wrong date entered; K65R entered in error" /></label></div>;
}

// Lets laboratory staff reopen a step they already recorded, until the committee has reviewed the result.
function CorrectionPicker({ patient, lab, correcting, setCorrecting }) {
  const steps = [
    ['collection', 'Sample collection', Boolean(patient.sample_at)],
    ['dispatch', 'Hub pick-up', Boolean(patient.dispatched_at)],
    ['receipt', 'CPHL receipt', Boolean(patient.cphl_outcome) && !['Usable result', 'Unamplified', 'Sequencing failed'].includes(patient.status)],
    ['result', 'Genotype result', ['Usable result', 'Unamplified', 'Sequencing failed'].includes(patient.status)],
  ].filter(([, , ok]) => ok);
  if (!steps.length) return null;
  return <div className="correction-bar"><span>Edit a recorded step:</span>{steps.map(([key, label]) => <button type="button" key={key} className={`btn small ${correcting === key ? '' : 'secondary'}`} onClick={() => setCorrecting(correcting === key ? null : key)}>{correcting === key ? `Cancel editing ${label.toLowerCase()}` : label}</button>)}<span className="tiny muted">Every edit needs a reason and is kept in the audit trail.</span></div>;
}
