import {useEffect,useRef} from 'react';
import {Link,useLocation} from 'react-router-dom';
import {useCan} from '../../contexts/AuthContext.jsx';
import {labService} from '../../services/labService.js';
import usePatientAction from '../../hooks/usePatientAction.js';
import Card from '../common/Card.jsx';
import Feedback from '../common/Feedback.jsx';
import {MUTATION_GROUPS,mutationValue} from '../../utils/resistance.js';

export default function MutationEntry({patient,record,onSaved}) {
  const can=useCan(),action=usePatientAction(onSaved);
  const panel=useRef(null),location=useLocation();
  useEffect(()=>{if(location.hash==='#mutation-entry')panel.current?.scrollIntoView({block:'start'});},[location.hash,patient.id]);
  const locked=patient.reviewed_at||patient.decision||patient.archived_at;
  const failed=['Unamplified','Sequencing failed','Rejected','Deferred'].includes(patient.status);
  const editable=can('record_lab',patient)&&!locked&&!failed;
  function submit(event) {
    event.preventDefault();
    const form=new FormData(event.currentTarget);
    const values=Object.fromEntries(MUTATION_GROUPS.map(g=>[g.key.toLowerCase(),form.get(g.key)]));
    action.run(()=>labService.mutations(patient.id,{...values,reason:form.get('reason'),expected_version:patient.data_version,expected_lab_version:patient.version}),
      'Mutations saved. Review the prefilled Stanford input below, then run the interpretation.');
  }
  return <div ref={panel} id="mutation-entry" className="mutation-entry"><Card title="Recorded mutations and mutation entry" subtitle="PI → protease (PR); INSTI → integrase (IN); NRTI and NNRTI → reverse transcriptase (RT).">
    <div className="table-wrap"><table><thead><tr><th>Dataset mutation group</th><th>Reported mutations</th></tr></thead><tbody>{MUTATION_GROUPS.map(g=><tr key={g.key}><td>{g.key}</td><td>{mutationValue(record,g)||'Not recorded'}</td></tr>)}</tbody></table></div>
    {record['All Mutations Combined']&&<p className="tiny"><b>Combined report:</b> {record['All Mutations Combined']}</p>}
    <h3>Add / update mutations</h3>
    <p>Enter the mutations under the group printed on the laboratory report. Frequencies such as <code>E157Q(99.7%)</code> are retained in the record; only gene-prefixed mutation tokens are sent to Stanford.</p>
    <Feedback error={action.error} success={action.success}/>
    <form key={`${patient.id}-${patient.data_version}`} onSubmit={submit}><fieldset disabled={!editable||action.busy}><div className="record-grid">
      {MUTATION_GROUPS.map(g=><div className="field" key={g.key}><label htmlFor={`mutation-${g.key}`}>{g.key} mutations ({g.gene})</label><textarea id={`mutation-${g.key}`} name={g.key} maxLength={5000} defaultValue={mutationValue(record,g)} placeholder={g.key==='PI'?'M46I, I54V, V82A':g.key==='INSTI'?'E157Q(99.7%)':g.key==='NRTI'?'M184V, K65R':'K103N'}/></div>)}
      <div className="field full"><label htmlFor="mutation-reason">Report entry / correction note</label><input id="mutation-reason" name="reason" required minLength={10} maxLength={3000} placeholder="e.g. Transcribed from the laboratory report"/></div>
    </div><p className="tiny muted">Saving updates the mutation record, clears previous drug interpretations and the sequence, and keeps sample dates and the laboratory outcome unchanged. The original imported report is retained in the source record. For a report with no mutations, enter its nucleotide sequence in the Stanford form below.</p>
    <div className="form-actions"><button className="btn" disabled={!editable||action.busy}>{action.busy?'Saving mutations…':'Save mutations to laboratory record'}</button></div></fieldset></form>
    {!editable&&<p className="notice">{!can('record_lab',patient)?'Viewing only: sign in with a laboratory account to add or update mutations.':locked?'This laboratory record is reviewed or locked; use the amendment workflow.':'Correct the unsuccessful laboratory outcome before entering mutations.'} <Link className="text-link" to={`/patients/${patient.id}?tab=laboratory`}>Open laboratory workflow →</Link></p>}
    {editable&&patient.status!=='Usable result'&&<p className="notice info">You can save mutation evidence here. Stanford analysis remains unavailable until a usable laboratory result has been recorded in the laboratory workflow.</p>}
  </Card></div>;
}
