import {request} from './api.js';
export const operationsService={
 amend:(id,reason)=>request(`/operations/patients/${id}/amend`,{method:'POST',data:{reason}}),
 fields:(id,fields,expected_version)=>request(`/operations/patients/${id}/fields`,{method:'PATCH',data:{fields,expected_version}}),
 archive:(id,archived,reason)=>request(`/operations/patients/${id}/archive`,{method:'POST',data:{archived,reason}}),
 account:data=>request('/operations/accounts',{method:'POST',data}),
 prediction:id=>request(`/operations/patients/${id}/prediction`),
 model:()=>request('/operations/model'),
};
