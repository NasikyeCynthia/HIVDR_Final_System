import {useEffect,useState} from 'react';
import {operationsService} from '../../services/operationsService.js';
import Card from '../common/Card.jsx';
const pct=v=>v==null?'—':`${(v*100).toFixed(1)}%`;
const dec=v=>v==null?'—':v.toFixed(3);
const comparedMetrics=[['AUROC','roc_auc',dec],['Sensitivity','sensitivity',pct],['Specificity','specificity',pct],['Accuracy','accuracy',pct],['Balanced accuracy','balanced_accuracy',pct],['Brier score','brier_score',dec]];

function Calibration({bins=[]}){
 return <><h3>Calibration by predicted probability</h3><div className="table-wrap"><table><thead><tr><th>Probability bin</th><th>Records</th><th>Mean prediction</th><th>Observed resistance</th></tr></thead><tbody>{bins.map((b,i)=><tr key={i}><td>{pct(b.lower)}–{pct(b.upper)}</td><td>{b.n}</td><td>{pct(b.mean_probability)}</td><td>{pct(b.observed_rate)}</td></tr>)}</tbody></table></div></>;
}
function Subgroups({groups=[]}){
 return <><h3>Subgroup checks</h3><p className="tiny muted">Descriptive checks at the research cutoff. Small groups are suppressed; differences do not establish fairness.</p><div className="table-wrap"><table><thead><tr><th>Group</th><th>Records</th><th>Sensitivity</th><th>Specificity</th><th>AUROC</th></tr></thead><tbody>{groups.map(g=><tr key={g.group}><td>{g.group}</td><td>{g.n}</td><td>{pct(g.metrics?.sensitivity)}</td><td>{pct(g.metrics?.specificity)}</td><td>{g.suppressed?'Too few records':dec(g.metrics?.roc_auc)}</td></tr>)}</tbody></table></div></>;
}
export default function ModelReport(){
 const [result,setResult]=useState(null),[error,setError]=useState('');
 useEffect(()=>{operationsService.model().then(setResult).catch(e=>setError(e.message))},[]);
 const m=result?.metadata,t=m?.held_out_test,a=result?.validation,r=result?.retraining_evaluation;
 const comparison=m?.development_comparison||m?.model_comparison||{};
 return <Card title="Machine-learning model and evaluation" className="section-gap">{error?<p>{error}</p>:!m?<p>{result?.message||'Loading model…'}</p>:<>
 <h3>{m.selected_model} · {m.version}</h3><p>{m.target}</p>
 <p className="notice info">Active research estimate for referred and tested patients. It does not diagnose resistance, determine test eligibility or prescribe treatment.{r?' Independent prospective/external validation is still pending.':''}</p>
 <div className="table-wrap"><table><thead><tr><th>Partition</th><th>Records</th><th>Facilities</th><th>Resistance outcome</th></tr></thead><tbody>{Object.entries(m.split).map(([name,s])=><tr key={name}><td>{name.replaceAll('_',' ')}</td><td>{s.rows.toLocaleString()}</td><td>{s.facilities}</td><td>{pct(s.positive_rate)}</td></tr>)}</tbody></table></div>
 <p className="tiny muted">{r?`Four-fold facility-grouped cross-validation selected the configuration. Separate calibration and cutoff facilities set the probability adjustment and ${pct(m.threshold)} research cutoff. The legacy test had already been examined; it is not a new independent validation.`:`Facilities are disjoint. Validation data selected the model, calibration and ${pct(m.threshold)} research cutoff. Test data evaluated the finished pipeline.`}</p>
 <table><thead><tr><th>Candidate</th><th>{r?'Mean training-fold AUROC':'Validation AUROC'}</th></tr></thead><tbody>{Object.entries(comparison).map(([name,v])=><tr key={name}><td>{name}</td><td>{dec(v.mean_auroc??v.validation_roc_auc)}</td></tr>)}</tbody></table>
 <h3>{r?'Legacy-test performance (previously examined)':'Held-out performance'}</h3><div className="detail-list">
 <div><label>AUROC · ranking</label>{dec(t.roc_auc)}</div><div><label>Average precision</label>{dec(t.average_precision)}</div>
 <div><label>Sensitivity · positives detected</label>{pct(t.sensitivity)}</div><div><label>Specificity · negatives excluded</label>{pct(t.specificity)}</div>
 <div><label>Accuracy</label>{pct(t.accuracy)}</div><div><label>Balanced accuracy</label>{pct(t.balanced_accuracy)}</div><div><label>Brier score · lower is better</label>{dec(t.brier_score)}</div></div>
 <table><thead><tr><th>Actual outcome</th><th>Below cutoff</th><th>At / above cutoff</th></tr></thead><tbody><tr><td>Resistance present</td><td>{t.confusion_matrix.fn} missed</td><td>{t.confusion_matrix.tp} detected</td></tr><tr><td>Resistance absent</td><td>{t.confusion_matrix.tn} correctly excluded</td><td>{t.confusion_matrix.fp} incorrectly flagged</td></tr></tbody></table>
 <p className="tiny muted">AUROC measures ranking, not accuracy. A below-cutoff estimate cannot exclude resistance.</p>
 {r&&<details><summary>Retraining comparison, calibration and subgroups</summary>
 <table><thead><tr><th>Measure</th><th>Original model</th><th>Active retrained model</th></tr></thead><tbody>{comparedMetrics.map(([label,key,fmt])=><tr key={key}><td>{label}</td><td>{fmt(r.baseline_legacy_test[key])}</td><td>{fmt(r.legacy_test[key])}</td></tr>)}</tbody></table>
 <p className="tiny muted">Improved sensitivity comes with lower specificity at the selected cutoffs. This is a retrospective comparison on the same 1,739 records.</p>
 <p>Paired facility-bootstrap 95% interval for the AUROC difference: {dec(r.paired_comparison.auroc_difference_95_interval[0])}–{dec(r.paired_comparison.auroc_difference_95_interval[1])}. This excludes model-selection uncertainty.</p>
 <p>Precision: {pct(t.precision)} · Negative predictive value: {pct(t.negative_predictive_value)}.</p>
 <Calibration bins={r.calibration}/><Subgroups groups={r.subgroups}/>
 </details>}
 {!r&&<details><summary>Additional frozen-model validation</summary>{!a?<p>No matching additional validation report is installed.</p>:<>
 <p>{a.bootstrap.replicates} facility-cluster bootstrap replicates; 95% intervals describe this cohort, not external clinical validation.</p>
 <table><thead><tr><th>Measure</th><th>95% interval</th></tr></thead><tbody>{Object.entries(a.bootstrap.intervals).map(([name,v])=><tr key={name}><td>{name.replaceAll('_',' ')}</td><td>{dec(v[0])}–{dec(v[1])}</td></tr>)}</tbody></table>
 <p>Precision: {pct(a.metrics.precision)} · Negative predictive value: {pct(a.metrics.negative_predictive_value)}.</p>
 <p>Training-prevalence baseline Brier: {dec(a.baselines.training_prevalence_brier)}. Majority-class baseline accuracy: {pct(a.baselines.majority_accuracy)}.</p>
 <Calibration bins={a.calibration}/><Subgroups groups={a.subgroups}/>
 </>}</details>}
 <details><summary>Limitations{m.top_global_features?.length?' and global feature importance':''}</summary><ul>{m.limitations.map(v=><li key={v}>{v}</li>)}</ul>{m.top_global_features?.length>0&&<><p className="tiny muted">Global importance is neither causal nor a patient-specific explanation.</p><ul>{m.top_global_features.map(v=><li key={v.feature}>{v.feature}: {v.importance.toFixed(3)}</li>)}</ul></>}</details>
 </>}</Card>;
}
