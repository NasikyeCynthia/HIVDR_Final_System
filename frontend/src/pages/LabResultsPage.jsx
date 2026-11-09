import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import LaboratoryOverview from '../components/dashboard/LaboratoryOverview.jsx';
import PatientList from '../components/patients/PatientList.jsx';
export default function LabResultsPage() {
  const { visiblePatients } = useWorkspace();
  return <><PageHeader title="Lab results" description="Track specimen choice, amplification, usable results and repeat-sample requests." /><div className="section-gap"><LaboratoryOverview patients={visiblePatients} /></div><div className="notice info">Open a patient to enter results. DBS requires a reason; unsuccessful tests require a failure explanation. Only laboratory personnel can save those changes.</div><PatientList patients={visiblePatients} tab="laboratory" /></>;
}
