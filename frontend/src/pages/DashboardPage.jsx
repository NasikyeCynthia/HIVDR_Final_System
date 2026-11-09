import { Link } from 'react-router-dom';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import StatisticsCard from '../components/dashboard/StatisticsCard.jsx';
import ProcessCascade from '../components/dashboard/ProcessCascade.jsx';
import ClinicalCascade from '../components/dashboard/ClinicalCascade.jsx';
import DecisionChart from '../components/dashboard/DecisionChart.jsx';
import ProfileCompleteness from '../components/dashboard/ProfileCompleteness.jsx';
import LaboratoryOverview from '../components/dashboard/LaboratoryOverview.jsx';
import PatientTable from '../components/patients/PatientTable.jsx';
export default function DashboardPage() {
  const { visiblePatients: patients, rules } = useWorkspace();
  return <><PageHeader title="Surveillance overview" description="From patient identification to implemented care — every step in view." /><div className="stats">
    <StatisticsCard title="Patient records" value={patients.length} description="Within selected source" icon="♙" />
    <StatisticsCard title="Usable laboratory results" value={patients.filter(p => p.status === 'Usable result').length} description="Results available for review" icon="⌕" filter="usable" />
    <StatisticsCard title="Awaiting clinical review" value={patients.filter(p => p.status === 'Usable result' && !p.reviewed_at).length} description="Usable results awaiting action" icon="☷" filter="awaiting-review" />
    <StatisticsCard title="Incomplete profiles" value={patients.filter(p => !p.pre_complete).length} description="Before clinical discussion" icon="◇" filter="missing-pre" />
  </div><div className="notice">{rules?.notice} Factor scores are preserved. Overall classification and automatic referral remain pending.</div>
    <div className="grid-two"><ProcessCascade patients={patients} /><ClinicalCascade patients={patients} /></div>
    <div className="grid-half"><DecisionChart patients={patients} /><ProfileCompleteness patients={patients} /></div>
    <div className="grid-half"><LaboratoryOverview patients={patients} /><Card title="Needs attention" subtitle="Operational follow-through"><Link className="clinical-row" to="/patients?filter=failed"><span>Unsuccessful tests</span><span /><b>{patients.filter(p => ['Unamplified', 'Sequencing failed'].includes(p.status)).length}</b></Link><Link className="clinical-row" to="/patients?filter=awaiting-implementation"><span>Decision not implemented</span><span /><b>{patients.filter(p => p.decision && !p.implemented_at).length}</b></Link><Link className="text-link" to="/notifications">Open work queue →</Link></Card></div>
    <Card title="Patient activity" subtitle="Open a record to see missing fields and the responsible care worker" action={<Link className="text-link" to="/patients">All records →</Link>}><PatientTable patients={patients.slice(0, 6)} /></Card>
  </>;
}
