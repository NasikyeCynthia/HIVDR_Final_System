import ModelReport from '../components/settings/ModelReport.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import RiskChart from '../components/dashboard/RiskChart.jsx';
import EligibilityChart from '../components/dashboard/EligibilityChart.jsx';
import PatientList from '../components/patients/PatientList.jsx';

export default function RiskAssessmentPage() {
  const { visiblePatients: patients } = useWorkspace();
  const flagged = patients.filter(p => p.risk?.flagged).length;
  const due = patients.filter(p => p.eligibility?.status === 'eligible' && !p.referred_at).length;
  return <>
    <PageHeader title="Risk assessment" description={`${flagged} patient(s) flagged at high risk of drug resistance · ${due} eligible for a DR test and not yet requested.`} />
    <div className="grid-half"><RiskChart patients={patients} /><EligibilityChart patients={patients} /></div>
    <PatientList patients={patients} tab="risk" />

  </>;
}
