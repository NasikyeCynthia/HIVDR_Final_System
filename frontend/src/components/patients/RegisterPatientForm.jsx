import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { patientService } from '../../services/patientService.js';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import Card from '../common/Card.jsx';
import FormField from '../common/FormField.jsx';
import Feedback from '../common/Feedback.jsx';
export default function RegisterPatientForm({ onCancel }) {
  const { refresh, setSource } = useWorkspace();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try { const result = await patientService.create(data); setSource('manual'); await refresh(); navigate(`/patients/${result.id}?tab=profile`); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <Card title="Register a patient" className="section-gap"><Feedback error={error} /><form onSubmit={submit}><div className="form-grid"><FormField label="Unique patient ID" name="external_id" required maxLength="100" /><FormField label="Patient name / display label" name="name" maxLength="200" /></div><div className="form-actions"><button className="btn" disabled={busy}>Register and complete profile</button><button className="btn secondary" type="button" onClick={onCancel}>Cancel</button></div></form></Card>;
}
