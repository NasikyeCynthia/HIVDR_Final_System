import { useState } from 'react';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import { workflowService } from '../../services/workflowService.js';
import { getFacilityGroups } from '../../utils/facilityOptions.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';

function FacilityOptions({ groups, currentFacility }) {
  const known = [...groups.original, ...groups.synthetic];
  return <>
    {currentFacility && !known.includes(currentFacility) && <optgroup label="Current assignment">
      <option value={currentFacility}>{currentFacility}</option>
    </optgroup>}
    <optgroup label="Original data facilities">
      {groups.original.map(facility => <option key={facility} value={facility}>{facility}</option>)}
    </optgroup>
    <optgroup label="Synthetic demo facility">
      {groups.synthetic.map(facility => <option key={facility} value={facility}>{facility}</option>)}
    </optgroup>
  </>;
}

export default function UserManagement() {
  const { users, patients, refresh } = useWorkspace();
  const groups = getFacilityGroups(patients);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event, user) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await workflowService.updateUser(user.id, {
        name: form.get('name'),
        facility: form.get('facility'),
        can_access_all: user.role === 'nurse' || form.has('all'),
      });
      setSuccess('Account updated. That user must sign in again.');
      await refresh();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return <Card title="Staff names, facilities and access" className="section-gap">
    <Feedback error={error} success={success} />
    <p className="tiny muted">
      Assign each account to a hospital from the Original dataset or to the Synthetic demo facility.
      Nurses can view all facilities in the active dataset; they can edit records only at their assigned hospital.
      Other roles can be granted all-facility viewing here. Changes revoke that user’s active sessions.
    </p>
    {users.map(user => <form key={user.id} onSubmit={event => submit(event, user)} className="user-form">
      <b>{user.role}</b>
      <input aria-label={`${user.role} name`} name="name" defaultValue={user.name} required />
      <select aria-label={`${user.role} facility`} name="facility" defaultValue={user.facility} required>
        <FacilityOptions groups={groups} currentFacility={user.facility} />
      </select>
      <label className="checkbox">
        <input type="checkbox" name="all" defaultChecked={user.role === 'nurse' || Boolean(user.can_access_all)} disabled={user.role === 'nurse'} />{user.role === 'lab' ? 'Central laboratory (CPHL / DR lab): records lab steps for all facilities' : 'All facilities'}
      </label>
      <button className="btn small" disabled={busy}>Save</button>
    </form>)}
  </Card>;
}
