import {useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {patientService} from '../../services/patientService.js';
import Badge from '../common/Badge.jsx';
import {DRUG_GROUPS, EXPOSURES, RESISTANCE_FIELDS, exposureValue, regimenDrugs, resistanceResult, LEVEL_COLORS, MUTATION_GROUPS, mutationValue, sampleTreatment} from '../../utils/resistance.js';

export default function ResistancePatientList({patients}) {
  const [search,setSearch]=useState(''), [page,setPage]=useState(0);
  const [columns,setColumns]=useState([]), [extra,setExtra]=useState([]);
  const [rows,setRows]=useState({}), [error,setError]=useState(''), [loading,setLoading]=useState(false);
  const filtered=patients.filter(p=>[p.external_id,p.name,p.regimen,p.facility].join(' ').toLowerCase().includes(search.toLowerCase()));
  const pages=Math.max(1,Math.ceil(filtered.length/25)), current=Math.min(page,pages-1);
  const visible=filtered.slice(current*25,current*25+25);
  const idsKey=visible.map(p=>p.id).join(','), extraKey=extra.join('\u001f');
  useEffect(()=>{
    let active=true;
    const relevant=new Set(['Age(yrs)','sex','Sample Type','Sample collection Date','dateTestedForDR','Date referred to DR Lab','DR_results_releaseDate','amplified','No. of DR tests','Accessory Mutations','Other Mutations','ART@VL@DR start date','ART@VL@DR stop date','Regimen changes prior to sample collection']);
    patientService.columns().then(r=>{if(active)setColumns(r.columns.filter(c=>!RESISTANCE_FIELDS.includes(c)&&(relevant.has(c)||c.startsWith('has relevant '))));}).catch(e=>{if(active)setError(e.message);});
    return ()=>{active=false;};
  },[]);
  useEffect(()=>{
    let active=true; setRows({});setError('');
    if(!idsKey){setLoading(false);return ()=>{active=false;};}
    setLoading(true);
    patientService.table(idsKey.split(',').map(Number),[...RESISTANCE_FIELDS,...(extraKey?extraKey.split('\u001f'):[])],true)
      .then(data=>{if(active)setRows(Object.fromEntries(data.map(r=>[r.id,r])));})
      .catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[idsKey,extraKey,patients]);
  return <>
    <div className="toolbar"><input aria-label="Search resistance records" type="search" placeholder="Search patient ID, name, regimen or facility" value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/><span>{filtered.length} {filtered.length===1?'patient':'patients'}</span></div>
    <p className="tiny muted">Treatment at sample collection, the four recorded mutation groups, all seven exposure fields and all 15 drug interpretations are shown by default. Scroll horizontally to compare drug classes. Exposure is recorded history; resistance is an interpretation for a specific drug.</p>
    <details className="column-picker"><summary>Choose more variables ({extra.length} added)</summary><p className="tiny muted">The standard resistance fields remain visible.</p><button type="button" className="btn secondary small" onClick={()=>setExtra([])}>Clear additional variables</button><div className="column-picker-grid">{columns.map(c=><label key={c}><input type="checkbox" checked={extra.includes(c)} onChange={()=>setExtra(v=>v.includes(c)?v.filter(x=>x!==c):[...v,c])}/>{c}</label>)}</div></details>
    {error&&<p className="notice error" role="alert">Could not load resistance evidence: {error}</p>}
    <div role="status" aria-live="polite">{loading?'Loading exposure and resistance evidence…':''}</div>
    <section className="card"><div className="table-wrap" tabIndex={0} aria-label="Patient resistance classifications; scroll horizontally"><table className="resistance-patient-table"><thead>
      <tr><th rowSpan={2}>Patient ID / name</th><th rowSpan={2}>Treatment line at sample collection</th><th rowSpan={2}>Drugs</th><th colSpan={4}>Recorded laboratory mutations</th><th colSpan={7}>Drug exposure history</th>{DRUG_GROUPS.map(g=><th key={g.name} colSpan={g.drugs.length}>{g.name}</th>)}<th rowSpan={2}>Result source / API analysis</th>{extra.map(c=><th rowSpan={2} key={c}>{c}</th>)}<th rowSpan={2}>Action</th></tr>
      <tr>{MUTATION_GROUPS.map(g=><th key={g.key}>{g.key} mutations</th>)}{EXPOSURES.map(([key,label])=><th key={key} title={key}>{label}</th>)}{DRUG_GROUPS.flatMap(g=>g.drugs.map(d=><th key={d}>{d}</th>))}</tr>
    </thead><tbody>{visible.map(patient=>{
      const row=rows[patient.id],treatment=sampleTreatment(patient,row?.fields),drugs=regimenDrugs(treatment.regimen);
      return <tr key={patient.id}><td className="patient-cell"><b>{patient.external_id}</b><small>{patient.name}</small></td><td>{treatment.line||'Not recorded'}</td><td>{treatment.regimen||'Not recorded'}</td>
        {MUTATION_GROUPS.map(g=><td key={g.key} className="mutation-cell">{row?mutationValue(row.fields,g)||'Not recorded':error?'Unavailable':'Loading…'}</td>)}
        {EXPOSURES.map(([key])=><td key={key}>{row?exposureValue(row.fields[key]):error?'Unavailable':'Loading…'}</td>)}
        {DRUG_GROUPS.flatMap(g=>g.drugs.map(drug=>{
          const r=row?resistanceResult(drug,row.interpretation,row.fields):null;
          return <td key={drug}><Badge color={LEVEL_COLORS[r?.level]||''}>{r?.text||(error?'Unavailable':'Loading…')}</Badge>{drugs.includes(drug)&&<div className="tiny"><b>On regimen</b></div>}</td>;
        }))}
        <td>{row?.interpretation?<><b>Stanford API</b><div>{row.interpretation.version?.text}</div><div className="tiny muted">{row.interpreted_at||'Time not recorded'}</div></>:row?<><b>{MUTATION_GROUPS.some(g=>mutationValue(row.fields,g))?'Recorded mutations available':'No saved Stanford API analysis'}</b><div className="tiny muted">Existing mutations are shown above. Drug categories require a recorded interpretation or Stanford analysis.</div></>:error?'Unavailable':'Loading…'}</td>
        {extra.map(c=><td key={c}>{row?String(row.fields[c]??'').trim()||'Not recorded':error?'Unavailable':'Loading…'}</td>)}
        <td><Link className="text-link" to={`/patients/${patient.id}?tab=resistance`}>Mutations / analyse →</Link><div><Link className="text-link" to={`/patients/${patient.id}?tab=resistance#mutation-entry`}>Add / update mutations</Link></div></td></tr>;
    })}</tbody></table>{!visible.length&&<p className="empty">No patients match this view.</p>}</div>
    <div className="card-footer"><span>Page {current+1} of {pages}</span><div><button type="button" className="text-link" disabled={current===0} onClick={()=>setPage(current-1)}>← Previous</button> · <button type="button" className="text-link" disabled={current===pages-1} onClick={()=>setPage(current+1)}>Next →</button></div></div></section>
  </>;
}
