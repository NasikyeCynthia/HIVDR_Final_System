import {useEffect,useState} from 'react';
import {useAuth} from '../contexts/AuthContext.jsx';
import {useWorkspace} from '../contexts/WorkspaceContext.jsx';
import usePreferences from '../hooks/usePreferences.js';
import PageHeader from '../components/common/PageHeader.jsx';
import Card from '../components/common/Card.jsx';
import CreateAccountForm from '../components/settings/CreateAccountForm.jsx';
import UserManagement from '../components/settings/UserManagement.jsx';
import DataImportForm from '../components/settings/DataImportForm.jsx';
import ArchivedRecords from '../components/settings/ArchivedRecords.jsx';
import HistoryMapping from '../components/settings/HistoryMapping.jsx';
import AuditLog from '../components/settings/AuditLog.jsx';
import StanfordConnection from '../components/resistance/StanfordConnection.jsx';
export default function SettingsPage(){
 const {user}=useAuth(),{source,setSource,datasetSaving,integrations}=useWorkspace(),{preferences,save}=usePreferences(user.id);
 const [tab,setTab]=useState('account'),[draft,setDraft]=useState(preferences),[dataset,setDataset]=useState(source),[message,setMessage]=useState(''),[error,setError]=useState('');
 useEffect(()=>setDraft(preferences),[preferences]);useEffect(()=>setDataset(source),[source]);
 const tabs=[['account','My account'],['preferences','Preferences'],['workspace','Workspace'],['integrations','Integrations'],...(user.role==='admin'?[['users','Users & access'],['data','Data management'],['audit','Audit history']]:[])];
 return <><PageHeader title="Settings"/><div className="tabs" role="tablist" aria-label="Settings sections">{tabs.map(([key,label])=><button key={key} role="tab" aria-selected={tab===key} className={`tab ${tab===key?'active':''}`} onClick={()=>{setTab(key);setMessage('');setError('');}}>{label}</button>)}</div>{message&&<p className="notice info" role="status">{message}</p>}{error&&<p className="notice error" role="alert">{error}</p>}
 {tab==='account'&&<Card title="My account"><dl className="resistance-context"><div><dt>Name</dt><dd>{user.name}</dd></div><div><dt>Username</dt><dd>{user.username||'Not provided'}</dd></div><div><dt>Role</dt><dd>{({lab:'Laboratory',clinician:'Clinician',nurse:'Nurse',counsellor:'Counsellor',admin:'Administrator'})[user.role]}</dd></div><div><dt>Assigned facility</dt><dd>{user.facility}</dd></div><div><dt>Edit scope</dt><dd>{user.edit_any_facility?'All facilities':user.facility}</dd></div></dl><p className="tiny muted">Contact your system administrator to change account details or access.</p></Card>}
 {tab==='preferences'&&<Card title="Display and notifications"><form onSubmit={e=>{e.preventDefault();try{save(draft);setError('');setMessage('Preferences saved for this account on this browser.');}catch{setError('This browser could not save your preferences.');}}}><div className="settings-row"><div><label htmlFor="display-density">Display density</label><p className="tiny muted">Spacing in tables and records.</p></div><select id="display-density" value={draft.density} onChange={e=>setDraft({...draft,density:e.target.value})}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></div><label className="settings-row"><span>Open Notifications on unread items</span><input type="checkbox" checked={draft.unreadFirst} onChange={e=>setDraft({...draft,unreadFirst:e.target.checked})}/></label><label className="settings-row"><span>Refresh notifications automatically</span><input type="checkbox" checked={draft.autoRefresh} onChange={e=>setDraft({...draft,autoRefresh:e.target.checked})}/></label><div className="form-actions"><button className="btn">Save preferences</button></div></form></Card>}
 {tab==='workspace'&&<Card title="Workspace dataset">{user.role==='admin'?<form onSubmit={async e=>{e.preventDefault();try{await setSource(dataset);setMessage('Workspace dataset updated.');}catch(failure){setError(failure.message);}}}><label htmlFor="workspace-dataset">Dataset</label><select id="workspace-dataset" value={dataset} onChange={e=>setDataset(e.target.value)}><option value="original">Original data</option><option value="synthetic">Synthetic demonstration</option></select><div className="form-actions"><button className="btn" disabled={datasetSaving||dataset===source}>{datasetSaving?'Saving…':'Save workspace settings'}</button></div></form>:<p>Active dataset: <b>{source==='synthetic'?'Synthetic demonstration':'Original data'}</b></p>}</Card>}
 {tab==='integrations'&&<><StanfordConnection/><Card title="Risk model"><p>{integrations?.machine_learning?.message||'Status unavailable'}</p></Card></>}
 {tab==='users'&&<><CreateAccountForm/><UserManagement/></>}{tab==='data'&&<><Card title="Import patient data"><DataImportForm/></Card><ArchivedRecords/><details><summary>Historical import maintenance</summary><HistoryMapping/></details></>}{tab==='audit'&&<AuditLog/>}</>;
}
