import { useAuth } from '../../contexts/AuthContext.jsx';
import { discussionService } from '../../services/discussionService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import { formatDate } from '../../utils/format.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';
export default function DiscussionThread({ patientId, entries, onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  async function submit(event) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    const lines = [
      ['Adherence review', data.get('adherence')],
      ['Regimen review', data.get('regimen_review')],
      ['Psychosocial barriers / supports', data.get('psychosocial')],
      ['Discussion notes and follow-up', data.get('body')],
    ].filter(([, value]) => value?.trim()).map(([label, value]) => `${label}: ${value.trim()}`);
    const body = lines.join('\n\n');
    if (await action.run(() => discussionService.add(patientId, body), 'Discussion entry added')) form.reset();
  }
  return <Card title="Patient discussion">{entries.length ? entries.map(entry => <article className="discussion-entry" key={entry.id}><b>{entry.author_name}</b> <span className="tiny muted">{formatDate(entry.created_at)}</span><p>{entry.body}</p></article>) : <p className="muted">No discussion entries yet.</p>}<Feedback error={action.error} success={action.success} />{['nurse', 'counsellor', 'clinician'].includes(user.role) ? <form onSubmit={submit} style={{ marginTop: 20 }}>
    <h3>Structured case discussion</h3>
    <div className="form-grid">
      <div className="field"><label htmlFor="adherence">Adherence review</label><select id="adherence" name="adherence" defaultValue=""><option value="">Not discussed</option><option>Adherence concerns reported</option><option>No current adherence concerns reported</option><option>Needs further assessment</option><option>Support offered / follow-up planned</option></select></div>
      <div className="field"><label htmlFor="regimen_review">Regimen adequacy / action</label><select id="regimen_review" name="regimen_review" defaultValue=""><option value="">Not discussed</option><option>Current regimen maintained</option><option>Substitution considered</option><option>Regimen switched after clinical review</option><option>Awaiting evidence or further review</option></select></div>
      <div className="field full"><label htmlFor="psychosocial">Psychosocial factors, barriers or supports</label><textarea id="psychosocial" name="psychosocial" maxLength="1500" placeholder="Record relevant factors and supports discussed…" /></div>
      <div className="field full"><label htmlFor="body">Notes and follow-up plan</label><textarea id="body" name="body" required maxLength="2500" placeholder="Record the discussion, agreed next steps, and follow-up…" /></div>
    </div>
    <p className="tiny muted">These prompts document the discussion; they do not make or approve a treatment decision.</p>
    <div className="form-actions"><button className="btn" disabled={action.busy}>Add entry</button></div>
  </form> : <div className="notice info"><b>Structured discussion template</b><p>Clinical roles can document adherence review, regimen adequacy or action, psychosocial barriers and supports, and notes with a follow-up plan. Your current role is read-only for patient discussions.</p></div>}</Card>;
}
