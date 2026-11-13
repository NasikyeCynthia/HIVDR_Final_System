import test from 'node:test';
import assert from 'node:assert/strict';
import {reviewStage,ACTION_LABELS} from './discussion.js';

test('approval is distinct from a generated draft',()=>{
  assert.equal(reviewStage({status:'Usable result',has_interpretation:true,suggested_action:'Switched'}).key,'ready');
  assert.equal(reviewStage({decision:'Switched'}).key,'approved');
  assert.equal(ACTION_LABELS.Substituted,'Substitute');
});
test('running and failed Stanford jobs are visible without inventing readiness',()=>{
  assert.equal(reviewStage({status:'Usable result',interpretation_status:'running'}).key,'processing');
  assert.equal(reviewStage({status:'Usable result',automation:{status:'failed'}}).key,'attention');
  assert.equal(reviewStage({status:'Usable result'}).key,'awaiting');
});
test('an unsuccessful lab result is not a recommendation candidate',()=>{
  assert.equal(reviewStage({status:'Unamplified',has_interpretation:false}).key,'laboratory');
});
