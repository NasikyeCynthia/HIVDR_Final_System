import test from 'node:test';
import assert from 'node:assert/strict';
import {EXPOSURES, DRUG_GROUPS, exposureValue, regimenDrugs, resistanceResult, MUTATION_GROUPS, RESISTANCE_FIELDS, mutationValue, sampleTreatment} from './resistance.js';

test('default view includes all requested exposures and drug groups',()=>{
  assert.equal(EXPOSURES.length,7);
  assert.deepEqual(DRUG_GROUPS.map(g=>g.drugs.length),[4,3,4,4]);
});
test('missing exposure stays distinct from no exposure',()=>{
  assert.equal(exposureValue(0),'No');
  assert.equal(exposureValue('0'),'No');
  assert.equal(exposureValue(false),'No');
  assert.equal(exposureValue(''),'Not recorded');
  assert.equal(exposureValue(null),'Not recorded');
  assert.equal(exposureValue('unknown'),'Unknown');
});
test('regimen highlights boosted drugs while keeping FTC and 3TC distinct',()=>{
  assert.deepEqual(regimenDrugs('TDF/FTC/LPV/r'),['TDF','FTC','LPV/r']);
  assert.deepEqual(regimenDrugs('ZDV-3TC-ATV/r'),['AZT','3TC','ATV/r']);
});
test('saved Stanford results take precedence without filling coverage gaps from old reports',()=>{
  const saved={analysis:{drugResistance:[{drugScores:[{drug:{displayAbbr:'3TC'},score:60,level:5,text:'High-Level Resistance'}]}]}};
  assert.equal(resistanceResult('3TC',saved,{'Resistance to 3TC':'Susceptible'}).level,5);
  assert.equal(resistanceResult('DTG',saved,{'Resistance to DTG':'Susceptible'}).text,'Not assessed');
});
test('recorded reports are labeled separately from missing results',()=>{
  assert.equal(resistanceResult('DTG',null,{'Resistance to DTG':'Susceptible'}).source,'Recorded laboratory report');
  assert.equal(resistanceResult('DTG',null,{}).text,'Not recorded');
});
test('original mutation columns are requested and displayed with report frequencies',()=>{
  for(const key of ['PI','INSTI','NRTI','NNRTI'])assert.ok(RESISTANCE_FIELDS.includes(key));
  assert.equal(mutationValue({INSTI:'E157Q(99.7%)'},MUTATION_GROUPS[1]),'E157Q(99.7%)');
  assert.equal(mutationValue({PI:',', 'PiMajor Mutations':'M46I'},MUTATION_GROUPS[0]),'M46I');
  assert.equal(mutationValue({PI:','},MUTATION_GROUPS[0]),'');
  assert.equal(resistanceResult('DTG',null,{INSTI:'E157Q(99.7%)'}).text,'Awaiting interpretation');
});
test('sample ART and treatment line are separate and prefer their dataset fields',()=>{
  assert.deepEqual(sampleTreatment({regimen:'old regimen',treatment_line:1},
    {'ART at sample collection(ART@VL@DR)':'AZT+3TC+DTG','Treatment Line at Sample collection':'Second Line'}),
    {regimen:'AZT+3TC+DTG',line:'Second Line'});
});
