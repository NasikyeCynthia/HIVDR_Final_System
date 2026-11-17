import { Link } from 'react-router-dom';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import RiskChart from '../components/dashboard/RiskChart.jsx';
import EligibilityChart from '../components/dashboard/EligibilityChart.jsx';
import PatientList from '../components/patients/PatientList.jsx';

export default function RiskAssessmentPage() {
  const { visiblePatients: patients } = useWorkspace();
  const flagged = patients.filter(p => p.risk?.flagged).length;
  const due = patients.filter(p => p.eligibility?.status === 'eligible' && !p.referred_at).length;
  return <>
    <PageHeader title="Risk assessment" description={`${flagged} patient(s) flagged at high risk of drug resistance · ${due} eligible for a DR test and not yet requested.`} />
    <section className="risk-output-guide" aria-label="Three different assessment outputs">
      <div><h2>Risk score · points</h2><p>Prioritises review using viral load, adherence and treatment line.</p></div>
      <div><h2>DR-test eligibility</h2><p>Shows whether the documented criteria for requesting a test are met.</p></div>
      <div><h2>ML estimate · research</h2><p>Estimates resistance probability. It does not determine test eligibility.</p></div>
    </section>
    <p className="tiny muted"><Link className="text-link" to="/help#risk-assessment">How to read these results →</Link></p>
    <div className="grid-half"><RiskChart patients={patients} /><EligibilityChart patients={patients} /></div>
    <PatientList patients={patients} tab="risk" />

  </>;
}
