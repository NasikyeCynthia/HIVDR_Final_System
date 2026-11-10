import { useEffect, useState } from 'react';
import PatientTable from './PatientTable.jsx';
import { matchesFilter } from '../../utils/patientFilters.js';
import { patientService } from '../../services/patientService.js';
import { useAuth } from '../../contexts/AuthContext.jsx';

const options = ['missing-pre', 'missing-post', 'failed', 'awaiting-review', 'awaiting-implementation', 'usable', 'pending', 'Low', 'Intermediate', 'High', 'Rule unresolved', 'Incomplete', 'Maintained', 'Substituted', 'Switched', 'Plasma', 'DBS'];
const defaultColumns = ['ART at sample collection(ART@VL@DR)', 'Treatment Line at Sample collection', 'VL Leading to DR', 'Facility'];

export default function PatientList({ patients, tab = 'overview', initialFilter = '', datasetView = false }) {
  const { user } = useAuth();
  const isNurse = user.role === 'nurse';
  const nurseHiddenFilters = new Set(['missing-post','failed','awaiting-review','awaiting-implementation','usable','pending','Maintained','Substituted','Switched','Plasma','DBS']);
  const filterOptions = isNurse ? options.filter(value => !nurseHiddenFilters.has(value)) : options;
  const safeInitialFilter = isNurse && nurseHiddenFilters.has(initialFilter) ? '' : initialFilter;
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState(safeInitialFilter);
  const [lineFilter, setLineFilter] = useState('');
  const [regimenFilter, setRegimenFilter] = useState('');
  const [page, setPage] = useState(0);
  const [availableColumns, setAvailableColumns] = useState([]);
  const [selectedColumns, setSelectedColumns] = useState(defaultColumns);
  const [recordFields, setRecordFields] = useState({});
  const [tableError, setTableError] = useState('');
  const visibleColumns = isNurse
    ? (availableColumns.length ? selectedColumns.filter(field => availableColumns.includes(field)) : defaultColumns)
    : selectedColumns;
  const filtered = patients.filter(patient => matchesFilter(patient, filter) && matchesFilter(patient, lineFilter) && matchesFilter(patient, regimenFilter) && [patient.name, patient.external_id, patient.facility, patient.owner_name].join(' ').toLowerCase().includes(search.toLowerCase()));
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const safePage = Math.min(page, pages - 1);
  const pagePatients = filtered.slice(safePage * 25, safePage * 25 + 25);
  const idsKey = pagePatients.map(patient => patient.id).join(',');
  const columnsKey = visibleColumns.join('\u001f');
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
      setSelectedColumns(current => current.filter(field => availableColumns.includes(field)));
    }
  }, [availableColumns, isNurse]);

  useEffect(() => {
    if (!datasetView || !idsKey) { setRecordFields({}); return undefined; }
    let active = true;
    setRecordFields({});
    setTableError('');
    const ids = idsKey.split(',').map(Number);
    const fields = columnsKey ? columnsKey.split('\u001f') : [];
    patientService.table(ids, fields).then(rows => {
      if (active) setRecordFields(Object.fromEntries(rows.map(row => [row.id, row.fields || {}])));
    }).catch(failure => { if (active) { setRecordFields({}); setTableError(failure.message); } });
    return () => { active = false; };
  }, [datasetView, idsKey, columnsKey]);

  function toggleColumn(column) {
    setSelectedColumns(current => {
      const safeCurrent = isNurse && availableColumns.length
        ? current.filter(item => availableColumns.includes(item))
        : current;
      return safeCurrent.includes(column) ? safeCurrent.filter(item => item !== column) : [...safeCurrent, column];
    });
  }

  return <>
    {datasetView && <details className="column-picker"><summary>Choose dataset columns ({visibleColumns.length} selected)</summary><p className="tiny muted">Patient ID/name and risk stay visible. Only the current page is loaded for selected dataset fields.{isNurse?' Laboratory and committee fields are restricted for nurse accounts.':''}</p><div className="column-picker-actions"><button type="button" className="btn secondary small" onClick={() => setSelectedColumns(availableColumns)}>Select all</button><button type="button" className="btn secondary small" onClick={() => setSelectedColumns([])}>Unselect all</button></div><div className="column-picker-grid">{availableColumns.map(column => <label key={column}><input type="checkbox" checked={visibleColumns.includes(column)} onChange={() => toggleColumn(column)} />{column}</label>)}</div></details>}
    <div className="toolbar"><input aria-label="Search patients" type="search" placeholder="Search patient, ID, facility or care worker" value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} /><select aria-label="Filter records" value={filter} onChange={event => { setFilter(event.target.value); setPage(0); }}><option value="">All records</option>{[...new Set([...filterOptions, safeInitialFilter].filter(Boolean))].map(value => <option value={value} key={value}>{value === 'missing-pre' ? 'Incomplete patient profiles' : value === 'missing-post' ? 'Incomplete committee follow-up' : value === 'Incomplete' ? 'Incomplete risk assessment' : value.replaceAll('-', ' ')}</option>)}</select>{tab === 'risk' && <><select aria-label="Filter treatment line" value={lineFilter} onChange={event => { setLineFilter(event.target.value); setPage(0); }}><option value="">All treatment lines</option>{lineOptions.map(value => <option key={value} value={`line:${value}`}>Line {value}</option>)}</select><select aria-label="Filter regimen" value={regimenFilter} onChange={event => { setRegimenFilter(event.target.value); setPage(0); }}><option value="">All regimens</option>{regimenOptions.map(value => <option key={value} value={`regimen:${value}`}>{value}</option>)}</select></>}<span className="tiny muted">{filtered.length} matches</span></div>
    {tableError && <p className="notice error">Could not load dataset columns: {tableError}</p>}
    <section className="card"><PatientTable patients={pagePatients} tab={tab} datasetView={datasetView} columns={visibleColumns} recordFields={recordFields} /><div className="card-footer"><span>Page {safePage + 1} of {pages}</span><div><button className="text-link" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>← Previous</button> &nbsp; <button className="text-link" disabled={safePage === pages - 1} onClick={() => setPage(safePage + 1)}>Next →</button></div></div></section>
  </>;
}
