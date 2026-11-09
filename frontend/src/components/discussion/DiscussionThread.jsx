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
    event.preventDefault(); const form = event.currentTarget; const body = new FormData(form).get('body');
    if (await action.run(() => discussionService.add(patientId, body), 'Discussion entry added')) form.reset();
  }
  return <Card title="Patient discussion">{entries.length ? entries.map(entry => <article className="discussion-entry" key={entry.id}><b>{entry.author_name}</b> <span className="tiny muted">{formatDate(entry.created_at)}</span><p>{entry.body}</p></article>) : <p className="muted">No discussion entries yet.</p>}<Feedback error={action.error} success={action.success} />{['nurse', 'counsellor', 'clinician'].includes(user.role) ? <form onSubmit={submit} style={{ marginTop: 20 }}><label htmlFor="body">New discussion entry</label><textarea id="body" name="body" required maxLength="5000" placeholder="Record observations and review notes…" /><div className="form-actions"><button className="btn" disabled={action.busy}>Add entry</button></div></form> : <p className="tiny muted">Only clinical roles can contribute discussion entries.</p>}</Card>;
}
