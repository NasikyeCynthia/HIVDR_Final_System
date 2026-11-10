import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { patientService } from '../../services/patientService.js';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';

const lockedGroups = new Set(['Identity and provenance', 'Laboratory', 'Discussion and committee decision']);
const groupOrder = ['Patient background', 'Treatment history', 'Viral load history', 'Psychosocial', 'Follow-up', 'Laboratory', 'Discussion and committee decision', 'Identity and provenance'];

function isFixedPriorVlField(key) {
  return /^vl_\d+_Prior_To_DR$/i.test(key) || /^VL_\d+_Prior_To_DR_TestDate$/i.test(key);
}

function fieldGroup(key) {
  if (['Patient No.', 'Facility', 'Patient Add Time', 'Is Backlog?', 'isBacklog'].includes(key)) return 'Identity and provenance';
  if (['Decision Date', 'Decision', 'decision Category', 'Assigned ART by switch committee', 'ART started by patient', 'ART start date', 'Treatment Line on new ART'].includes(key)) return 'Discussion and committee decision';
  if (key.startsWith('VL 6 Months') || key.startsWith('VL 12 Months')) return 'Follow-up';
  if (key.startsWith('PSS:') || key === 'ASP') return 'Psychosocial';
  if (key === 'VL Leading to DR' || key === 'VL Test Date' || key.toLowerCase().startsWith('vl_')) return 'Viral load history';
  if (key.startsWith('Resistance to ') || key.toLowerCase().includes('mutation') || ['PI','INSTI','NRTI','NNRTI','Sample Type','Sample collection Date','No. of DR tests','dateTestedForDR','Date referred to DR Lab','DR_results_releaseDate','amplified'].includes(key) || key.startsWith('has relevant ')) return 'Laboratory';
  if (key.includes('ART') || key.includes('Treatment') || key.startsWith('exposure_') || ['drIndication','Regimen changes prior to sample collection'].includes(key)) return 'Treatment history';
  return 'Patient background';
}

function inputType(key) {
  if (/date/i.test(key)) return 'date';
  if (/^(Age\(yrs\)|Weight|Total Duration on ART|VL |vl_\d|No\. of DR tests)/i.test(key)) return 'number';
  return 'text';
}

function choiceField(key) {
  return key.startsWith('PSS:') || key.startsWith('exposure_') || key.startsWith('has relevant ') || ['Is Backlog?','isBacklog','ASP'].includes(key);
}

export default function RegisterPatientForm({ onCancel }) {
  const { refresh, source } = useWorkspace();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [columns, setColumns] = useState([]);
  const [viralLoadRows, setViralLoadRows] = useState([1]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    patientService.columns().then(result => { if (active) setColumns(result.columns || []); }).catch(failure => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);

  const grouped = columns.filter(column => !isFixedPriorVlField(column)).reduce((result, column) => {
    const group = fieldGroup(column);
    (result[group] ||= []).push(column);
    return result;
  }, {});

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const form = event.currentTarget;
    const formData = new FormData(form);
    const fields = {};
    for (const column of columns) {
      if (isFixedPriorVlField(column)) continue;
      if (lockedGroups.has(fieldGroup(column))) continue;
      const value = formData.get(`field:${column}`);
      if (value != null && String(value).trim()) fields[column] = String(value).trim();
    }
    for (const number of viralLoadRows) {
      const result = String(formData.get(`viral_load_test_${number}`) || '').trim();
      const date = String(formData.get(`viral_load_test_${number}_date`) || '').trim();
      if (date && !result) {
        setError(`Enter the result for viral load test ${number}, or clear its date.`);
        setBusy(false);
        return;
      }
      if (result) {
        fields[`viral_load_test_${number}`] = result;
        if (date) fields[`viral_load_test_${number}_date`] = date;
      }
    }
    try {
      const result = await patientService.create({
        external_id: formData.get('external_id'),
        name: formData.get('name') || '',
        dataset_source: source,
        fields,
      });
      await refresh();
      navigate(`/patients/${result.id}?tab=record`);
    } catch (failure) {
      setError(failure.message);
      setBusy(false);
    }
  }

  return <Card title="Register a patient" subtitle="Enter the identifying details and any known dataset fields. You can complete more fields later." className="section-gap">
    <Feedback error={error} />
    <form onSubmit={submit}>
      <div className="form-grid">
        <div className="field"><label htmlFor="new-patient-id">Unique patient ID (Patient No.)</label><input id="new-patient-id" name="external_id" required maxLength="100" /></div>
        <div className="field"><label htmlFor="new-patient-name">Patient name / display label</label><input id="new-patient-name" name="name" maxLength="200" /></div>
      </div>
      <p className="tiny muted">Facility is assigned from your account: <b>{user.facility}</b>. This registration will appear in the currently selected <b>{source === 'synthetic' ? 'Synthetic' : 'Original'}</b> dataset. The ID and facility are added automatically.</p>
      {!columns.length ? <p className="muted">Loading dataset fields…</p> : <>
        <p className="notice info">The form includes the CSV’s demographic, treatment, drug exposure, viral-load history, psychosocial and follow-up fields. Laboratory results and committee decisions are shown as separate locked sections; enter those through the lab and decision workflows.</p>
        {groupOrder.filter(group => grouped[group]?.length || group === 'Viral load history').map(group => <details className="registration-section" key={group} open={['Patient background','Treatment history','Viral load history'].includes(group)}>
          <summary>{group} <span className="tiny muted">({grouped[group].length} fields)</span></summary>
          {lockedGroups.has(group) && <p className="tiny muted">These fields are completed by the laboratory team or through clinical review; they cannot be entered during patient registration.</p>}
          <div className="record-grid registration-grid">{(grouped[group] || []).map(column => {
            const locked = lockedGroups.has(group);
            const id = `new-field-${encodeURIComponent(column)}`;
            return <div className="field" key={column}>
              <label htmlFor={id}>{column}{locked && <small> (role restricted)</small>}</label>
              {choiceField(column) ? <select id={id} name={`field:${column}`} disabled={locked || busy} defaultValue=""><option value="">Not recorded</option><option>Yes</option><option>No</option><option>Unknown</option><option value="1">1</option><option value="0">0</option></select>
                : <input id={id} name={`field:${column}`} type={inputType(column)} disabled={locked || busy} step={inputType(column)==='number'?'any':undefined} maxLength={inputType(column)==='text'?20000:undefined} />}
            </div>;
          })}</div>
          {group === 'Viral load history' && <div className="section-gap"><h3>Additional viral load tests</h3><p className="tiny muted">Add as many dated tests as needed. The index result “VL Leading to DR” remains a separate field for the resistance assessment.</p>{viralLoadRows.map(number => <div className="form-grid viral-load-input-row" key={number}><div className="field"><label htmlFor={`viral-load-result-${number}`}>Viral load test {number} result</label><input id={`viral-load-result-${number}`} name={`viral_load_test_${number}`} maxLength="100" placeholder="e.g. 250, &lt;20, or undetectable" /></div><div className="field"><label htmlFor={`viral-load-date-${number}`}>Test date</label><input id={`viral-load-date-${number}`} name={`viral_load_test_${number}_date`} type="date" /></div></div>)}<button className="btn secondary small" type="button" onClick={() => setViralLoadRows(rows => [...rows, Math.max(0, ...rows) + 1])}>+ Add another viral load test</button></div>}
        </details>)}
      </>}
      <div className="form-actions"><button className="btn" disabled={busy || !columns.length}>{busy ? 'Registering…' : 'Register and save entered fields'}</button><button className="btn secondary" type="button" onClick={onCancel} disabled={busy}>Cancel</button></div>
    </form>
  </Card>;
}
