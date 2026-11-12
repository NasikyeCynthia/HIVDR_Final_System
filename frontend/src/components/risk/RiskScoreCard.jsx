import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
// The project's original points algorithm (backend: services/risk_service.py).
export const RISK_COLOR = { High: 'red', Intermediate: 'yellow', Low: 'green' };
export function RiskBadge({ risk }) {
  const category = risk?.category || 'Not assessed';
  return <Badge color={RISK_COLOR[category] || ''}>{category === 'Incomplete' ? 'Risk: incomplete' : `${category} risk`}{risk?.flagged ? ' · flagged' : ''}</Badge>;
}
export default function RiskScoreCard({ risk }) {
  if (!risk?.factors) return null;
  return <Card title="Risk of drug resistance" subtitle={`Points score · ${risk.version}`}>
    <div className="split-heading"><RiskBadge risk={risk} /><span className="tiny muted">{risk.known_total} points{risk.complete ? '' : ' known so far'}</span></div>
    <p className={`notice ${risk.flagged ? 'error' : 'info'}`} style={{ marginTop: 14 }}>{risk.reason}</p>
    <div className="table-wrap"><table><thead><tr><th>Factor</th><th>This patient</th><th>Rule</th><th>Points</th></tr></thead><tbody>
      {risk.factors.map(f => <tr key={f.name}><td>{f.name}</td><td>{f.value ?? 'Not recorded'}</td><td className="tiny">{f.rule}</td><td><b>{f.points ?? '—'}</b> / {f.max}</td></tr>)}
    </tbody></table></div>
    <p className="tiny muted">Low 0 · Intermediate 30–59 · High 60–180. A known score of 60 or more flags high risk even if another input is missing. {risk.notice}</p>
  </Card>;
}
