import PatientLookup from '../components/patients/PatientLookup.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import LaboratoryOverview from '../components/dashboard/LaboratoryOverview.jsx';
import LabWorklist, { isLabWork } from '../components/lab/LabWorklist.jsx';

export default function LabResultsPage() {
  const { visiblePatients } = useWorkspace();
  const count = visiblePatients.filter(isLabWork).length;
  return <>
    <PageHeader title="Lab results" description={`The laboratory worklist: ${count.toLocaleString()} patients with a DR test to request, a sample to collect or follow, or a result.`} />
    <PatientLookup title="Find a patient to request a test or enter a sample or result" />
    <div className="section-gap"><LaboratoryOverview patients={visiblePatients} /></div>
    <LabWorklist patients={visiblePatients} />
  </>;
}
