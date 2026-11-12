import { useAuth, useCan } from '../../contexts/AuthContext.jsx';
import { workflowService } from '../../services/workflowService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';
import ViewOnly from '../common/ViewOnly.jsx';

// The psychosocial support (PSS) factors of the MoH HIVDR database; recommendations follow the
// MoH PSS service packages (Desktop Job Aid 2020). They guide counselling and are not risk points.
const FACTORS = ['Non-disclosure', 'Denial/coping with results', 'Anger/Stress', 'Stigma & discrimination', 'Bereavement',
  'Dysfunctional family/client support system', 'Harmful habits (Alcohol & substance abuse)', 'Risky sexual behaviours',
  'Lack of life-survival skills', 'Transition challenges', 'Economic challenges/poverty', 'Had 1 or no meal/day', 'Malnourished',
  'Spiritual issues (Religious beliefs, Drug holidays etc)', 'Fear/Anxiety'];

export function PsychosocialRecommendations({ items = [] }) {
  if (!items.length) return <p className="muted">No psychosocial barriers recorded.</p>;
  return <div className="table-wrap"><table><thead><tr><th>Barrier</th><th>Recommended support</th></tr></thead><tbody>
    {items.map(r => <tr key={r.factor}><td>{r.factor}</td><td>{r.action}</td></tr>)}</tbody></table></div>;
}

export default function PsychosocialForm({ patient, onSaved }) {
  const { user } = useAuth();
  const can = useCan();
  const action = usePatientAction(onSaved);
  const data = patient.psychosocial || {};
  const permitted = can('record_psychosocial', patient);
  const assignedOk = !patient.assigned_to || patient.assigned_to === user.id;
  function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    action.run(() => workflowService.psychosocial(patient.id, { assessed: f.has('assessed'), factors: f.getAll('factors'), notes: f.get('notes') }), 'Assessment saved');
  }
  return <>
    <Card title="Recommended psychosocial support" subtitle="From the MoH psychosocial support service packages">
      <PsychosocialRecommendations items={patient.psychosocial_recommendations} />
    </Card>
    <Card title="Psychosocial and adherence assessment" subtitle="Required before the committee can decide">
      <Feedback error={action.error} success={action.success} />
      {!permitted && <ViewOnly action="record_psychosocial" />}
      {permitted && !assignedOk && <ViewOnly>This patient is assigned to another nurse or counsellor.</ViewOnly>}
      <form onSubmit={submit}><fieldset disabled={!permitted || !assignedOk || action.busy}>
        <label className="checkbox"><input type="checkbox" name="assessed" defaultChecked={data.assessed} />Assessment completed</label>
        <div className="check-grid">{FACTORS.map(f => <label className="checkbox" key={f}><input type="checkbox" name="factors" value={f} defaultChecked={data.factors?.includes(f)} />{f}</label>)}</div>
        <p className="tiny muted">Also ask the two depression questions (little interest or pleasure; feeling down or hopeless in the past 2 weeks). If both are “yes”, refer for mental-health review. Use HEADSS for adolescents.</p>
        <label htmlFor="psy-notes">Assessment notes and agreed follow-up</label><textarea id="psy-notes" name="notes" defaultValue={data.notes || ''} maxLength="5000" />
        {permitted && assignedOk && <button className="btn" style={{ marginTop: 15 }}>Save assessment</button>}
      </fieldset></form>
    </Card>
  </>;
}
