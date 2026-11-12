import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import PatientList from '../components/patients/PatientList.jsx';
import DiscussionStatus from '../components/dashboard/DiscussionStatus.jsx';
export default function DiscussionPage() {
  const { visiblePatients } = useWorkspace();
  return <><PageHeader title="Discussion" description="Patient-specific clinical discussions, decisions and follow-through." /><div className="notice info">Open a record to contribute to its discussion. The Decision tab allows clinician approval and implementation tracking.</div><div className="section-gap"><DiscussionStatus patients={visiblePatients} /></div><PatientList patients={visiblePatients} tab="discussion" /></>;
}
