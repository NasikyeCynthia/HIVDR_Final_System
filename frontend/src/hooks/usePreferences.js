import {useEffect,useState} from 'react';
export const DEFAULT_PREFERENCES={density:'comfortable',unreadFirst:true,autoRefresh:true};
const key=id=>`hivdr-preferences:${id}`;
function load(id){try{return {...DEFAULT_PREFERENCES,...JSON.parse(localStorage.getItem(key(id))||'{}')};}catch{return {...DEFAULT_PREFERENCES};}}
export default function usePreferences(userId){
  const [preferences,setPreferences]=useState(()=>load(userId));
  useEffect(()=>{const changed=()=>setPreferences(load(userId));changed();window.addEventListener('hivdr-preferences',changed);window.addEventListener('storage',changed);return()=>{window.removeEventListener('hivdr-preferences',changed);window.removeEventListener('storage',changed);};},[userId]);
  function save(value){localStorage.setItem(key(userId),JSON.stringify(value));setPreferences(value);window.dispatchEvent(new Event('hivdr-preferences'));}
  return {preferences,save};
}
