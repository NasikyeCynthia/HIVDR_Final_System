import AccountabilitySummary from '../components/dashboard/AccountabilitySummary.jsx';
import RiskChart from '../components/dashboard/RiskChart.jsx';
import EligibilityChart from '../components/dashboard/EligibilityChart.jsx';
import HivdrCascade from '../components/dashboard/HivdrCascade.jsx';
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
        ? 'Changing this setting updates the dataset for every role. Facility selection controls which records are in view.'
        : 'This is the dataset selected by your administrator. You can change the facility in the toolbar above.'}</p>
    </div>
  </Card>;
}

export default function DashboardPage() {
  const { visiblePatients: patients, users } = useWorkspace();
  const preDiscussion = patients.filter(patient => patient.amplified === 1 && patient.discussion_status === 'Pending');
  const postDecision = patients.filter(patient => patient.discussion_status === 'Done');
  const preIncomplete = preDiscussion.filter(patient => !patient.pre_complete);
  const postIncomplete = postDecision.filter(patient => !patient.post_complete);
  const usable = patients.filter(patient => patient.status === 'Usable result');
  const awaitingReview = usable.filter(patient => !patient.reviewed_at);

  return <>
    <PageHeader title="Surveillance overview" description="From patient identification to implemented care — every step in view." />
    <SharedDatasetSelector />
    <div className="stats">
      <StatisticsCard title="Patient records" value={patients.length} description="Within selected source and facility" icon="♙" />
      <StatisticsCard title="Flagged high risk" value={patients.filter(p => p.risk?.flagged).length} description="High risk of drug resistance" icon="◆" filter="flagged" />
      <StatisticsCard title="Usable laboratory results" value={usable.length} description="Results available for review" icon="⌕" filter="usable" />
      <StatisticsCard title="Awaiting clinical review" value={awaitingReview.length} description="Usable results awaiting action" icon="☷" filter="awaiting-review" />
      <StatisticsCard title="Profiles incomplete before discussion" value={preIncomplete.length} description="Patient details to complete" icon="◇" filter="missing-pre" />
      <StatisticsCard title="Profiles incomplete after discussion" value={postIncomplete.length} description="Committee follow-up to complete" icon="◇" filter="missing-post" />
    </div>
    <div className="grid-two"><ProcessCascade patients={patients} /><ClinicalCascade patients={patients} /></div>
    <div className="grid-half"><DecisionChart patients={patients} /><RiskChart patients={patients} /></div>
    <div className="grid-half"><EligibilityChart patients={patients} /><HivdrCascade patients={patients} /></div>
    <div className="section-gap"><ProfileCompleteness patients={patients} /></div>
    <div className="grid-half"><LaboratoryOverview patients={patients} /><Card title="Needs attention" subtitle="Operational follow-through">
      <Link className="clinical-row" to="/patients?filter=failed"><span>Unsuccessful tests</span><span /><b>{patients.filter(p => ['Unamplified', 'Sequencing failed'].includes(p.status)).length}</b></Link>
      <Link className="clinical-row" to="/patients?filter=awaiting-implementation"><span>Decision not implemented</span><span /><b>{patients.filter(p => p.decision && !p.implemented_at).length}</b></Link>
      <Link className="clinical-row" to="/patients?filter=flagged"><span>Flagged: high risk of resistance</span><span /><b>{patients.filter(p => p.risk?.flagged).length}</b></Link>
      <Link className="clinical-row" to="/patients?filter=elig:eligible"><span>Eligible, DR test not yet requested</span><span /><b>{patients.filter(p => p.eligibility?.status === 'eligible' && !p.referred_at).length}</b></Link>
      <Link className="clinical-row" to="/patients?filter=returned"><span>Samples rejected or deferred</span><span /><b>{patients.filter(p => ['Rejected', 'Deferred'].includes(p.status)).length}</b></Link>
      <Link className="text-link" to="/notifications">Open work queue →</Link>
    </Card></div>
    <div className="section-gap"><AccountabilitySummary patients={patients} users={users}/></div>
  </>;
}
