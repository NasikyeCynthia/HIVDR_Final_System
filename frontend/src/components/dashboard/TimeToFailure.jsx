import Card from '../common/Card.jsx';
import { FAILURE_GROUPS } from './TreatmentLineFailure.jsx';
// How long patients stayed on their current regimen before the first viral load >=1000 (time to treatment failure).
// Descriptive, among patients who failed (the CPHL extract holds only failures). To avoid follow-up bias it uses
// regimens started from 2019 onwards and at least 36 months before the latest data, and failures within 36 months.
const WINDOW = 36;
const ANCHORS = [
  ['DTG-based', p => /DTG/i.test(p.regimen || ''), '#2c63c9'],
  ['NNRTI-based (EFV/NVP)', p => /EFV|NVP/i.test(p.regimen || ''), '#e07b00'],
  ['PI-based (LPV/ATV/DRV)', p => /LPV|ATV|DRV/i.test(p.regimen || ''), '#7a4fc9'],
];
const quantile = (sorted, q) => { if (!sorted.length) return null; const i = (sorted.length - 1) * q, lo = Math.floor(i); return sorted[lo] + (sorted[Math.ceil(i)] - sorted[lo]) * (i - lo); };
const solid = color => color.startsWith('linear') ? color.match(/#[0-9a-f]{6}/i)[0] : color;

export function timeToFailureCohort(patients) {
  const withTtf = patients.filter(p => Array.isArray(p.ttf));
  if (!withTtf.length) return { cohort: [], cutoff: null };
  const end = withTtf.reduce((max, p) => p.ttf[2] > max ? p.ttf[2] : max, '');
  const d = new Date(end); d.setMonth(d.getMonth() - WINDOW);
  const cutoff = d.toISOString().slice(0, 10);
  return { cohort: withTtf.filter(p => p.ttf[1] >= '2019-01-01' && p.ttf[1] <= cutoff && p.ttf[0] <= WINDOW), cutoff };
}

function summarise(group) {
  const m = group.map(p => p.ttf[0]).sort((a, b) => a - b);
  return { n: m.length, median: quantile(m, 0.5), q1: quantile(m, 0.25), q3: quantile(m, 0.75), within12: m.length ? Math.round(m.filter(x => x <= 12).length / m.length * 100) : 0 };
}

function Row({ label, color, s }) {
  const pct = v => `${Math.min(100, v / WINDOW * 100)}%`;
  return <div className="ttf-row">
    <span className="line-label">{label}</span>
    <span className="ttf-track">{s.n > 0 && <><span className="ttf-iqr" style={{ left: pct(s.q1), width: `calc(${pct(s.q3)} - ${pct(s.q1)})`, background: color, opacity: .35 }} /><span className="ttf-median" style={{ left: pct(s.median), background: color }} /></>}</span>
    <span className="line-value">{s.n ? <><b>{s.median.toFixed(0)} mo</b><small>{s.within12}% within 12 months · n {s.n.toLocaleString()}</small></> : <small>No patients</small>}</span>
  </div>;
}

export default function TimeToFailure({ patients }) {
  const { cohort, cutoff } = timeToFailureCohort(patients);
  const overall = summarise(cohort);
  return <Card className="accent-time" title="Time to treatment failure" subtitle={`Months from starting the current regimen to the first viral load ≥1000 · ${cohort.length.toLocaleString()} patients`}>
    {!cohort.length ? <p className="muted">Not enough dated regimen starts and viral loads to show time to failure.</p> : <>
      <div className="ttf-scale"><span /><span className="ttf-ticks">{[0, 6, 12, 18, 24, 30, 36].map(t => <i key={t} style={{ left: `${t / WINDOW * 100}%` }}>{t}</i>)}</span><span /></div>
      <h3 className="ttf-heading">By treatment line</h3>
      {FAILURE_GROUPS.map(([key, label, test, color]) => <Row key={key} label={label} color={solid(color)} s={summarise(cohort.filter(test))} />)}
      <h3 className="ttf-heading">By anchor drug</h3>
      {ANCHORS.map(([label, test, color]) => <Row key={label} label={label} color={color} s={summarise(cohort.filter(test))} />)}
      <p className="tiny muted" style={{ marginTop: 14 }}>Dot = median; bar = middle half of patients (25th–75th percentile). Overall median {overall.median.toFixed(0)} months; {overall.within12}% failed within 12 months. Among patients who failed: regimens started 2019 to {cutoff}, failures within 36 months, so every patient had the same chance to be seen. It describes patterns; it does not predict an individual patient's failure.</p>
    </>}
  </Card>;
}
