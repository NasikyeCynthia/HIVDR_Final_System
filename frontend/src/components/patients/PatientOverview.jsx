import { workflowService } from '../../services/workflowService.js';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { patientService } from '../../services/patientService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import { formatDate, formatNumber } from '../../utils/format.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';

export default function PatientOverview({ patient, users, onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  const owner = users.find(person => person.id === patient.assigned_to)?.name || 'Unassigned';
  const labOwner = users.find(person => person.id === patient.lab_owner)?.name || 'Unassigned';
  const facts = [
    ['Age / sex', `${patient.age ?? 'Unknown'} / ${patient.sex || 'Unknown'}`],
    ['Regimen', patient.regimen || 'Missing'],
    ['Care worker', owner],
    ...([['Laboratory officer', labOwner]]),
    ['Viral load', `${formatNumber(patient.viral_load)} copies/mL`],
    ['Adherence', patient.adherence == null ? 'Missing' : `${patient.adherence}%`],
  ];

  function assign(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    action.run(() => patientService.assign(patient.id, data.get('assigned_to')), 'Care worker assigned');
  }

  return <>
    <Card title="Patient at a glance">
      <div className="detail-list">{facts.map(([label, value]) => <div key={label}><label>{label}</label>{value}</div>)}</div>
    </Card>
    <Card title="Profile completion">
      <div className={`notice ${patient.pre_complete ? 'info' : ''}`}>
        Pre-discussion: {patient.pre_complete ? 'complete' : `missing ${patient.missing_pre.join(', ')}`}
      </div>
      {(patient.reviewed_at
        ? <div className="notice">Post-discussion: {patient.post_complete ? 'complete' : `missing ${patient.missing_post.join(', ')}`}</div>
        : <p className="tiny muted">Post-discussion requirements apply after clinical review.</p>)}
      <Feedback error={action.error} success={action.success} />
      {user.role === 'admin' && <form onSubmit={assign}>
        <label htmlFor="assigned_to">Assigned nurse / counsellor</label>
        <select id="assigned_to" name="assigned_to" defaultValue={patient.assigned_to || ''} required>
          <option value="">Choose a care worker…</option>
          {users.filter(person => ['nurse', 'counsellor'].includes(person.role) && person.facility === patient.facility)
            .map(person => <option key={person.id} value={person.id}>{person.name}</option>)}
        </select>
        <div className="form-actions"><button className="btn" disabled={action.busy}>Save assignment</button></div>
      </form>}
      {user.role === 'admin' && <form style={{ marginTop: 20 }} onSubmit={event => {
        event.preventDefault();
        const id = new FormData(event.currentTarget).get('lab_owner');
        action.run(() => workflowService.assignLab(patient.id, id), 'Laboratory officer assigned');
      }}>
        <label htmlFor="lab_owner">Responsible laboratory officer</label>
        <select id="lab_owner" name="lab_owner" defaultValue={patient.lab_owner || ''} required>
          <option value="">Choose laboratory officer…</option>
          {users.filter(person => person.role === 'lab' && person.facility === patient.facility)
            .map(person => <option key={person.id} value={person.id}>{person.name}</option>)}
        </select>
        <button className="btn" style={{ marginTop: 12 }} disabled={action.busy}>Save laboratory assignment</button>
      </form>}
    </Card>
    {<Card title="Care journey"><div className="timeline">
      {[
        ['Registered', patient.created_at], ['Referred for DRT', patient.referred_at],
        ['Sample collected', patient.sample_at], ['Laboratory report', patient.report_at],
        ['Reviewed', patient.reviewed_at], ['Implemented', patient.implemented_at],
      ].map(([label, stamp]) => <div className="timeline-item" key={label}>{label}<small>{formatDate(stamp)}</small></div>)}
    </div></Card>}
  </>;
}
