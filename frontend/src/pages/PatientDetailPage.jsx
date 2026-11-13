import MutationEntry from '../components/resistance/MutationEntry.jsx';
import RiskScoreCard from '../components/risk/RiskScoreCard.jsx';
import RecordEditor from '../components/patients/RecordEditor.jsx';
import ArchiveControl from '../components/patients/ArchiveControl.jsx';
import LaboratoryHistory from '../components/lab/LaboratoryHistory.jsx';
import InterpretationPanel from '../components/resistance/InterpretationPanel.jsx';
import PsychosocialForm from '../components/patients/PsychosocialForm.jsx';
import ReviewReadiness from '../components/discussion/ReviewReadiness.jsx';
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
import ImplementationPanel from '../components/decisions/ImplementationPanel.jsx';
import SourceRecord from '../components/patients/SourceRecord.jsx';
import ViralLoadHistory from '../components/patients/ViralLoadHistory.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
const tabs = [['overview', 'Overview'], ['profile', 'Profile'], ['record', 'Full record'], ['viral-load', 'Viral load history'], ['risk', 'Risk & eligibility'], ['laboratory', 'Laboratory'], ['resistance', 'Resistance'], ['psychosocial', 'Psychosocial'], ['discussion', 'Discussion & committee decision'], ['decision', 'Implementation & follow-up'], ['source', 'Source record']];
export default function PatientDetailPage() {
  const { patientId } = useParams();
  const [params, setParams] = useSearchParams();
  const { user } = useAuth();
  const { users, refresh } = useWorkspace();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const [pollError,setPollError]=useState('');
  const requestedTab = params.get('tab') || 'overview';
  const requestedSection = requestedTab;
  const nurseBlockedSection = false;
  const tab = nurseBlockedSection ? 'overview' : requestedSection;
  const visibleTabs = tabs;
  useEffect(() => {
    if (nurseBlockedSection) setParams({ tab: 'overview' }, { replace: true });
  }, [nurseBlockedSection, setParams]);
  const load = useCallback(async () => { const value = await patientService.get(patientId); setDetail(value); }, [patientId]);
  useEffect(() => { let active = true; setDetail(null); setError(''); patientService.get(patientId).then(value => { if (active) setDetail(value); }).catch(failure => { if (active) setError(failure.message); }); return () => { active = false; }; }, [patientId]);
  const onSaved = async () => { await load(); await refresh(); };
  const analysisPending=['pending','running'].includes(detail?.patient?.automation?.status);
  useEffect(()=>{
    if(!analysisPending)return;
    let active=true;
    const timer=setInterval(async()=>{
      try{const next=await patientService.get(patientId);if(!active)return;setPollError('');setDetail(next);
        if(!['pending','running'].includes(next.patient.automation?.status))refresh().catch(()=>{});
      }catch(failure){if(active)setPollError(failure.message);}
    },2000);
    return()=>{active=false;clearInterval(timer);};
  },[analysisPending,patientId,refresh]);

  if (error) return <p className="notice error" role="alert">{error}</p>;
  if (!detail) return <div className="loading">Loading patient record…</div>;
  const { patient, original, discussion } = detail;
  return <><PageHeader title={patient.name} description={`${patient.external_id} · ${patient.source} · ${patient.facility}`} action={<Link to="/patients" className="btn secondary">← Patient records</Link>} /><div className="tabs" role="tablist" aria-label="Patient sections">{visibleTabs.map(([key, label]) => <button role="tab" aria-selected={tab === key} key={key} className={`tab ${tab === key ? 'active' : ''}`} onClick={() => setParams({ tab: key })}>{label}</button>)}</div><div className="patient-detail">{pollError&&<p className="notice error" role="alert">Could not refresh analysis status: {pollError}</p>}
    {tab === 'overview' && <><PatientOverview patient={patient} users={users} onSaved={onSaved}/><ArchiveControl patient={patient} onSaved={onSaved}/></>}
    {tab === 'profile' && <><ProfileForm patient={patient} onSaved={onSaved}/><RecordEditor patient={patient} sections={detail.record_sections} allowedSections={['Patient background','Treatment history']} onSaved={onSaved}/></>}
    {tab === 'record' && <><RecordEditor patient={patient} sections={detail.record_sections} onSaved={onSaved}/><RiskScoreCard risk={patient.risk}/></>}
    {tab === 'viral-load' && <ViralLoadHistory patient={patient} record={detail.current_record} samples={detail.vl_samples || []} indications={detail.vl_indications || []} onSaved={onSaved}/>}
    {tab === 'risk' && <RiskSummary patient={patient} sessions={detail.iac_sessions||[]} onSaved={onSaved} />}
    {tab === 'laboratory' && <><LaboratoryForm patient={patient} record={detail.current_record} onSaved={onSaved}/><div id="lab-mutations"><MutationEntry patient={patient} record={detail.current_record} onSaved={onSaved}/></div><LaboratoryHistory entries={detail.lab_history||[]}/></>}
    {tab === 'resistance' && <InterpretationPanel patient={patient} record={detail.current_record} onSaved={onSaved}/>}
    {tab === 'psychosocial' && <PsychosocialForm patient={patient} onSaved={onSaved}/>}
    {tab === 'discussion' && <><ReviewReadiness patient={patient} onSaved={onSaved}/><DecisionForm patient={patient} onSaved={onSaved}/><details className="section-gap"><summary>Case discussion notes</summary><DiscussionThread patientId={patient.id} entries={discussion} onSaved={onSaved}/></details>{detail.review_history?.length>0&&<section className="card"><div className="card-body"><h2>Previous committee decisions</h2>{detail.review_history.map(r=>{let old={};try{old=JSON.parse(r.snapshot_json)}catch{}return <div className="lookup-result" key={r.id}><div><b>{old.decision||'Committee review without final decision'}</b><p className="tiny muted">{r.created_at} · {r.actor} · {r.reason}</p><p className="tiny">{old.decision_notes}</p></div></div>})}</div></section>}</>}
    {tab === 'decision' && <ImplementationPanel patient={patient} followUps={detail.follow_ups||[]} onSaved={onSaved}/>}
    {tab === 'source' && <SourceRecord original={original} />}
    {!visibleTabs.some(([key]) => key === tab) && <p className="notice">Unknown patient section. Choose a tab above.</p>}
  </div></>;
}
