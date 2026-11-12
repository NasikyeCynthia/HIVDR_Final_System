import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import ViewOnly from '../common/ViewOnly.jsx';
import { patientService } from '../../services/patientService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import FormField from '../common/FormField.jsx';
import Feedback from '../common/Feedback.jsx';
export default function ProfileForm({ patient, onSaved }) {
  const { user } = useAuth();
  const can = useCan();
  const action = usePatientAction(onSaved);
  const permitted = can('edit_patient_record', patient);
  function submit(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    data.expected_version=patient.data_version||0;
    for (const key of ['age', 'viral_load', 'adherence', 'treatment_line']) data[key] = data[key] === '' ? null : Number(data[key]);
    action.run(() => patientService.updateProfile(patient.id, data));
  }
  return <Card title="Clinical and patient information"><Feedback error={action.error} success={action.success} />{!permitted && <ViewOnly action="edit_patient_record" />}<form onSubmit={submit}><fieldset disabled={!permitted || action.busy}>
    <div className="form-grid"><FormField label="Patient display name" name="name" defaultValue={patient.name} required />
      <FormField label="Age (years)" name="age" type="number" min="0" max="120" step="any" defaultValue={patient.age ?? ''} />
      <FormField label="Sex" name="sex"><select id="sex" name="sex" defaultValue={patient.sex || ''}><option value="">Not recorded</option><option value="F">Female</option><option value="M">Male</option><option value="X">Other / recorded X</option></select></FormField>
      <FormField label="Current regimen" name="regimen" defaultValue={patient.regimen || ''} />
      <FormField label="Treatment line" name="treatment_line"><select id="treatment_line" name="treatment_line" defaultValue={patient.treatment_line || ''}><option value="">Not recorded</option><option value="1">First line</option><option value="2">Second line</option><option value="3">Third line</option></select></FormField>
      <FormField label="Latest viral load (copies/mL)" name="viral_load" type="number" min="0" step="any" defaultValue={patient.viral_load ?? ''} />
      <FormField label="Adherence (%)" name="adherence" type="number" min="0" max="100" step="any" defaultValue={patient.adherence ?? ''} />
      <FormField label="Care notes" name="notes" full><textarea id="notes" name="notes" maxLength="5000" defaultValue={patient.notes || ''} /></FormField>
    </div><div className="form-actions"><button className="btn">{action.busy ? 'Saving…' : 'Save profile'}</button></div>
  </fieldset></form></Card>;
}
