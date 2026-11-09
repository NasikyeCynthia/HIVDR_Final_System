import Card from '../common/Card.jsx';
import { RiskBadge } from '../common/Badge.jsx';
import Feedback from '../common/Feedback.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { riskService } from '../../services/riskService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
export default function RiskSummary({ patient, onSaved }) {
  const { user } = useAuth();
  const action = usePatientAction(onSaved);
  return <Card title="Risk assessment"><div className="notice">{patient.risk.notice} Overall categories await clarification; no category is silently inferred.</div><div className="score-grid">{patient.risk.factors.map(factor => <div className="score-box" key={factor.name}><span>{factor.name}</span><strong>{factor.points ?? '—'}</strong><span>{factor.value ?? 'Not recorded'}</span></div>)}</div><div className="split-heading" style={{ marginTop: 24 }}><span>Total: <b>{patient.risk.total ?? 'Incomplete'}</b></span><RiskBadge risk={patient.risk} /></div><p className="tiny muted">Scoring version: {patient.risk.version}. Factor weights remain high 60, moderate 30, low 0.</p><Feedback error={action.error} success={action.success} /><button className="btn" disabled={!patient.risk.eligible || action.busy || !['nurse', 'counsellor', 'clinician'].includes(user.role)} onClick={() => action.run(() => riskService.refer(patient.id), 'Referral recorded')}>Refer for DRT</button></Card>;
}
