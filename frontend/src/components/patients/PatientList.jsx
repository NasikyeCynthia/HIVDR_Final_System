import { eligibilityLabel } from '../../utils/eligibility.js';
import { useEffect, useState } from 'react';
import PatientTable from './PatientTable.jsx';
import { matchesFilter } from '../../utils/patientFilters.js';
import { patientService } from '../../services/patientService.js';
import { useAuth } from '../../contexts/AuthContext.jsx';

const options = ['missing-pre', 'missing-post', 'discussion-pending', 'discussion-done', 'discussion-blank', 'sample-type-blank', 'amplified-blank', 'failed', 'returned', 'awaiting-receipt', 'at-dr-lab', 'lab-problem', 'awaiting-review', 'awaiting-implementation', 'usable', 'pending', 'flagged', 'risk:High', 'risk:Intermediate', 'risk:Low', 'risk:Incomplete', 'elig:eligible', 'elig:needs_documentation', 'elig:not_yet', 'elig:in_process', 'elig:suppressed', 'elig:insufficient_data', 'Maintained', 'Substituted', 'Switched', 'Plasma', 'DBS'];

export default function PatientList({ patients, tab = 'overview', initialFilter = '', datasetView = false }) {
  const { user } = useAuth();
  const isNurse = false; // all roles may view every column; editing is per role
  const nurseHiddenFilters = new Set();
  // Each page offers only the filters relevant to it; Patient records offers all of them.
  const byTab = {
    risk: ['flagged', 'risk:High', 'risk:Intermediate', 'risk:Low', 'risk:Incomplete', 'elig:eligible', 'elig:needs_documentation', 'elig:not_yet', 'elig:in_process', 'elig:suppressed', 'elig:insufficient_data', 'failing:child', 'failing:adolescent', 'failing:adult', 'failing:second', 'failing:third'],
    laboratory: ['awaiting-receipt', 'at-dr-lab', 'returned', 'lab-problem', 'failed', 'usable', 'pending', 'Plasma', 'DBS', 'sample-type-blank', 'amplified-blank'],
    discussion: ['awaiting-review', 'missing-pre', 'discussion-pending', 'discussion-done', 'discussion-blank', 'Maintained', 'Substituted', 'Switched', 'awaiting-implementation', 'missing-post'],
  };
  const filterOptions = byTab[tab] || options;
  const safeInitialFilter = isNurse && nurseHiddenFilters.has(initialFilter) ? '' : initialFilter;
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState(safeInitialFilter);
  const [lineFilter, setLineFilter] = useState('');
  const [regimenFilter, setRegimenFilter] = useState('');
  const [page, setPage] = useState(0);
  const [availableColumns, setAvailableColumns] = useState([]);
  const [selectedColumns, setSelectedColumns] = useState(null);
  const [recordFields, setRecordFields] = useState({});
  const [tableError, setTableError] = useState('');
  const visibleColumns = selectedColumns === null ? availableColumns : availableColumns.filter(field=>selectedColumns.includes(field));
  const filtered = patients.filter(patient => matchesFilter(patient, filter) && matchesFilter(patient, lineFilter) && matchesFilter(patient, regimenFilter) && [patient.name, patient.external_id, patient.facility, patient.owner_name].join(' ').toLowerCase().includes(search.toLowerCase()));
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const safePage = Math.min(page, pages - 1);
  const pagePatients = filtered.slice(safePage * 25, safePage * 25 + 25);
  const idsKey = pagePatients.map(patient => patient.id).join(',');
  const columnsKey = (datasetView?visibleColumns:tab==='risk'?['Age(yrs)','sex','VL Leading to DR','Treatment Line at Sample collection','ART at sample collection(ART@VL@DR)']:[]).join('\u001f');
  const lineOptions = [...new Set(patients.map(p => p.treatment_line).filter(v => v != null && v !== ''))].sort((a,b) => Number(a)-Number(b));
  const regimenOptions = [...new Set(patients.map(p => p.regimen).filter(Boolean))].sort();

  useEffect(() => {
    if (!datasetView) return undefined;
    let active = true;
    patientService.columns().then(response => { if (active) setAvailableColumns(response.columns || []); }).catch(failure => { if (active) setTableError(failure.message); });
    return () => { active = false; };
  }, [datasetView]);

  useEffect(() => {
    if (isNurse && availableColumns.length) {
      setSelectedColumns(current => current === null ? null : current.filter(field => availableColumns.includes(field)));
    }
  }, [availableColumns, isNurse]);

  useEffect(() => {
    if ((!datasetView && tab!=='risk') || !idsKey) { setRecordFields({}); return undefined; }
    let active = true;
    setRecordFields({});
    setTableError('');
    const ids = idsKey.split(',').map(Number);
    const fields = columnsKey ? columnsKey.split('\u001f') : [];
    patientService.table(ids, fields).then(rows => {
      if (active) setRecordFields(Object.fromEntries(rows.map(row => [row.id, row.fields || {}])));
    }).catch(failure => { if (active) { setRecordFields({}); setTableError(failure.message); } });
    return () => { active = false; };
  }, [datasetView, tab, idsKey, columnsKey, patients]);

  function toggleColumn(column) {
    setSelectedColumns(current => {
      const safeCurrent = current === null ? availableColumns : current;
      return safeCurrent.includes(column) ? safeCurrent.filter(item => item !== column) : [...safeCurrent, column];
    });
  }

  return <>
    {datasetView && <details className="column-picker"><summary>Choose dataset columns ({visibleColumns.length} selected)</summary><p className="tiny muted">All dataset columns are shown by default in their original order. Risk and eligibility are added after the source columns. Hide fields here if needed; their dataset order is retained.{isNurse?' Laboratory and committee fields are restricted for nurse accounts.':''}</p><div className="column-picker-actions"><button type="button" className="btn secondary small" onClick={() => setSelectedColumns(null)}>Show all in dataset order</button><button type="button" className="btn secondary small" onClick={() => setSelectedColumns([])}>Unselect all</button></div><div className="column-picker-grid">{availableColumns.map(column => <label key={column}><input type="checkbox" checked={visibleColumns.includes(column)} onChange={() => toggleColumn(column)} />{column}</label>)}</div></details>}
    <div className="toolbar"><input aria-label="Search patients" type="search" placeholder="Search patient, ID, facility or care worker" value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} /><select aria-label="Filter records" value={filter} onChange={event => { setFilter(event.target.value); setPage(0); }}><option value="">All records</option>{[...new Set([...filterOptions, safeInitialFilter].filter(Boolean))].map(value => <option value={value} key={value}>{value === 'missing-pre' ? 'Incomplete patient profiles' : value === 'missing-post' ? 'Incomplete post-decision follow-up' : value === 'discussion-pending' ? 'Discussion pending' : value === 'discussion-done' ? 'Discussion done' : value === 'discussion-blank' ? 'Discussion status blank' : value === 'sample-type-blank' ? 'Sample type blank' : value === 'amplified-blank' ? 'Amplified value blank' : value === 'returned' ? 'Rejected or deferred at CPHL' : value === 'awaiting-receipt' ? 'Collected, not yet received at CPHL' : value === 'at-dr-lab' ? 'At DR laboratory' : value === 'lab-problem' ? 'Sample quality problems' : value === 'flagged' ? 'Flagged: high risk of resistance' : value.startsWith('failing:') ? 'Failing: ' + ({child:'children <15, 1st line',adolescent:'adolescents 15–19, 1st line',adult:'adults 20+, 1st line',second:'2nd line',third:'3rd line'})[value.slice(8)] : value.startsWith('risk:') ? 'Risk: ' + value.slice(5) : value.startsWith('elig:') ? 'Eligibility: ' + eligibilityLabel(value.slice(5)) : value.replaceAll('-', ' ')}</option>)}</select>{tab === 'risk' && <><select aria-label="Filter treatment line" value={lineFilter} onChange={event => { setLineFilter(event.target.value); setPage(0); }}><option value="">All treatment lines</option>{lineOptions.map(value => <option key={value} value={`line:${value}`}>Line {value}</option>)}</select><select aria-label="Filter regimen" value={regimenFilter} onChange={event => { setRegimenFilter(event.target.value); setPage(0); }}><option value="">All regimens</option>{regimenOptions.map(value => <option key={value} value={`regimen:${value}`}>{value}</option>)}</select></>}<span className="tiny muted">{filtered.length} matches</span></div>
    {tableError && <p className="notice error">Could not load dataset columns: {tableError}</p>}
    <section className="card"><PatientTable patients={pagePatients} tab={tab} datasetView={datasetView} columns={visibleColumns} recordFields={recordFields} /><div className="card-footer"><span>Page {safePage + 1} of {pages}</span><div><button className="text-link" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>← Previous</button> &nbsp; <button className="text-link" disabled={safePage === pages - 1} onClick={() => setPage(safePage + 1)}>Next →</button></div></div></section>
  </>;
}
