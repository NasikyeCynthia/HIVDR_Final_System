export function taskQueue(patients,users){
 const tasks=[];const name=id=>users.find(u=>u.id===id)?.name;
 function add(p,type,reason,ownerId,fallback,tab,start){const age=start?Math.max(0,Math.floor((Date.now()-new Date(start).getTime())/86400000)):null;tasks.push({key:`${p.id}-${type}`,patient:p,reason,type,owner:name(ownerId)||fallback,ownerId,tab,days:age,overdue:age!=null&&age>7});}
 for(const p of patients){
  if(p.amplified===1&&p.discussion_status==='Pending'&&p.missing_pre.length)add(p,'Profile',`Missing: ${p.missing_pre.join(', ')}`,p.assigned_to,'Unassigned nurse / counsellor','profile',p.created_at);
  if(p.sample_type==='DBS'&&!p.dbs_reason)add(p,'DBS reason','Record why DBS was used',p.lab_owner,'Unassigned laboratory officer','laboratory',p.sample_at);
  if(['Unamplified','Sequencing failed'].includes(p.status))add(p,'Failed test',`${p.failure_reason||'Failure reason missing'}${p.repeat_requested_at?' · new sample requested':' · request a new sample'}`,p.lab_owner,'Unassigned laboratory officer','laboratory',p.report_at);
  if(p.repeat_requested_at&&['Unamplified','Sequencing failed'].includes(p.status))add(p,'New sample','Arrange recollection of the requested sample',p.assigned_to,'Unassigned nurse / counsellor','laboratory',p.repeat_requested_at);
  if(p.status==='Pending')add(p,'Lab result','Laboratory result remains pending',p.lab_owner,'Unassigned laboratory officer','laboratory',p.sample_at);
  if(p.status==='Usable result'&&!p.reviewed_at)add(p,'Clinical review',p.pre_complete?'Usable result ready for review':'Review awaits profile completion',p.reviewer,'Facility clinician','discussion',p.report_at);
  if(p.decision&&!p.implemented_at)add(p,'Implementation',`Implement approved decision: ${p.decision}`,p.assigned_to,'Unassigned nurse / counsellor','decision',p.decision_at);
  if(p.discussion_status==='Done'&&p.missing_post.length)add(p,'Post-discussion',`Complete: ${p.missing_post.join(', ')}`,p.assigned_to,'Unassigned nurse / counsellor','decision',p.decision_at);
 }
 return tasks.sort((a,b)=>Number(b.overdue)-Number(a.overdue)||(b.days||0)-(a.days||0));
}
