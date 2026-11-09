import { useState } from 'react';
import PatientTable from './PatientTable.jsx';
import { matchesFilter } from '../../utils/patientFilters.js';
const options = ['missing-pre', 'missing-post', 'failed', 'awaiting-review', 'awaiting-implementation', 'usable', 'pending', 'Low', 'Moderate', 'High', 'Rule unresolved', 'Incomplete', 'Maintained', 'Substituted', 'Switched', 'Plasma', 'DBS'];
export default function PatientList({ patients, tab = 'overview', initialFilter = '' }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState(initialFilter);
  const [page, setPage] = useState(0);
  const filtered = patients.filter(patient => matchesFilter(patient, filter) && [patient.name, patient.external_id, patient.facility, patient.owner_name].join(' ').toLowerCase().includes(search.toLowerCase()));
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const safePage = Math.min(page, pages - 1);
  return <><div className="toolbar"><input aria-label="Search patients" type="search" placeholder="Search patient, ID, facility or care worker" value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} /><select aria-label="Filter records" value={filter} onChange={event => { setFilter(event.target.value); setPage(0); }}><option value="">All records</option>{[...new Set([...options, initialFilter].filter(Boolean))].map(value => <option value={value} key={value}>{value.replaceAll('-', ' ')}</option>)}</select><span className="tiny muted">{filtered.length} matches</span></div><section className="card"><PatientTable patients={filtered.slice(safePage * 25, safePage * 25 + 25)} tab={tab} /><div className="card-footer"><span>Page {safePage + 1} of {pages}</span><div><button className="text-link" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>← Previous</button> &nbsp; <button className="text-link" disabled={safePage === pages - 1} onClick={() => setPage(safePage + 1)}>Next →</button></div></div></section></>;
}
