import {createContext,useCallback,useContext,useEffect,useRef,useState} from 'react';
import {useAuth} from './AuthContext.jsx';
import {useWorkspace} from './WorkspaceContext.jsx';
import {request} from '../services/api.js';
import usePreferences from '../hooks/usePreferences.js';
const Context=createContext(null);
export function NotificationsProvider({children}){
 const {user}=useAuth(),{source,facility,patients}=useWorkspace(),{preferences}=usePreferences(user.id);
 const [items,setItems]=useState([]),[unread,setUnread]=useState(0),[total,setTotal]=useState(0),[loading,setLoading]=useState(false),[updating,setUpdating]=useState(false),[error,setError]=useState('');
 const [filter,changeFilter]=useState(preferences.unreadFirst?'unread':'all'),[category,changeCategory]=useState('all'),[page,setPage]=useState(0),generation=useRef(0);
 const refresh=useCallback(async()=>{const run=++generation.current;setLoading(true);try{const value=await request(`/notifications/inbox?source=${encodeURIComponent(source)}&facility=${encodeURIComponent(facility)}&status=${filter}&category=${encodeURIComponent(category)}&offset=${page*20}&limit=20`);if(run!==generation.current)return;setItems(value.items);setUnread(value.unread_count);setTotal(value.total);setError('');}catch(failure){if(run===generation.current)setError(failure.message);}finally{if(run===generation.current)setLoading(false);}},[source,facility,user.id,filter,category,page]);
 useEffect(()=>{setPage(0);},[source,facility]);
 useEffect(()=>{setItems([]);refresh();return()=>{generation.current++;};},[refresh,patients]);
 useEffect(()=>{if(!preferences.autoRefresh)return;const timer=setInterval(refresh,60000);window.addEventListener('focus',refresh);return()=>{clearInterval(timer);window.removeEventListener('focus',refresh);};},[preferences.autoRefresh,refresh]);
 async function mark(ids,read=true){if(!ids.length)return;setUpdating(true);try{await request('/notifications/read',{method:'PATCH',data:{ids,read}});await refresh();}catch(failure){setError(failure.message);}finally{setUpdating(false);}}
 function setFilter(value){changeFilter(value);setPage(0);}function setCategory(value){changeCategory(value);setPage(0);}
 return <Context.Provider value={{items,unread,total,loading,updating,error,refresh,mark,preferences,filter,setFilter,category,setCategory,page,setPage}}>{children}</Context.Provider>;
}
export const useNotifications=()=>useContext(Context);
