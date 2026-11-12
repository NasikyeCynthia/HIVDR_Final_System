import PatientLookup from '../components/patients/PatientLookup.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import LaboratoryOverview from '../components/dashboard/LaboratoryOverview.jsx';
import PatientList from '../components/patients/PatientList.jsx';
export default function LabResultsPage() {
  const { visiblePatients } = useWorkspace();
  return <><PageHeader title="Lab results" description="Track specimen choice, amplification, usable results and repeat-sample requests."  /><PatientLookup title="Enter a lab result for an existing patient"/><div className="section-gap"><LaboratoryOverview patients={visiblePatients} /></div><div className="notice info">To add or update a result, search for the patient above or choose “Enter / update result” in the list. Only laboratory staff can request DR tests and record samples and results; failed tests can request a repeat sample. Patients are registered in Patient records.</div><PatientList patients={visiblePatients} tab="laboratory" /></>;
}
