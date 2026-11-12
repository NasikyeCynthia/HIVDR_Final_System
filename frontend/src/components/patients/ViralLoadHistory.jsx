import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import { operationsService } from '../../services/operationsService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';
import ViralLoadSamples from './ViralLoadSamples.jsx';

function numberedTests(record) {
  const numbers = new Set();
  for (let n = 1; n <= 10; n += 1) {
    const value = record[`vl_${n}_Prior_To_DR`];
    const date = record[`VL_${n}_Prior_To_DR_TestDate`];
    if (String(value || '').trim() || String(date || '').trim()) numbers.add(n);
  }
  for (const key of Object.keys(record)) {
    const match = key.match(/^viral_load_test_(\d+)(?:_date)?$/);
    if (match && String(record[key] || '').trim()) numbers.add(Number(match[1]));
  }
  return [...numbers].sort((a, b) => a - b).map(number => ({
    number,
    result: record[`viral_load_test_${number}`] || record[`vl_${number}_Prior_To_DR`] || '',
    date: record[`viral_load_test_${number}_date`] || record[`VL_${number}_Prior_To_DR_TestDate`] || '',
  }));
}

export default function ViralLoadHistory({ patient, record = {}, samples = [], indications = [], onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  const tests = numberedTests(record);
  const nextNumber = Math.max(0, ...tests.map(test => test.number)) + 1;
  const canEdit = useCan()('edit_patient_record', patient);

  async function addTest(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const result = String(data.get('result') || '').trim();
    const date = String(data.get('test_date') || '').trim();
    const fields = { [`viral_load_test_${nextNumber}`]: result };
    if (date) fields[`viral_load_test_${nextNumber}_date`] = date;
    if (await action.run(() => operationsService.fields(patient.id, fields, patient.data_version || 0), `Viral load test ${nextNumber} added`)) event.currentTarget.reset();
  }

  const followUps = [
    ['6-month follow-up', record['VL 6 Months Post Decision'], record['VL 6 Months Post Decision: Date']],
    ['12-month follow-up', record['VL 12 Months Post Decision'], record['VL 12 Months Post Decision: Date']],
  ].filter(([, value, date]) => String(value || '').trim() || String(date || '').trim());

  return <>
    <ViralLoadSamples patient={patient} samples={samples} indications={indications} onSaved={onSaved} />
    <Card title="Viral load history" subtitle="Numbered tests can continue beyond the 10 prior-test columns in the original CSV.">
      <div className="detail-list"><div><label>{record['VL Leading to DR'] ? 'VL leading to drug-resistance testing' : 'Latest viral load'}</label>{record['VL Leading to DR'] || patient.viral_load || 'Not recorded'}</div><div><label>Test date</label>{record['VL Test Date'] || 'Not recorded'}</div></div>
      <h3>Viral load tests</h3>
      {tests.length ? <div className="table-wrap"><table><thead><tr><th>Test</th><th>Result</th><th>Date</th></tr></thead><tbody>{tests.map(test => <tr key={test.number}><td>Test {test.number}</td><td>{test.result || 'Not recorded'}</td><td>{test.date || 'Not recorded'}</td></tr>)}</tbody></table></div> : <p className="muted">No additional prior viral load tests are recorded.</p>}
      {followUps.length > 0 && <><h3>Post-decision follow-up</h3><div className="table-wrap"><table><thead><tr><th>Follow-up</th><th>Viral load</th><th>Date</th></tr></thead><tbody>{followUps.map(([label, value, date]) => <tr key={label}><td>{label}</td><td>{value || 'Not recorded'}</td><td>{date || 'Not recorded'}</td></tr>)}</tbody></table></div></>}
      <p className="tiny muted">All dated results here are used, in date order, by the eligibility rules and the risk score. Non-suppressed means 1,000 copies/mL or more (WHO).</p>
    </Card>
    {canEdit ? <Card title={`Add a past result (test ${nextNumber})`} subtitle="For results from before this system, e.g. copied from the patient file">
      <Feedback error={action.error} success={action.success}/>
      <form onSubmit={addTest}><div className="form-grid"><div className="field"><label htmlFor="new-vl-result">Test result</label><input id="new-vl-result" name="result" required maxLength="100" placeholder="e.g. 250, &lt;20, or undetectable" /></div><div className="field"><label htmlFor="new-vl-date">Test date</label><input id="new-vl-date" name="test_date" type="date" /></div></div><div className="form-actions"><button className="btn" disabled={action.busy}>{action.busy ? 'Saving…' : `Add test ${nextNumber}`}</button></div></form>
    </Card> : null}
  </>;
}
