import {request} from './api.js';
export const workflowService={
 retryInterpretation:id=>request(`/workflow/patients/${id}/retry-interpretation`,{method:'POST'}),
 interpret:(id,data)=>request(`/workflow/patients/${id}/interpret`,{method:'POST',data}),
 psychosocial:(id,data)=>request(`/workflow/patients/${id}/psychosocial`,{method:'PUT',data}),
 mapHistory:()=>request('/workflow/map-original-history',{method:'POST'}),
 markReviewed:(id,notes)=>request(`/workflow/patients/${id}/review`,{method:'POST',data:{notes}}),
 assignLab:(id,lab_owner)=>request(`/workflow/patients/${id}/lab-assignment`,{method:'PATCH',data:{lab_owner:Number(lab_owner)}}),
 updateUser:(id,data)=>request(`/workflow/users/${id}`,{method:'PATCH',data}),
};
