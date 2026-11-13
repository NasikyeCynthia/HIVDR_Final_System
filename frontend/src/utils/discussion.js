export const ACTION_LABELS={Maintained:'Maintain',Substituted:'Substitute',Switched:'Switch'};
export function reviewStage(patient) {
  if(patient.decision)return {key:'approved',label:'Clinician approved',color:'green'};
  if(patient.status!=='Usable result')return {key:'laboratory',label:'Awaiting usable lab result',color:''};
  const status=patient.automation?.status||patient.interpretation_status;
  if(['pending','running'].includes(status))return {key:'processing',label:'Stanford analysis in progress',color:'yellow'};
  if(patient.interpretation||patient.has_interpretation)return {key:'ready',label:'Ready for clinician review',color:'green'};
  if(['failed','needs_input'].includes(status))return {key:'attention',label:status==='failed'?'Stanford analysis failed':'Laboratory input needed',color:'red'};
  return {key:'awaiting',label:'Awaiting Stanford analysis',color:'yellow'};
}
