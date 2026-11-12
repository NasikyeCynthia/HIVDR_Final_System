import { Link } from 'react-router-dom';
import Card from '../common/Card.jsx';
// Patients failing ART (viral load ≥1000 copies/mL) by treatment line, using the MoH/CPHL
// DR-indication groups: children <15, adolescents 15–19 and adults 20+ on first line; second; third line.
export const FAILURE_GROUPS = [
  ['child', 'Children <15 · 1st line', p => p.treatment_line === 1 && p.age != null && p.age < 15, 'linear-gradient(180deg,#ffb347,#e07b00)'],
  ['adolescent', 'Adolescents 15–19 · 1st line', p => p.treatment_line === 1 && p.age != null && p.age >= 15 && p.age < 20, 'linear-gradient(180deg,#ff7aa2,#c93a6b)'],
  ['adult', 'Adults 20+ · 1st line', p => p.treatment_line === 1 && p.age != null && p.age >= 20, 'linear-gradient(180deg,#5b8def,#2c55b8)'],
  ['second', '2nd line', p => p.treatment_line === 2, 'linear-gradient(180deg,#8f6ae0,#5a39a8)'],
  ['third', '3rd line', p => p.treatment_line === 3, 'linear-gradient(180deg,#e2475f,#9c1c35)'],
];
export const isFailing = p => p.viral_load != null && p.viral_load >= 1000;

export default function TreatmentLineFailure({ patients }) {
  const failing = patients.filter(isFailing);
  const rows = FAILURE_GROUPS.map(([key, label, test, color]) => {
    const group = failing.filter(test);
    return { key, label, color, n: group.length, tested: group.filter(p => p.amplified === 1).length };
  });
  const max = Math.max(1, ...rows.map(r => r.n));
  const unknown = failing.length - rows.reduce((sum, r) => sum + r.n, 0);
  return <Card className="accent-lines" title="Patients failing treatment, by treatment line" subtitle={`${failing.length.toLocaleString()} patients with viral load ≥1000 copies/mL`}>
    <div className="line-chart">{rows.map(r => <Link key={r.key} className="line-row" to={`/patients?filter=failing:${r.key}`}>
      <span className="line-label">{r.label}</span>
      <span className="line-track"><span className="line-fill" style={{ width: `${Math.max(1, r.n / max * 100)}%`, background: r.color }} /></span>
      <span className="line-value"><b>{r.n.toLocaleString()}</b><small>{failing.length ? Math.round(r.n / failing.length * 100) : 0}% · {r.tested.toLocaleString()} with a DR result</small></span>
    </Link>)}</div>
    <p className="tiny muted">Groups follow the CPHL DR-testing indications. {unknown > 0 ? `${unknown.toLocaleString()} failing patients have no recorded treatment line or age. ` : ''}Select a bar to see the patients.</p>
  </Card>;
}
