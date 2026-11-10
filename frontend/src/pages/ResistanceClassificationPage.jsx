import {useWorkspace} from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import PatientLookup from '../components/patients/PatientLookup.jsx';
import PatientList from '../components/patients/PatientList.jsx';
export default function ResistanceClassificationPage(){const {visiblePatients}=useWorkspace();return <><PageHeader title="Resistance classification" description="Interpret laboratory sequences or mutations using the Stanford HIVdb API."/><PatientLookup tab="resistance" title="Find patient for mutation interpretation"/><PatientList patients={visiblePatients} tab="resistance"/></>}
