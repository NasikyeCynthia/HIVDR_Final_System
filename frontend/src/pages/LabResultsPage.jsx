import PatientLookup from '../components/patients/PatientLookup.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import LaboratoryOverview from '../components/dashboard/LaboratoryOverview.jsx';
import PatientList from '../components/patients/PatientList.jsx';
import RegisterPatientForm from '../components/patients/RegisterPatientForm.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useState } from 'react';
export default function LabResultsPage() {
  const { visiblePatients } = useWorkspace();
  const { user } = useAuth();
  const [registering, setRegistering] = useState(false);
  const canRegister = ['nurse', 'counsellor'].includes(user.role);
  return <><PageHeader title="Lab results" description="Track specimen choice, amplification, usable results and repeat-sample requests." action={canRegister && <button className="btn" onClick={() => setRegistering(true)}>+ Register patient</button>} />{registering && <RegisterPatientForm onCancel={() => setRegistering(false)} />}<PatientLookup title="Enter a lab result for an existing patient"/><div className="section-gap"><LaboratoryOverview patients={visiblePatients} /></div><div className="notice info">To add or update a result, search for the patient above or choose “Enter / update result” in the list. Only laboratory personnel can save specimen and result changes; failed or unamplified results can request a repeat sample.</div><PatientList patients={visiblePatients} tab="laboratory" /></>;
}
