import { useAuth } from '../contexts/AuthContext.jsx';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import DataImportForm from '../components/settings/DataImportForm.jsx';
import AuditLog from '../components/settings/AuditLog.jsx';
export default function SettingsPage() {
  const { user } = useAuth();
  const { integrations } = useWorkspace();
  return <><PageHeader title="Settings" description="Data provenance, role permissions, integration readiness and audit history." /><div className="grid-half"><Card title="Import patient data"><p className="tiny muted">Imported columns remain intact in each source snapshot. Duplicate source + Patient No. records are skipped. Original files are not overwritten.</p>{user.role === 'admin' ? <DataImportForm /> : <div className="notice info">Administrator access is required to import data.</div>}</Card><Card title="Access permissions"><table><tbody><tr><td>Nurse / counsellor</td><td>Assigned profiles, discussion, implementation</td></tr><tr><td>Laboratory</td><td>Samples, results, repeat requests</td></tr><tr><td>Clinician</td><td>Discussion, approved decisions, implementation</td></tr><tr><td>Administrator</td><td>Imports, assignments and audit history</td></tr></tbody></table><p className="tiny muted">Identifiable patient access is scoped to the account’s facility.</p></Card></div><Card title="Integration status" className="section-gap"><div className="detail-list"><div><label>Stanford HIVdb</label>{integrations?.stanford?.message || 'Not connected'}</div><div><label>Machine learning</label>{integrations?.machine_learning?.message || 'Not connected'}</div><div><label>Backend</label>Python · FastAPI · SQLite</div><div><label>Frontend</label>React · JSX · Vite · HTML · CSS</div></div></Card>{user.role === 'admin' && <AuditLog />}</>;
}
