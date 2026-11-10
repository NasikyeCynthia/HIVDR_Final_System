export function getFacilityGroups(patients = []) {
  const groups = { original: new Set(), synthetic: new Set() };

  for (const patient of patients) {
    const dataset = patient.source === 'manual'
      ? (patient.dataset_source || 'original')
      : patient.source;
    if (patient.facility && groups[dataset]) groups[dataset].add(patient.facility);
  }

  return {
    original: [...groups.original].sort((a, b) => a.localeCompare(b)),
    synthetic: [...groups.synthetic].sort((a, b) => a.localeCompare(b)),
  };
}
