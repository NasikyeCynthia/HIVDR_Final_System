import {useWorkspace} from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import ResistancePatientList from '../components/resistance/ResistancePatientList.jsx';
import StanfordConnection from '../components/resistance/StanfordConnection.jsx';
export default function ResistanceClassificationPage(){const {visiblePatients}=useWorkspace();return <><PageHeader title="Resistance classification" description="Review regimen, drug exposure and drug-specific resistance, including drugs outside the current regimen."/><StanfordConnection/><ResistancePatientList patients={visiblePatients}/></>}
