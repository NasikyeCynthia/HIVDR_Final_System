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
  return <Card title="Model results for this patient" subtitle="Research models; they support but never replace the laboratory test and the clinician">
    <div className="model-grid">
      <div className="model-box">
        <h3>Chance of drug resistance</h3>
        {!ml ? <p className="muted">Not calculated yet.</p> : !ml.available ? <p className="muted">{ml.reason}</p> : <>
          <div className="model-probability">{Math.round(ml.probability * 100)}<small>%</small></div>
          <Badge color={ml.above_research_threshold ? 'red' : 'green'}>{ml.above_research_threshold ? 'Above' : 'Below'} the research threshold ({Math.round((ml.threshold || 0.64) * 100)}%)</Badge>
          <p className="tiny muted">Estimated chance that the virus has low-level or higher resistance to at least one of 12 drugs, from viral load, age, sex, line, regimen, years on ART and earlier viral loads. Random forest; AUROC 0.72 on facilities it had not seen.</p>
        </>}
      </div>
      <div className="model-box">
        <h3>Time to treatment failure</h3>
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
