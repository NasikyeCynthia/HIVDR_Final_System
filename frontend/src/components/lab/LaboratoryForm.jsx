import { useAuth } from '../../contexts/AuthContext.jsx';
import { labService } from '../../services/labService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import { formatDate } from '../../utils/format.js';
import Card from '../common/Card.jsx';
import FormField from '../common/FormField.jsx';
import Feedback from '../common/Feedback.jsx';
export default function LaboratoryForm({ patient, users, onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  const canEdit = user.role === 'lab' && patient.facility === user.facility && !patient.reviewed_at;
  function submit(event) { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); action.run(() => labService.save(patient.id, data)); }
  return <Card title="Sample and laboratory result"><div className="detail-list" style={{ marginBottom: 20 }}><div><label>Laboratory officer</label>{users.find(person => person.id === patient.lab_owner)?.name || 'Unassigned'}</div><div><label>Repeat sample requested</label>{formatDate(patient.repeat_requested_at)}</div></div>{!canEdit && <div className="notice info">{patient.reviewed_at ? 'This episode has been reviewed; its laboratory result is locked.' : 'Only laboratory personnel can update this section.'}</div>}<Feedback error={action.error} success={action.success} /><form onSubmit={submit}><fieldset disabled={!canEdit || action.busy}><div className="form-grid">
    <FormField label="Specimen type" name="sample_type"><select id="sample_type" name="sample_type" defaultValue={patient.sample_type || ''} required><option value="">Choose specimen…</option><option value="Plasma">Plasma</option><option value="DBS">DBS</option></select></FormField>
    <FormField label="Laboratory outcome" name="status"><select id="status" name="status" defaultValue={patient.status === 'Not collected' ? '' : patient.status} required><option value="">Choose outcome…</option><option value="Pending">Awaiting result</option><option value="Usable result">Amplified · usable result</option><option value="Unamplified">Unamplified</option><option value="Sequencing failed">Amplified · sequencing failed</option></select></FormField>
    <FormField label="Reason for using DBS (required for DBS)" name="dbs_reason" full><textarea id="dbs_reason" name="dbs_reason" maxLength="3000" defaultValue={patient.dbs_reason || ''} /></FormField>
    <FormField label="Reason for unsuccessful test" name="failure_reason" full><textarea id="failure_reason" name="failure_reason" maxLength="3000" defaultValue={patient.failure_reason || ''} /></FormField>
    <FormField label="Recorded mutations / laboratory evidence" name="mutations" full><textarea id="mutations" name="mutations" maxLength="15000" defaultValue={patient.mutations || ''} /></FormField>
  </div><div className="form-actions"><button className="btn">Save laboratory record</button><button type="button" className="btn secondary" disabled={!['Unamplified', 'Sequencing failed'].includes(patient.status)} onClick={() => action.run(() => labService.requestRepeat(patient.id), 'New sample requested')}>Request new sample</button></div></fieldset></form><p className="tiny muted" style={{ marginTop: 20 }}>Saving a new result archives the previous laboratory state. Repeat-sample requests remain tracked.</p></Card>;
}
