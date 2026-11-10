import AccountabilitySummary from '../components/dashboard/AccountabilitySummary.jsx';
import RiskChart from '../components/dashboard/RiskChart.jsx';
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
import PatientList from '../components/patients/PatientList.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';

function SharedDatasetSelector() {
  const { source, setSource, datasetSaving, canManageDataset } = useWorkspace();
  return <Card title="Dataset used across all roles" subtitle="The selected dataset stays active for everyone until an administrator changes it." className="section-gap">
    <div className="form-grid">
      <div>
        <label htmlFor="dashboard-dataset">Shared dataset</label>
        <select id="dashboard-dataset" value={source} disabled={!canManageDataset || datasetSaving} onChange={event => setSource(event.target.value).catch(() => {})}>
          <option value="original">Original data</option>
          <option value="synthetic">Synthetic demo</option>
        </select>
      </div>
      <p className="tiny muted">{canManageDataset
        ? 'Changing this setting updates the dataset for every role. Each account’s facility permissions still apply.'
        : 'This is the dataset selected by your administrator. Your account’s facility permissions still apply.'}</p>
    </div>
  </Card>;
}

export default function DashboardPage() {
  const { visiblePatients: patients, users } = useWorkspace();
  const { user } = useAuth();
  if (user.role === 'nurse') {
    const incompleteProfiles = patients.filter(patient => !patient.pre_complete);
    return <>
      <PageHeader title="Patient workspace" description="Review assigned patients and complete missing profile information." />
      <SharedDatasetSelector />
      <div className="stats">
        <StatisticsCard title="Patient records" value={patients.length} description="At your assigned facility" icon="♙" />
        <StatisticsCard title="Incomplete profiles" value={incompleteProfiles.length} description="Ready for your follow-up" icon="◇" filter="missing-pre" />
      </div>
      <ProfileCompleteness patients={patients} />
      <section className="section-gap"><h2>Profiles to complete</h2><p className="tiny muted">Open a patient to fill the missing profile fields.</p>
        <PatientList patients={incompleteProfiles} tab="profile" />
      </section>
    </>;
  }
  return <><PageHeader title="Surveillance overview" description="From patient identification to implemented care — every step in view." /><SharedDatasetSelector /><div className="stats">
    <StatisticsCard title="Patient records" value={patients.length} description="Within selected source" icon="♙" />
    <StatisticsCard title="Usable laboratory results" value={patients.filter(p => p.status === 'Usable result').length} description="Results available for review" icon="⌕" filter="usable" />
    <StatisticsCard title="Awaiting clinical review" value={patients.filter(p => p.status === 'Usable result' && !p.reviewed_at).length} description="Usable results awaiting action" icon="☷" filter="awaiting-review" />
    <StatisticsCard title="Incomplete profiles" value={patients.filter(p => !p.pre_complete).length} description="Before clinical discussion" icon="◇" filter="missing-pre" />
  </div><div className="grid-two"><ProcessCascade patients={patients} /><ClinicalCascade patients={patients} /></div>
    <div className="grid-half"><DecisionChart patients={patients} /><RiskChart patients={patients} /></div><div className="section-gap"><ProfileCompleteness patients={patients} /></div>
    <div className="grid-half"><LaboratoryOverview patients={patients} /><Card title="Needs attention" subtitle="Operational follow-through"><Link className="clinical-row" to="/patients?filter=failed"><span>Unsuccessful tests</span><span /><b>{patients.filter(p => ['Unamplified', 'Sequencing failed'].includes(p.status)).length}</b></Link><Link className="clinical-row" to="/patients?filter=awaiting-implementation"><span>Decision not implemented</span><span /><b>{patients.filter(p => p.decision && !p.implemented_at).length}</b></Link><Link className="text-link" to="/notifications">Open work queue →</Link></Card></div>
    <div className="section-gap"><AccountabilitySummary patients={patients} users={users}/></div>
  </>;
}
