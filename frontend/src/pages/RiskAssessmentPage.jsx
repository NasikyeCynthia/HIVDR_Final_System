import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import PatientList from '../components/patients/PatientList.jsx';
export default function RiskAssessmentPage() {
  const { visiblePatients, rules } = useWorkspace();
  return <><PageHeader title="Risk assessment" description="Your transparent scoring rules, with factor contributions for each patient." /><div className="notice">{rules?.notice} Factor totals are calculated; overall categories remain unresolved.</div><Card title="Scoring factors" className="section-gap"><table className="rule-table"><thead><tr><th>Factor</th><th>Low · 0</th><th>Moderate · 30</th><th>High · 60</th></tr></thead><tbody><tr><td>Viral load (copies/mL)</td><td>&lt;200</td><td>200–999</td><td>≥1,000</td></tr><tr><td>Adherence</td><td>100%</td><td>85% to &lt;100%</td><td>&lt;85%</td></tr><tr><td>Treatment line</td><td>First line</td><td>Second line</td><td>Third line</td></tr></tbody></table></Card><Card title="Machine-learning readiness" className="section-gap"><p className="muted">No model is connected. Future predictions will be displayed separately from the rules-based score, using validated pre-DRT features and real laboratory outcomes.</p></Card><PatientList patients={visiblePatients} tab="risk" /></>;
}
