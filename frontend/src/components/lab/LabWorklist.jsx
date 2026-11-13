import { useState } from 'react';
import PatientList from '../patients/PatientList.jsx';

// The laboratory's own work, not every patient record. A patient appears once there is laboratory work:
// eligible for a DR test, requested, sampled, being tested, resulted, or needing a repeat sample.
const SEGMENTS = [
  ['vl', 'Viral load results awaited', p => p.vl_pending > 0],
  ['request', 'To request', p => p.eligibility?.status === 'eligible' && !p.referred_at && p.status === 'Not collected'],
  ['collect', 'To collect', p => p.status === 'Not collected' && (p.referred_at || p.repeat_requested_at)],
  ['process', 'In process', p => p.status === 'Pending'],
  ['amplified', 'Amplified', p => p.status === 'Usable result'],
  ['failed', 'Failed / returned', p => ['Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'].includes(p.status)],
];
export const isLabWork = p => SEGMENTS.some(([, , test]) => test(p));

export default function LabWorklist({ patients }) {
  const [segment, setSegment] = useState('all');
  const lab = patients.filter(isLabWork);
  const current = SEGMENTS.find(([key]) => key === segment);
  const shown = current ? lab.filter(current[2]) : lab;
  return <>
    <div className="segments" role="tablist">{[...SEGMENTS, ['all', 'All laboratory records', () => true]].map(([key, label, test]) =>
      <button key={key} role="tab" aria-selected={segment === key} className={`segment ${segment === key ? 'active' : ''}`} onClick={() => setSegment(key)}>{label}<b>{lab.filter(test).length.toLocaleString()}</b></button>)}</div>
    <PatientList key={segment} patients={shown} tab="laboratory" />
  </>;
}
