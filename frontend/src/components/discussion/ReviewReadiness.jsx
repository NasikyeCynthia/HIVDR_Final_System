import {Link} from 'react-router-dom';
import {useAuth} from '../../contexts/AuthContext.jsx';
import {workflowService} from '../../services/workflowService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Feedback from '../common/Feedback.jsx';
import Card from '../common/Card.jsx';
import Badge from '../common/Badge.jsx';
import {PsychosocialRecommendations} from '../patients/PsychosocialForm.jsx';
import {reviewStage} from '../../utils/discussion.js';
import {drugResults,LEVEL_COLORS} from '../../utils/resistance.js';

export default function ReviewReadiness({patient,onSaved}) {
  const {user}=useAuth(),action=usePatientAction(onSaved);
  const stage=reviewStage(patient),automation=patient.automation||{},scores=drugResults(patient.interpretation);
  const active=stage.key==='processing';
  const canRun=['lab','clinician'].includes(user.role)&&patient.status==='Usable result'&&!patient.decision;
  return <>
    <Card title="Clinical evidence">
      <p><Badge color={stage.color}>{stage.label}</Badge></p>
      <dl className="resistance-context"><div><dt>Patient ID</dt><dd>{patient.external_id}</dd></div><div><dt>Drugs</dt><dd>{patient.regimen||'Not recorded'}</dd></div><div><dt>Laboratory outcome</dt><dd>{patient.status}</dd></div><div><dt>Result released</dt><dd>{patient.report_at?.slice(0,10)||'Not recorded'}</dd></div></dl>
      <p className="tiny"><Link className="text-link" to="/help#clinical-decision-support">Review guidance</Link></p>
      {automation.message&&<p className={`notice ${stage.key==='attention'?'error':'info'}`} role="status">{automation.message}</p>}
      <Feedback error={action.error} success={action.success}/>
      {canRun&&!active&&<button type="button" className="btn secondary" disabled={action.busy} onClick={()=>action.run(()=>workflowService.retryInterpretation(patient.id),'Saved laboratory input queued for Stanford analysis.')}>{patient.interpretation?'Re-run saved laboratory result':stage.key==='attention'?'Retry Stanford analysis':'Analyse saved laboratory result'}</button>}
      {active&&<p className="tiny muted" aria-live="polite">Waiting for Stanford. This view updates automatically; no treatment decision is approved while analysis is pending.</p>}
      <p><b>Mutation input:</b> {patient.suggested_mutations|| (patient.sequence?'Saved nucleotide sequence':'No gene-specific mutation list or sequence recorded')}</p>
      <p className="tiny"><Link className="text-link" to={`/patients/${patient.id}?tab=laboratory#lab-mutations`}>Review / correct the laboratory evidence →</Link></p>
      {patient.interpretation&&<><dl className="resistance-context"><div><dt>Interpretation source</dt><dd>{patient.interpretation.provider||'Stanford HIVdb Sierra'}</dd></div><div><dt>Algorithm</dt><dd>{patient.interpretation.version?.text||'Not recorded'}</dd></div><div><dt>Algorithm publication</dt><dd>{patient.interpretation.version?.publishDate||'Not recorded'}</dd></div><div><dt>Analysis saved</dt><dd>{patient.interpreted_at||'Not recorded'}</dd></div></dl>
        {(patient.interpretation.analysis?.validationResults||[]).map((v,i)=><p key={i} className="notice">{v.level}: {v.message}</p>)}
        <details><summary>All returned Stanford drug interpretations and comments ({scores.length} drugs)</summary><div className="table-wrap"><table><thead><tr><th>Gene</th><th>Drug</th><th>Score</th><th>Stanford interpretation</th></tr></thead><tbody>{scores.map((s,i)=><tr key={i}><td>{s.gene}</td><td>{s.drug.displayAbbr}</td><td>{s.score}</td><td><Badge color={LEVEL_COLORS[s.level]||''}>{s.text}</Badge></td></tr>)}</tbody></table></div>{(patient.interpretation.analysis?.drugResistance||[]).flatMap(g=>(g.commentsByTypes||[]).flatMap(t=>t.comments||[])).map((c,i)=><p key={i}>{c.text}</p>)}</details></>}
    </Card>
    <Card title="Clinical context for the review">
      <p>Viral load: <b>{patient.viral_load??'Not recorded'}</b> copies/mL · Adherence: <b>{patient.adherence==null?'Not recorded':patient.adherence+'%'}</b> · Treatment line: <b>{patient.treatment_line??'Not recorded'}</b></p>
      <p className="tiny muted">Review drug exposure, prior treatment and earlier viral loads alongside the genotype. <Link className="text-link" to={`/patients/${patient.id}?tab=record`}>Open complete patient record →</Link></p>
      <PsychosocialRecommendations items={patient.psychosocial_recommendations}/>
      {patient.review_notes&&<p><b>Earlier clinical review notes:</b> {patient.review_notes}</p>}
    </Card>
  </>;
}
