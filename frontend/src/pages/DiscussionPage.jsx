import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {useWorkspace} from '../contexts/WorkspaceContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import Badge from '../components/common/Badge.jsx';
import {reviewStage,ACTION_LABELS} from '../utils/discussion.js';

export default function DiscussionPage() {
  const {visiblePatients,refresh}=useWorkspace();
  const [search,setSearch]=useState(''),[filter,setFilter]=useState('all'),[page,setPage]=useState(0);
  const active=visiblePatients.some(p=>['pending','running'].includes(p.interpretation_status));
  useEffect(()=>{refresh().catch(()=>{});},[refresh]);
  useEffect(()=>{if(!active)return;const timer=setInterval(()=>refresh().catch(()=>{}),8000);return()=>clearInterval(timer);},[active,refresh]);
  const relevant=visiblePatients.filter(p=>p.status==='Usable result'||p.decision);
  const filtered=relevant.filter(p=>(filter==='all'||reviewStage(p).key===filter)&&[p.external_id,p.name,p.regimen,p.facility].join(' ').toLowerCase().includes(search.toLowerCase()));
  const pages=Math.max(1,Math.ceil(filtered.length/25)),current=Math.min(page,pages-1),shown=filtered.slice(current*25,current*25+25);
  return <><PageHeader title="Discussion and clinician approval" description="Clinical review and treatment approvals."/>
    <div className="toolbar"><input type="search" aria-label="Search discussion queue" placeholder="Patient ID, name, drugs or facility" value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/><select aria-label="Review status" value={filter} onChange={e=>{setFilter(e.target.value);setPage(0);}}><option value="all">All discussion records</option><option value="processing">Stanford processing</option><option value="awaiting">Awaiting Stanford analysis</option><option value="attention">Analysis needs attention</option><option value="ready">Ready for clinician review</option><option value="approved">Clinician approved</option></select><span>{filtered.length} records</span></div>
    <section className="card"><div className="table-wrap"><table><thead><tr><th>Patient No.</th><th>Drugs</th><th>Laboratory result released</th><th>Stanford interpretation</th><th>Draft action</th><th>Clinician decision</th><th>Implementation</th><th>Action</th></tr></thead><tbody>{shown.map(p=>{const stage=reviewStage(p);return <tr key={p.id}><td>{p.external_id}<div className="tiny muted">{p.name}</div></td><td>{p.regimen||'Not recorded'}</td><td>{p.report_at?.slice(0,10)||'Not recorded'}</td><td><Badge color={stage.color}>{stage.label}</Badge>{p.interpreted_at&&<div className="tiny muted">Saved {p.interpreted_at}</div>}</td><td>{p.suggested_action?ACTION_LABELS[p.suggested_action]:stage.key==='approved'?'Not stored':stage.key==='ready'?'Individual clinician assessment required':'Awaiting evidence'}</td><td>{p.decision?<>{ACTION_LABELS[p.decision]}<div className="tiny muted">{p.reviewer_name||'Clinician'} · {p.decision_at?.slice(0,10)}</div></>:'Not approved'}</td><td>{p.implemented_at?'Recorded':p.decision?'Pending nurse / counsellor':'Awaiting approval'}</td><td><Link className="text-link" to={`/patients/${p.id}?tab=discussion`}>Review evidence / approve →</Link></td></tr>;})}</tbody></table>{!shown.length&&<p className="empty">No records match this discussion view.</p>}</div><div className="card-footer"><span>Page {current+1} of {pages}</span><div><button type="button" className="text-link" disabled={current===0} onClick={()=>setPage(current-1)}>← Previous</button> · <button type="button" className="text-link" disabled={current===pages-1} onClick={()=>setPage(current+1)}>Next →</button></div></div></section>
  </>;
}
