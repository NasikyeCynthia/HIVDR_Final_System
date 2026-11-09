import { Link } from 'react-router-dom';
import { useWorkspace } from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import Badge from '../components/common/Badge.jsx';
export default function NotificationsPage() {
  const { visiblePatients } = useWorkspace();
  const rows = visiblePatients.map(patient => {
    const reasons = [];
    if (patient.missing_pre.length) reasons.push(`Missing profile: ${patient.missing_pre.join(', ')}`);
    if (['Unamplified', 'Sequencing failed'].includes(patient.status)) reasons.push(`Laboratory: ${patient.failure_reason || 'unsuccessful test; reason missing'}`);
    if (patient.status === 'Usable result' && !patient.reviewed_at) reasons.push('Usable result awaits clinician review');
    if (patient.decision && !patient.implemented_at) reasons.push('Approved decision awaits implementation');
    return { patient, reasons };
  }).filter(row => row.reasons.length);
  return <><PageHeader title="Notifications" description="A live work queue showing missing information, reasons and responsible care workers." /><Card title="Outstanding follow-up" action={<Badge color="yellow">{rows.length} records</Badge>}><div className="notification-list">{rows.slice(0, 200).map(({ patient, reasons }) => <article className="notification-item" key={patient.id}><div><b>{patient.name}</b><p className="tiny muted">{patient.external_id} · Care worker: {patient.owner_name || 'Unassigned'}</p><ul>{reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></div><Link className="text-link" to={`/patients/${patient.id}`}>Open →</Link></article>)}{!rows.length && <div className="empty">No outstanding follow-up for this source.</div>}{rows.length > 200 && <p className="tiny muted">Showing 200 records. Use Patient records to filter the full list.</p>}</div></Card><p className="tiny muted">This is an in-app queue. External notification delivery, acknowledgement and escalation schedules are not implemented.</p></>;
}
