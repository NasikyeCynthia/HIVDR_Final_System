import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { patientService } from '../services/patientService.js';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import PatientOverview from '../components/patients/PatientOverview.jsx';
import ProfileForm from '../components/patients/ProfileForm.jsx';
import RiskSummary from '../components/risk/RiskSummary.jsx';
import LaboratoryForm from '../components/lab/LaboratoryForm.jsx';
import DiscussionThread from '../components/discussion/DiscussionThread.jsx';
import DecisionForm from '../components/decisions/DecisionForm.jsx';
import SourceRecord from '../components/patients/SourceRecord.jsx';
const tabs = [['overview', 'Overview'], ['profile', 'Profile'], ['risk', 'Risk assessment'], ['laboratory', 'Laboratory'], ['discussion', 'Discussion'], ['decision', 'Decision'], ['source', 'Source record']];
export default function PatientDetailPage() {
  const { patientId } = useParams();
  const [params, setParams] = useSearchParams();
  const { users, refresh } = useWorkspace();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const tab = params.get('tab') || 'overview';
  const load = useCallback(async () => { const value = await patientService.get(patientId); setDetail(value); }, [patientId]);
  useEffect(() => { let active = true; setDetail(null); setError(''); patientService.get(patientId).then(value => { if (active) setDetail(value); }).catch(failure => { if (active) setError(failure.message); }); return () => { active = false; }; }, [patientId]);
  const onSaved = async () => { await load(); await refresh(); };
  if (error) return <p className="notice error" role="alert">{error}</p>;
  if (!detail) return <div className="loading">Loading patient record…</div>;
  const { patient, original, discussion } = detail;
  return <><PageHeader title={patient.name} description={`${patient.external_id} · ${patient.source} · ${patient.facility}`} action={<Link to="/patients" className="btn secondary">← Patient records</Link>} /><div className="tabs" role="tablist" aria-label="Patient sections">{tabs.map(([key, label]) => <button role="tab" aria-selected={tab === key} key={key} className={`tab ${tab === key ? 'active' : ''}`} onClick={() => setParams({ tab: key })}>{label}</button>)}</div><div className="patient-detail">
    {tab === 'overview' && <PatientOverview patient={patient} users={users} onSaved={onSaved} />}
    {tab === 'profile' && <ProfileForm patient={patient} onSaved={onSaved} />}
    {tab === 'risk' && <RiskSummary patient={patient} onSaved={onSaved} />}
    {tab === 'laboratory' && <LaboratoryForm patient={patient} users={users} onSaved={onSaved} />}
    {tab === 'discussion' && <DiscussionThread patientId={patient.id} entries={discussion} onSaved={onSaved} />}
    {tab === 'decision' && <DecisionForm patient={patient} onSaved={onSaved} />}
    {tab === 'source' && <SourceRecord original={original} />}
    {!tabs.some(([key]) => key === tab) && <p className="notice">Unknown patient section. Choose a tab above.</p>}
  </div></>;
}
