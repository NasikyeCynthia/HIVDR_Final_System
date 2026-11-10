import { useEffect, useState } from 'react';
import { operationsService } from '../../services/operationsService.js';
import Card from '../common/Card.jsx';

export default function MLPrediction({ patient }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setResult(null);
    setError('');
    operationsService.prediction(patient.id)
      .then(value => { if (active) setResult(value); })
      .catch(failure => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, [patient.id, patient.data_version, patient.viral_load, patient.treatment_line, patient.regimen]);

  return <Card title="Machine-learning estimate" subtitle="A research estimate, separate from the rules-based risk score">
    {error ? <p className="notice error">{error}</p> : !result ? <p>Loading model estimate...</p> : !result.available ? <p className="notice info">{result.reason}</p> : <>
      <div className="model-probability">{Math.round(result.probability * 100)}<small>% estimated probability</small></div>
      <p>{result.model} · {result.version}</p>
      <p className="notice">{result.scope}</p>
      {result.missing_features?.length > 0 && <p className="tiny muted">Some inputs were missing and filled using the model’s imputation method: {result.missing_features.join(', ')}.</p>}
      <p className="tiny muted">This estimate does not confirm resistance, change DRT eligibility, or choose treatment. It was evaluated in a referred and tested cohort, so it may not apply to people who were not referred for testing.</p>
    </>}
    <details className="model-explainer">
      <summary>What is the model doing?</summary>
      <div className="model-explainer-content">
        <p><b>In plain language:</b> it uses patterns from previously tested records to estimate how likely a patient is to have any low-level-or-higher resistance in the observed 12-drug panel. The displayed percentage is an estimate, not a diagnosis.</p>
        <p><b>Information it uses:</b> viral load at the resistance-test sample, age, sex, treatment line, ART duration at that sample, regimen, and earlier dated viral-load results.</p>
        <p><b>Information it does not use:</b> mutations, resistance results, adherence, psychosocial factors, committee decisions, or viral loads measured after the resistance-test decision. Facility was used to keep facilities separate during evaluation, not as a prediction input.</p>
        <p><b>How it was checked:</b> a random forest was selected after comparison with logistic regression. The held-out evaluation used 1,739 records from 236 facilities that were kept separate from model training. It achieved AUROC 0.72; at the demonstration threshold, sensitivity was 66% and specificity 68% in that test set.</p>
        <p><b>Limits:</b> records needed results for all 12 drugs to train/evaluate the target. The data are retrospective and referred for testing, and the model has not been prospectively validated. Use it for research demonstration only; clinical decisions require the laboratory evidence and clinician review.</p>
      </div>
    </details>
  </Card>;
}
