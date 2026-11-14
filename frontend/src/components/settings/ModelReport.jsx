import {useEffect,useState} from 'react';
import {operationsService} from '../../services/operationsService.js';
import Card from '../common/Card.jsx';
const pct=v=>v==null?'â€”':`${(v*100).toFixed(1)}%`;
const dec=v=>v==null?'â€”':v.toFixed(3);
export default function ModelReport(){
 const [result,setResult]=useState(null),[error,setError]=useState('');
 useEffect(()=>{operationsService.model().then(setResult).catch(e=>setError(e.message))},[]);
 const m=result?.metadata,t=m?.held_out_test,a=result?.validation;
 return <Card title="Machine-learning model and evaluation" className="section-gap">{error?<p>{error}</p>:!m?<p>{result?.message||'Loading modelâ€¦'}</p>:<>
 <h3>{m.selected_model} Â· {m.version}</h3><p>{m.target}</p>
 <p className="notice info">Research use in referred and tested patients. This model does not diagnose resistance, determine test eligibility or prescribe treatment.</p>
 <div className="table-wrap"><table><thead><tr><th>Partition</th><th>Records</th><th>Facilities</th><th>Resistance outcome</th></tr></thead><tbody>{Object.entries(m.split).map(([name,s])=><tr key={name}><td>{name}</td><td>{s.rows.toLocaleString()}</td><td>{s.facilities}</td><td>{pct(s.positive_rate)}</td></tr>)}</tbody></table></div>
 <p className="tiny muted">Facilities are disjoint. Validation data selected the model, calibration and {pct(m.threshold)} research cutoff. Test data evaluated the finished pipeline.</p>
 <table><thead><tr><th>Candidate</th><th>Validation AUROC</th></tr></thead><tbody>{Object.entries(m.model_comparison).map(([name,v])=><tr key={name}><td>{name}</td><td>{dec(v.validation_roc_auc)}</td></tr>)}</tbody></table>
 <h3>Held-out performance</h3><div className="detail-list">
 <div><label>AUROC Â· ranking</label>{dec(t.roc_auc)}</div><div><label>Average precision</label>{dec(t.average_precision)}</div>
 <div><label>Sensitivity Â· positives detected</label>{pct(t.sensitivity)}</div><div><label>Specificity Â· negatives excluded</label>{pct(t.specificity)}</div>
 <div><label>Accuracy</label>{pct(t.accuracy)}</div><div><label>Balanced accuracy</label>{pct(t.balanced_accuracy)}</div><div><label>Brier score Â· lower is better</label>{dec(t.brier_score)}</div></div>
 <table><thead><tr><th>Actual outcome</th><th>Below cutoff</th><th>At / above cutoff</th></tr></thead><tbody><tr><td>Resistance present</td><td>{t.confusion_matrix.fn} missed</td><td>{t.confusion_matrix.tp} detected</td></tr><tr><td>Resistance absent</td><td>{t.confusion_matrix.tn} correctly excluded</td><td>{t.confusion_matrix.fp} incorrectly flagged</td></tr></tbody></table>
 <p className="tiny muted">AUROC is a ranking measure, not accuracy. Sensitivity shows that below-cutoff estimates cannot exclude resistance.</p>
 <details><summary>Additional frozen-model validation</summary>{!a?<p>No matching additional validation report is installed. The original held-out results above remain available.</p>:<>
 <p>{a.bootstrap.replicates} facility-cluster bootstrap replicates; 95% intervals reflect uncertainty in this test cohort, not external clinical validation.</p>
 <table><thead><tr><th>Measure</th><th>95% interval</th></tr></thead><tbody>{Object.entries(a.bootstrap.intervals).map(([name,v])=><tr key={name}><td>{name.replaceAll('_',' ')}</td><td>{dec(v[0])}â€“{dec(v[1])}</td></tr>)}</tbody></table>
 <p>Precision: {pct(a.metrics.precision)} · Negative predictive value: {pct(a.metrics.negative_predictive_value)}.</p><p>Precision: {pct(a.metrics.precision)} · Negative predictive value: {pct(a.metrics.negative_predictive_value)}.</p><p>Training-prevalence baseline Brier: {dec(a.baselines.training_prevalence_brier)}. Majority-class baseline accuracy: {pct(a.baselines.majority_accuracy)}.</p>
 <h3>Calibration by predicted probability</h3><table><thead><tr><th>Probability bin</th><th>Records</th><th>Mean prediction</th><th>Observed resistance</th></tr></thead><tbody>{a.calibration.map((b,i)=><tr key={i}><td>{pct(b.lower)}â€“{pct(b.upper)}</td><td>{b.n}</td><td>{pct(b.mean_probability)}</td><td>{pct(b.observed_rate)}</td></tr>)}</tbody></table>
 <h3>Subgroup checks</h3><p className="tiny muted">Descriptive checks at the original cutoff; small groups are suppressed. Differences are uncertain and do not establish fairness.</p><table><thead><tr><th>Group</th><th>Records</th><th>Sensitivity</th><th>Specificity</th><th>AUROC</th></tr></thead><tbody>{a.subgroups.map(g=><tr key={g.group}><td>{g.group}</td><td>{g.n}</td><td>{pct(g.metrics?.sensitivity)}</td><td>{pct(g.metrics?.specificity)}</td><td>{g.suppressed?'Too few records':dec(g.metrics?.roc_auc)}</td></tr>)}</tbody></table>
 </>}</details>
 <details><summary>Limitations and global feature importance</summary><ul>{m.limitations.map(v=><li key={v}>{v}</li>)}</ul><p className="tiny muted">Global importance is neither causal nor a patient-specific explanation. No prospective or independent external validation is claimed.</p><ul>{m.top_global_features.map(v=><li key={v.feature}>{v.feature}: {v.importance.toFixed(3)}</li>)}</ul></details>
 </>}</Card>;
}
