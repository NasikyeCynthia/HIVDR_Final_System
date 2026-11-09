import { useState } from 'react';
import { settingsService } from '../../services/settingsService.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';
export default function AuditLog() {
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function load() { setBusy(true); setError(''); try { setRows(await settingsService.audit()); } catch (failure) { setError(failure.message); } finally { setBusy(false); } }
  return <Card title="Audit history" action={<button className="text-link" disabled={busy} onClick={load}>{busy ? 'Loading…' : 'Load recent activity →'}</button>}><Feedback error={error} />{rows ? <div className="table-wrap"><table><thead><tr><th>When</th><th>Actor</th><th>Role</th><th>Action</th><th>Record</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>{row.created_at}</td><td>{row.actor}</td><td>{row.role}</td><td>{row.action}</td><td>{row.entity}</td></tr>)}</tbody></table></div> : <p className="tiny muted">Load the audit history to see who changed what and when.</p>}</Card>;
}
