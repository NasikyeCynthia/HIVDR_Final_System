import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import { useWorkspace } from '../../contexts/WorkspaceContext.jsx';
import { FAILURE_GROUPS } from '../dashboard/TreatmentLineFailure.jsx';
import { timeToFailureCohort } from '../dashboard/TimeToFailure.jsx';

// Per-patient results from the analytic models (backend/ml): the resistance estimate and the
// patient's time to treatment failure compared with similar patients.
const fmt = iso => iso ? new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
const median = values => { const s = [...values].sort((a, b) => a - b); const i = (s.length - 1) / 2; return s.length ? (s[Math.floor(i)] + s[Math.ceil(i)]) / 2 : null; };

export default function ModelResults({ patient }) {
  const { patients } = useWorkspace();
  const ml = patient.risk?.ml;
  const ttf = Array.isArray(patient.ttf) ? patient.ttf : null;
  const group = FAILURE_GROUPS.find(([, , test]) => test(patient));
  let comparison = null;
  if (ttf && group) {
    const { cohort } = timeToFailureCohort(patients.filter(p => p.source === patient.source));
    const peers = cohort.filter(group[2]).map(p => p.ttf[0]);
    if (peers.length >= 20) {
      const sooner = Math.round(peers.filter(m => m > ttf[0]).length / peers.length * 100);
      comparison = { label: group[1], n: peers.length, median: median(peers), sooner, beyond: ttf[0] > 36 };
    }
  }
  return <Card title="Research estimate and observed history" subtitle="Separate from the rules-based score and DR-test eligibility">
    <div className="model-grid">
      <div className="model-box">
        <h3>ML panel-resistance estimate</h3>
        {!ml ? <p className="muted">Not calculated yet.</p> : !ml.available ? <p className="muted">{ml.reason}</p> : <>
          <div className="model-probability">{Math.round(ml.probability * 100)}<small>%</small></div>
          <Badge color={ml.above_research_threshold ? 'yellow' : ''}>{ml.above_research_threshold ? 'Above' : 'Below'} the research threshold ({Math.round(ml.threshold * 100)}%)</Badge>
          <p className="tiny muted">Any low-level-or-higher resistance in the 12-drug RT/IN panel, estimated for referred and tested patients. PI-only resistance is outside this target.</p>
          <p className="notice info">Research estimate, not a laboratory result. A below-threshold estimate does not rule out resistance or change DR-test eligibility.</p>
          <p className="tiny muted">{ml.model} · {ml.version}. Adherence is used by the points score, not this model.</p>
          {ml.missing_features?.length > 0 && <p className="tiny muted">Missing model inputs: {ml.missing_features.join(', ')}. Saved training values or missing categories were used.</p>}
        </>}
      </div>
      <div className="model-box">
        <h3>Observed time to treatment failure</h3>
        {!ttf ? <p className="muted">No dated start of the current regimen with a later viral load ≥1000, so it cannot be calculated.</p> : <>
          <div className="model-probability">{ttf[0].toFixed(0)}<small> months</small></div>
          <p>Started the current regimen on {fmt(ttf[1])}; first viral load ≥1000 on {fmt(ttf[2])}.</p>
          {comparison ? <p><Badge color={comparison.sooner >= 50 ? 'red' : 'green'}>{comparison.sooner >= 50 ? 'Earlier' : 'Later'} than typical</Badge> {comparison.label}: typical {comparison.median.toFixed(0)} months. {comparison.beyond ? `This patient failed after more than 36 months, later than all ${comparison.n.toLocaleString()} similar patients compared within 3 years.` : `This patient failed sooner than ${comparison.sooner}% of ${comparison.n.toLocaleString()} similar patients.`}</p>
            : <p className="tiny muted">Too few comparable patients to compare.</p>}
          <p className="tiny muted">Descriptive, among patients who failed. A model to predict who fails early was tested (AUROC 0.59) and is not used.</p>
        </>}
      </div>
    </div>
  </Card>;
}
