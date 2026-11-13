import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import PatientList from '../components/patients/PatientList.jsx';
import RegisterPatientForm from '../components/patients/RegisterPatientForm.jsx';
export default function PatientRecordsPage() {
  const { user } = useAuth();
  const { visiblePatients } = useWorkspace();
  const [params] = useSearchParams();
  const [registering, setRegistering] = useState(params.get('register') === '1');
  const filter = params.get('filter') || '';
  const cohort = params.get('cohort');
  const cohortPatients = cohort === 'eligible' ? visiblePatients.filter(p=>p.eligibility?.status==='eligible'||p.referred_at) : cohort === 'reviewed' ? visiblePatients.filter(p=>p.reviewed_at) : visiblePatients;
  const canRegister = ['nurse', 'counsellor'].includes(user.role);
  return <><PageHeader title="Patient records" description="Complete dataset in its original column order, with risk scores and DR-test eligibility." action={canRegister && <button className="btn" onClick={() => setRegistering(true)}>+ Register patient</button>} />{registering && <RegisterPatientForm onCancel={() => setRegistering(false)} />}<PatientList key={filter} patients={cohortPatients} initialFilter={filter} datasetView /></>;
}
