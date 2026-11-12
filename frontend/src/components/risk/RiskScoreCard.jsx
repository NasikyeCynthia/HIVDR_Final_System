import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
// Points score for the risk of drug resistance (backend: services/risk_service.py, RISK_SCORE.md).
export const RISK_COLOR = { High: 'red', Moderate: 'yellow', Low: 'green' };
export function RiskBadge({ risk }) {
  const category = risk?.category || 'Not assessed';
  return <Badge color={RISK_COLOR[category] || ''}>{category === 'Not applicable' ? 'Risk: not applicable' : `${category} risk`}{risk?.flagged ? ' · flagged' : ''}</Badge>;
}
export default function RiskScoreCard({ risk }) {
  if (!risk?.factors) return null;
  const applicable = risk.category !== 'Not applicable';
  return <Card title="Risk of drug resistance" subtitle={`Points score · ${risk.version}`}>
    <div className="split-heading"><RiskBadge risk={risk} />{applicable && <span className="tiny muted">{risk.total} points ({risk.data_points} data-validated + {risk.clinical_points} guideline)</span>}</div>
    <p className={`notice ${risk.flagged ? 'error' : 'info'}`} style={{ marginTop: 14 }}>{risk.reason}</p>
    <div className="table-wrap"><table><thead><tr><th>Factor</th><th>This patient</th><th>Points</th></tr></thead><tbody>
      {risk.factors.map(f => <tr key={f.name}><td>{f.name}{!f.validated && <div className="tiny muted">Guideline-based, not validated on outcomes</div>}</td><td>{f.value}</td><td><b>{f.points}</b> / {f.max}</td></tr>)}
    </tbody></table></div>
    <p className="tiny muted">Bands: {risk.bands.map(b => `${b.label} ${b.from}${b.to < 99 ? '–' + b.to : '+'} (≈${b.observed_rate}% had resistance)`).join(' · ')}. Scored only when VL ≥1000. Validated on 9,805 tested CPHL records: AUROC 0.71 (machine-learning model 0.72). {risk.notice}</p>
  </Card>;
}
