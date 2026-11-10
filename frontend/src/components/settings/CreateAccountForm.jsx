import { useState } from 'react';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import { operationsService } from '../../services/operationsService.js';
import { getFacilityGroups } from '../../utils/facilityOptions.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';

export default function CreateAccountForm() {
  const { patients, refresh } = useWorkspace();
  const groups = getFacilityGroups(patients);
  const [error, setError] = useState('');
  const [created, setCreated] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setBusy(true);
    setError('');
    try {
      setCreated(await operationsService.account(data));
      await refresh();
      form.reset();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return <Card title="Create an individual staff account" className="section-gap">
    <Feedback error={error} />
    <p className="tiny muted">
      Choose the staff member’s hospital from the Original dataset, or select the Synthetic demo facility.
      The account can edit clinical records only at its assigned hospital.
    </p>
    <form onSubmit={submit}>
      <div className="form-grid">
        <div><label htmlFor="new-username">Username</label><input id="new-username" name="username" required minLength={3} pattern="[a-zA-Z0-9_.-]+" /></div>
        <div><label htmlFor="new-name">Staff name</label><input id="new-name" name="name" required /></div>
        <div><label htmlFor="new-role">Role</label><select id="new-role" name="role"><option value="nurse">Nurse</option><option value="counsellor">Counsellor</option><option value="lab">Laboratory</option><option value="clinician">Clinician</option></select></div>
        <div>
          <label htmlFor="new-facility">Healthcare facility</label>
          <select id="new-facility" name="facility" required defaultValue="">
            <option value="" disabled>Select a facility</option>
            <optgroup label="Original data facilities">{groups.original.map(facility => <option key={facility} value={facility}>{facility}</option>)}</optgroup>
            <optgroup label="Synthetic demo facility">{groups.synthetic.map(facility => <option key={facility} value={facility}>{facility}</option>)}</optgroup>
          </select>
        </div>
      </div>
      <div className="form-actions"><button className="btn" disabled={busy}>Create account</button></div>
    </form>
    {created && <div className="notice info">
      <p>Account: <b>{created.username}</b></p>
      <label htmlFor="created-password">Generated password (shown once)</label>
      <input id="created-password" readOnly value={created.password} />
      <p className="tiny">{created.message}</p>
      <button className="text-link" onClick={() => setCreated(null)}>Hide credentials</button>
    </div>}
  </Card>;
}
