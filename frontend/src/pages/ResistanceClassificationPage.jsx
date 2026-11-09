import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import PatientList from '../components/patients/PatientList.jsx';
export default function ResistanceClassificationPage() {
  const { visiblePatients, integrations } = useWorkspace();
  return <><PageHeader title="Resistance classification" description="Inspect mutation evidence and recorded drug-resistance classifications." /><Card title="Stanford HIVdb integration" className="section-gap"><div className="notice info">{integrations?.stanford?.message || 'Stanford integration is not connected.'}</div><p className="tiny muted">Open the source-record tab to inspect the imported Resistance to… and mutation columns. These are existing source values; the system has not submitted new Stanford analyses or generated clinical recommendations.</p></Card><PatientList patients={visiblePatients} tab="source" /></>;
}
