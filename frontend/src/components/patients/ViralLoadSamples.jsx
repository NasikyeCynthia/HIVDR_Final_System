import { useState } from 'react';
import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import { patientService } from '../../services/patientService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';
import ViewOnly from '../common/ViewOnly.jsx';

// A viral load sample is recorded when blood is taken; its result is added when it returns.
// Results go into the dated viral load history used by eligibility, risk and time to failure.
const today = () => new Date().toISOString().slice(0, 10);
const fmt = v => v ? new Date(v + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

function ResultForm({ patient, sample, correcting, onDone, action }) {
  const [failed, setFailed] = useState(false);
  function submit(event) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const data = { result: f.get('result') || '', result_date: f.get('result_date'), failed, failure_reason: f.get('failure_reason') || '', correction_reason: f.get('correction_reason') || '' };
    action.run(() => patientService.vlResult(patient.id, sample.id, data), correcting ? 'Viral load result corrected' : 'Viral load result recorded').then(ok => ok && onDone());
  }
  return <form className="inline-form" onSubmit={submit}>
    <label className="checkbox"><input type="checkbox" checked={failed} onChange={e => setFailed(e.target.checked)} />Test failed / invalid</label>
    {!failed ? <label>Result (copies/mL)<input name="result" required defaultValue={correcting ? sample.result : ''} placeholder="e.g. 25000, <20, Target not detected" maxLength="100" /></label>
      : <label>Why it failed<input name="failure_reason" required maxLength="1000" placeholder="e.g. invalid run, sample haemolysed" /></label>}
    <label>Result date<input name="result_date" type="date" required min={sample.collected_on} max={today()} defaultValue={correcting ? sample.result_date : today()} /></label>
    {correcting && <label>Reason for the correction<input name="correction_reason" required minLength={10} maxLength="3000" /></label>}
    <button className="btn small" disabled={action.busy}>{correcting ? 'Save correction' : 'Save result'}</button>
    <button type="button" className="btn small secondary" onClick={onDone}>Cancel</button>
  </form>;
}

export default function ViralLoadSamples({ patient, samples = [], indications = [], onSaved }) {
  const { user } = useAuth();
  const can = useCan();
  const action = usePatientAction(onSaved);
  const [open, setOpen] = useState(null); // sample id being resulted or corrected
  const canSample = can('edit_patient_record', patient);
  const canResult = canSample || can('record_lab', patient);
  const pending = samples.filter(s => s.status === 'Pending').length;
  function addSample(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const f = new FormData(form);
    const data = { collected_on: f.get('collected_on'), indication: f.get('indication'), result: f.get('result') || '', result_date: f.get('result_date') || null };
    action.run(() => patientService.vlSample(patient.id, data), data.result ? 'Viral load sample and result recorded' : 'Viral load sample recorded; add the result when it returns').then(ok => ok && form.reset());
  }
  return <Card title="Viral load samples" subtitle={pending ? `${pending} result(s) awaited` : 'Record each viral load sample when it is taken, then its result when it returns'}>
    <Feedback error={action.error} success={action.success} />
    {samples.length ? <div className="table-wrap"><table><thead><tr><th>Sample taken</th><th>Indication</th><th>Status</th><th>Result</th><th>Result date</th><th>Recorded by</th><th /></tr></thead><tbody>
      {samples.map(s => <tr key={s.id}>
        <td>{fmt(s.collected_on)}</td><td>{s.indication}</td>
        <td><Badge color={s.status === 'Pending' ? 'yellow' : s.status === 'Resulted' ? 'green' : 'red'}>{s.status === 'Pending' ? 'Result awaited' : s.status}</Badge></td>
        <td>{s.status === 'Resulted' ? <>{s.result}{(() => { const n = Number(String(s.result).replace(/[^0-9.]/g, '')); return !/^</.test(s.result) && n >= 1000 ? <div><Badge color="red">≥1000 · not suppressed</Badge></div> : null; })()}</> : s.failure_reason || '—'}</td>
        <td>{fmt(s.result_date)}</td><td className="tiny">{s.collected_by_name}{s.resulted_by_name ? ` · ${s.resulted_by_name}` : ''}</td>
        <td>{canResult && open !== s.id && <button className="btn small secondary" onClick={() => setOpen(s.id)}>{s.status === 'Pending' ? 'Record result' : 'Correct'}</button>}</td>
      </tr>)}
    </tbody></table></div> : <p className="muted">No viral load samples recorded in the system yet.</p>}
    {open && <ResultForm key={open} patient={patient} sample={samples.find(s => s.id === open)} correcting={samples.find(s => s.id === open)?.status !== 'Pending'} onDone={() => setOpen(null)} action={action} />}
    <h3 style={{ marginTop: 18 }}>Record a sample taken</h3>
    {canSample ? <form onSubmit={addSample}><div className="form-grid">
      <div className="field"><label>Date the sample was taken<input name="collected_on" type="date" required max={today()} defaultValue={today()} /></label></div>
      <div className="field"><label>Indication (as on the request form)<select name="indication" required defaultValue=""><option value="" disabled>Choose…</option>{indications.map(i => <option key={i}>{i}</option>)}</select></label></div>
      <div className="field"><label>Result, if already back (optional)<input name="result" maxLength="100" placeholder="leave blank if awaited" /></label></div>
      <div className="field"><label>Result date (if result given)<input name="result_date" type="date" max={today()} /></label></div>
    </div><div className="form-actions"><button className="btn" disabled={action.busy}>Record sample</button></div></form> : <ViewOnly action="edit_patient_record" />}
    <p className="tiny muted">Results are filed in the viral load history under the date the sample was taken. Laboratory staff can also record returning results.</p>
  </Card>;
}
