import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {useCan} from '../../contexts/AuthContext.jsx';
import ViewOnly from '../common/ViewOnly.jsx';
import Badge from '../common/Badge.jsx';
import {workflowService} from '../../services/workflowService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';
import StanfordConnection from './StanfordConnection.jsx';
import MutationEntry from './MutationEntry.jsx';
import {DRUG_GROUPS, EXPOSURES, LEVEL_COLORS, exposureValue, regimenDrugs, drugResults, resistanceResult, sampleTreatment} from '../../utils/resistance.js';

export default function InterpretationPanel({patient,record={},onSaved}) {
  const action=usePatientAction(onSaved),can=useCan();
  const [kind,setKind]=useState(patient.suggested_mutations?'mutations':patient.sequence?'sequence':'mutations');
  const [drafts,setDrafts]=useState({mutations:patient.suggested_mutations||'',sequence:patient.sequence||''});
  const interpretation=patient.interpretation,analysis=interpretation?.analysis;
  const treatment=sampleTreatment(patient,record);
  const scores=drugResults(interpretation),currentDrugs=regimenDrugs(treatment.regimen);
  useEffect(()=>{setDrafts(d=>({...d,mutations:patient.suggested_mutations||'',sequence:patient.sequence||''}));},[patient.suggested_mutations,patient.sequence]);
  const automaticPending=['pending','running'].includes(patient.automation?.status);
  const canEdit=can('interpret_resistance',patient)&&patient.status==='Usable result'&&!patient.decision&&!automaticPending;
  const mutationFields=['PI','INSTI','NRTI','NNRTI','PI Mutations Combined','INSTI Mutations','NNRTI Mutations','NRTI Mutations','PiMajor Mutations','PiMinor Mutations','Accessory Mutations','Other Mutations','All Mutations Combined'];
  const reportedFields=mutationFields.filter(key=>String(record[key]??'').trim());
  const requestedDrugs=new Set(DRUG_GROUPS.flatMap(g=>g.drugs));
  const additionalScores=scores.filter(s=>!requestedDrugs.has(s.drug?.displayAbbr));
  function submit(e) {
    e.preventDefault();
    action.run(()=>workflowService.interpret(patient.id,{kind,text:drafts[kind]}),'Stanford responded; interpretation saved and results updated below.');
  }
  return <>
    <Card title="Patient and treatment at sample collection">
      <dl className="resistance-context"><div><dt>Patient ID</dt><dd>{patient.external_id}</dd></div><div><dt>Treatment Line at Sample collection</dt><dd>{treatment.line||'Not recorded'}</dd></div><div><dt>Drugs</dt><dd>{treatment.regimen||'Not recorded'}</dd></div></dl>
    </Card>
    <MutationEntry patient={patient} record={record} onSaved={onSaved}/>
    <Card title="Drug exposure history" subtitle="Recorded exposure includes prior treatment, even when the drug is outside ART at sample collection.">
      <div className="table-wrap"><table><thead><tr><th>Drug / exposure combination</th><th>Exposure</th></tr></thead><tbody>{EXPOSURES.map(([key,label])=><tr key={key}><td>{label}<div className="tiny muted">{key}</div></td><td>{exposureValue(record[key])}</td></tr>)}</tbody></table></div>
      <p className="tiny muted">These values come from the recorded treatment history. Missing history is not treated as “No”. Exposure alone does not determine a resistance category.</p>
    </Card>
    <StanfordConnection/>
    <Card title="Stanford interpretation"><p className="notice info">{automaticPending?'Automatic Stanford analysis is in progress; results will update here.':'Automatic analysis is enabled for usable results.'} <Link className="text-link" to={`/patients/${patient.id}?tab=discussion`}>Open clinician review →</Link></p>
      <p role="status" aria-live="polite" className="notice info">{action.busy?'Request in progress: waiting for Stanford and saving its response…':action.error?'Request or refresh failed. Any previously saved results below remain labeled with their original time.':action.success?'API response received and saved.':interpretation?'A saved Stanford API result is available below.':'No saved Stanford API interpretation for this episode. Recorded laboratory results are shown separately below.'}</p>
      <Feedback error={action.error} success={action.success}/>
      <form onSubmit={submit}><fieldset disabled={!canEdit||action.busy}>
        <label htmlFor="interpret-kind">Input type</label><select id="interpret-kind" value={kind} onChange={e=>setKind(e.target.value)}><option value="mutations">Mutations</option><option value="sequence">Nucleotide sequence / FASTA</option></select>
        <label htmlFor="interpret-text" style={{marginTop:15}}>{kind==='mutations'?'Mutations to submit (gene-prefixed)':'Sequence to submit (one FASTA record)'}</label>
        <textarea id="interpret-text" name="text" required maxLength={100000} value={drafts[kind]} onChange={e=>setDrafts({...drafts,[kind]:e.target.value})} placeholder={kind==='mutations'?'RT:M184V RT:K103N IN:R263K':'ACGT…'}/>
        <p className="tiny muted">Prefilled values come from the saved laboratory result. Review the full mutation pattern against the report. For a report with no mutations, use the laboratory sequence. FASTA headers are discarded before transmission.</p>
        <div className="form-actions"><button className="btn" disabled={!canEdit||action.busy}>{action.busy?'Analysing with Stanford…':'Analyse with Stanford'}</button></div>
      </fieldset></form>
      {!can('interpret_resistance',patient)?<ViewOnly action="interpret_resistance"/>:!canEdit&&<p className="notice">{patient.decision?'This episode has an approved decision and is locked.':automaticPending?'Automatic analysis is in progress.':'A usable laboratory result is required before analysis.'} <Link className="text-link" to={`/patients/${patient.id}?tab=laboratory`}>Review laboratory result →</Link></p>}
      <details><summary>Recorded specimen and mutation evidence</summary><p>Specimen: {patient.sample_type||record['Sample Type']||'Not recorded'} · Collection: {patient.sample_at||record['Sample collection Date']||'Not recorded'} · Laboratory status: {patient.status}</p>{reportedFields.length?<div className="table-wrap"><table><thead><tr><th>Field</th><th>Recorded mutations</th></tr></thead><tbody>{reportedFields.map(key=><tr key={key}><td>{key}</td><td>{record[key]}</td></tr>)}</tbody></table></div>:<p>No gene-specific mutations are recorded in the dataset fields.</p>}</details>
    </Card>
    <Card title="Drug-specific resistance results" subtitle={interpretation?'Source: saved Stanford API response':'Source: recorded laboratory report; no saved Stanford API response'}>
      {interpretation&&<><dl className="resistance-context"><div><dt>Provider / algorithm</dt><dd>{interpretation.provider||'Stanford HIVdb Sierra'} · {interpretation.version?.text||'Not recorded'}</dd></div><div><dt>Algorithm publication date</dt><dd>{interpretation.version?.publishDate||'Not recorded'}</dd></div><div><dt>Analysis saved</dt><dd>{patient.interpreted_at||interpretation.analyzed_at||'Not recorded'}</dd></div><div><dt>Genes with returned results</dt><dd>{(interpretation.analyzed_genes||[...new Set(scores.map(s=>s.gene))]).join(', ')||'Not recorded'}</dd></div></dl>
        {(analysis.validationResults||[]).map((v,i)=><p className="notice" key={i}>{v.level}: {v.message}</p>)}</>}
      <p className="tiny muted">All requested drugs are shown, including drugs outside ART at sample collection. “Not assessed” means this saved analysis returned no result for that drug. “Not recorded” means the laboratory report has no value. Neither means susceptible.</p>
      {DRUG_GROUPS.map(group=><section key={group.name}><h3>{group.name} <span className="tiny muted">{group.description!==group.name?`· ${group.description}`:''}</span></h3><div className="table-wrap"><table><thead><tr><th>Drug</th><th>Current treatment</th><th>Resistance classification</th><th>Stanford score</th><th>Source</th></tr></thead><tbody>{group.drugs.map(drug=>{
        const r=resistanceResult(drug,interpretation,record);
        return <tr key={drug} style={currentDrugs.includes(drug)?{background:'var(--primary-soft)'}:undefined}><td><b>{drug}</b></td><td>{currentDrugs.includes(drug)?'On regimen':'Outside regimen'}</td><td><Badge color={LEVEL_COLORS[r.level]||''}>{r.text}</Badge></td><td>{r.score??'—'}</td><td>{r.source}</td></tr>;
      })}</tbody></table></div></section>)}
      <p className="tiny muted">Five levels: susceptible (&lt;10); potential low-level (10–14); low-level (15–29); intermediate (30–59); high-level (≥60). Results are drug-specific and need clinical review alongside treatment and exposure history.</p>
      {interpretation&&<details><summary>Stanford response details and additional drugs</summary>{interpretation.submitted_mutations&&<p>Submitted mutations: {interpretation.submitted_mutations.join(' ')}</p>}{additionalScores.length>0&&<div className="table-wrap"><table><thead><tr><th>Additional drug</th><th>Score</th><th>Classification</th></tr></thead><tbody>{additionalScores.map((s,i)=><tr key={i}><td>{s.drug.displayAbbr}</td><td>{s.score}</td><td>{s.text}</td></tr>)}</tbody></table></div>}{(analysis.drugResistance||[]).flatMap(g=>(g.commentsByTypes||[]).flatMap(t=>t.comments||[])).map((c,i)=><p key={i}>{c.text}</p>)}</details>}
      {interpretation&&Object.keys(record).some(key=>key.startsWith('Resistance to ')&&record[key])&&<details><summary>Earlier recorded laboratory report (not merged into the API results)</summary><div className="table-wrap"><table><thead><tr><th>Drug</th><th>Recorded result</th></tr></thead><tbody>{DRUG_GROUPS.flatMap(g=>g.drugs).map(drug=><tr key={drug}><td>{drug}</td><td>{record[`Resistance to ${drug}`]||'Not recorded'}</td></tr>)}</tbody></table></div></details>}
    </Card>
  </>;
}
