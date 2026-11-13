export const EXPOSURES = [
  ['exposure_to_AZT', 'AZT'], ['exposure_to_ABC', 'ABC'],
  ['exposure_to_AZT_and_ABC', 'AZT and ABC'], ['exposure_to_AZT_only', 'AZT only'],
  ['exposure_to_LPV', 'LPV'], ['exposure_to_DTG', 'DTG'],
  ['exposure_to_LPVr_or_DTG', 'LPV/r or DTG'],
];
export const DRUG_GROUPS = [
  {name: 'INSTIs', description: 'Integrase strand transfer inhibitors', drugs: ['BIC', 'CAB', 'DTG', 'RAL']},
  {name: 'Protease inhibitors', description: 'Protease inhibitors', drugs: ['ATV/r', 'DRV/r', 'LPV/r']},
  {name: 'NRTIs', description: 'Nucleoside/nucleotide reverse transcriptase inhibitors', drugs: ['3TC', 'ABC', 'AZT', 'TDF']},
  {name: 'NNRTIs', description: 'Non-nucleoside reverse transcriptase inhibitors', drugs: ['DOR', 'EFV', 'ETR', 'NVP']},
];
export const MUTATION_GROUPS = [
  {key:'PI',gene:'PR',fields:['PI','PiMajor Mutations','PiMinor Mutations','PI Mutations Combined']},
  {key:'INSTI',gene:'IN',fields:['INSTI','INSTI Mutations']},
  {key:'NRTI',gene:'RT',fields:['NRTI','NRTI Mutations']},
  {key:'NNRTI',gene:'RT',fields:['NNRTI','NNRTI Mutations']},
];
export const SAMPLE_REGIMEN='ART at sample collection(ART@VL@DR)';
export const SAMPLE_LINE='Treatment Line at Sample collection';
export const RESISTANCE_FIELDS = [...new Set([SAMPLE_LINE,SAMPLE_REGIMEN,...MUTATION_GROUPS.flatMap(g=>g.fields),'All Mutations Combined',...EXPOSURES.map(([key]) => key), ...DRUG_GROUPS.flatMap(g => g.drugs.map(d => `Resistance to ${d}`))])];
export const LEVEL_COLORS = {1:'green', 2:'yellow', 3:'yellow', 4:'red', 5:'red'};

export function mutationValue(record,group) {
  const values=group.fields.map(key=>String(record?.[key]??'').trim()).filter(value=>/[A-Z]?\d+[A-Z*_/\-]+/i.test(value));
  // The original class column takes priority; older aliases remain supported.
  const primary=String(record?.[group.key]??'').trim();
  if (values.includes(primary)) return primary;
  return [...new Set(values)].join('; ');
}
export function sampleTreatment(patient,record={}) {
  return {
    regimen:Object.hasOwn(record,SAMPLE_REGIMEN)?String(record[SAMPLE_REGIMEN]??'').trim():(patient.regimen||''),
    line:Object.hasOwn(record,SAMPLE_LINE)?String(record[SAMPLE_LINE]??'').trim():(patient.treatment_line?`Line ${patient.treatment_line}`:''),
  };
}

export function exposureValue(value) {
  const text = String(value ?? '').trim();
  if (!text) return 'Not recorded';
  if (/^(1|yes|true)$/i.test(text)) return 'Yes';
  if (/^(0|no|false)$/i.test(text)) return 'No';
  if (/^(unknown|not known|na|n\/a)$/i.test(text)) return 'Unknown';
  return text;
}

export function regimenDrugs(regimen) {
  const aliases = {LPV:'LPV/r', ATV:'ATV/r', DRV:'DRV/r', ZDV:'AZT'};
  return [...new Set(String(regimen || '').toUpperCase().replace(/\/R\b/g, '').split(/[-+/,\s]+/)
    .filter(Boolean).map(d => aliases[d] || d))];
}

export function drugResults(interpretation) {
  return (interpretation?.analysis?.drugResistance || []).flatMap(g =>
    (g.drugScores || []).map(d => ({...d, gene:g.gene?.name})));
}

export function resistanceResult(drug, interpretation, record = {}) {
  const score = drugResults(interpretation).find(d => d.drug?.displayAbbr === drug);
  if (score) return {text:score.text, level:score.level, score:score.score, source:'Stanford API'};
  // A saved analysis defines its own coverage; never fill its gaps with an older dataset result.
  if (interpretation) return {text:'Not assessed', source:'Stanford API'};
  const recorded = String(record[`Resistance to ${drug}`] ?? '').trim();
  const hasMutations=MUTATION_GROUPS.some(g=>mutationValue(record,g)) || /[A-Z]\d+[A-Z]/i.test(String(record['All Mutations Combined']||''));
  return {text:recorded || (hasMutations?'Awaiting interpretation':'Not recorded'), source:recorded ? 'Recorded laboratory report' : hasMutations?'Recorded mutations; no drug interpretation':'No result'};
}
