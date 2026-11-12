import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
// Mirrors the MoH HIVDR cascade report (Eligible → Plasma → Referred → Results → Amplified → Reviewed → decision → Started).
export default function HivdrCascade({ patients }) {
  const eligible = patients.filter(p => p.eligibility?.status === 'eligible' || p.referred_at || p.sample_at);
  const reviewed = eligible.filter(p => p.decision);
  const changing = reviewed.filter(p => ['Switched', 'Substituted'].includes(p.decision));
  const rows = [
    ['Eligible for DRT', eligible.length, null, 'eligible'],
    ['Plasma samples', eligible.filter(p => p.sample_type === 'Plasma').length, eligible.length, 'Plasma'],
    ['Referred for DRT', eligible.filter(p => p.cphl_outcome === 'Referred to DR lab' || p.referred_at).length, eligible.length, 'referred'],
    ['Received results', eligible.filter(p => p.report_at && ['Usable result', 'Unamplified', 'Sequencing failed'].includes(p.status)).length, null, 'received'],
    ['Amplified', eligible.filter(p => p.amplified === 1).length, null, 'amplified'],
    ['Reviewed', reviewed.length, null, 'decision'],
    ['Maintained', reviewed.filter(p => p.decision === 'Maintained').length, reviewed.length, 'Maintained'],
    ['Switched', reviewed.filter(p => p.decision === 'Switched').length, reviewed.length, 'Switched'],
    ['Substituted', reviewed.filter(p => p.decision === 'Substituted').length, reviewed.length, 'Substituted'],
    ['Started (switched/substituted)', changing.filter(p => p.implemented_at).length, changing.length, 'implemented'],
  ];
  let previous = null;
  return <Card title="HIVDR cascade" subtitle="Same steps as the MoH HIVDR cascade report">
    <div className="table-wrap"><table><thead><tr><th>Step</th><th>Clients</th><th>% of previous step</th></tr></thead><tbody>
      {rows.map(([label, n, base, filter]) => { const den = base ?? previous; const pct = den ? Math.round(n / den * 100) : null; if (base == null) previous = n; return <tr key={label}><td><Link className="text-link" to={`/patients?cohort=eligible&filter=${filter}`}>{label}</Link></td><td><b>{n.toLocaleString()}</b></td><td>{label === 'Eligible for DRT' || pct == null ? '—' : `${pct}%`}</td></tr>; })}
    </tbody></table></div>
    <p className="tiny muted">Plasma and referral are shown as a share of eligible; decisions as a share of reviewed; “Started” as a share of switched or substituted.</p>
  </Card>;
}
