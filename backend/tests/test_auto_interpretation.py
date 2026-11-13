import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core import bootstrap,database
from app.core.errors import DomainError
from app.services.auto_interpretation import enqueue,process_pending,state
from app.services.decision_service import approve_decision
from app.services.suggestion_service import suggest


class AutomaticInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=bootstrap.ROOT,bootstrap.DB,database.DB
        bootstrap.ROOT=Path(self.temp.name);(bootstrap.ROOT/'data').mkdir()
        bootstrap.DB=database.DB=bootstrap.ROOT/'data/test.sqlite3'
        bootstrap.initialize()
        with database.connect() as con:
            self.lab=dict(con.execute("SELECT * FROM users WHERE role='lab'").fetchone())
            self.clinician=dict(con.execute("SELECT * FROM users WHERE role='clinician'").fetchone())
            con.execute("UPDATE patients SET regimen='TDF-3TC-DTG',adherence=96,psychosocial_json=?,source_overrides_json=? WHERE id=1",(json.dumps({'assessed':True,'factors':[]}),json.dumps({'NRTI':'M184V','INSTI':'R263K'})))
            con.execute("UPDATE episodes SET status='Usable result',decision=NULL,reviewed_at=NULL,mutations='RT:M184V IN:R263K',sequence='',interpretation_json=NULL WHERE patient_id=1")

    def tearDown(self):
        bootstrap.ROOT,bootstrap.DB,database.DB=self.old
        self.temp.cleanup()

    def rows(self,con):
        return dict(con.execute('SELECT * FROM patients WHERE id=1').fetchone()),dict(con.execute('SELECT * FROM episodes WHERE patient_id=1').fetchone())

    def result(self):
        return {'provider':'Stanford HIVdb Sierra','version':{'text':'fixture','publishDate':'2026-01-01'},
                'analysis':{'validationResults':[],'drugResistance':[{'gene':{'name':'RT'},'drugScores':[
                    {'drug':{'displayAbbr':d},'score':0,'level':1,'text':'Susceptible'} for d in ('TDF','3TC','DTG')]}]}}

    def queue(self):
        with database.connect() as con:return enqueue(con,self.lab,1)

    def test_success_creates_draft_but_never_approves(self):
        job=self.queue()
        with patch('app.services.stanford_service.analyze',return_value=self.result()) as analysis:process_pending(1)
        analysis.assert_called_once_with('mutations','RT:M184V IN:R263K')
        with database.connect() as con:
            p,e=self.rows(con)
            self.assertIsNone(e['decision']);self.assertIsNone(e['implemented_at'])
            self.assertEqual(json.loads(e['suggestion_json'])['action'],'Maintained')
            self.assertEqual(json.loads(e['suggestion_json'])['recommendation_source'],'Local committee decision-support rules')
            self.assertEqual(state(con,e)['status'],'ready')
            self.assertEqual(con.execute('SELECT status FROM interpretation_jobs WHERE id=?',(job,)).fetchone()[0],'completed')

    def test_failure_retains_lab_result_and_blocks_approval(self):
        self.queue()
        with patch('app.services.stanford_service.analyze',side_effect=DomainError('Stanford unavailable',502)):process_pending(1)
        with database.connect() as con:
            p,e=self.rows(con)
            self.assertEqual(e['status'],'Usable result');self.assertIsNone(e['interpretation_json'])
            self.assertEqual(state(con,e)['status'],'failed')
            with self.assertRaises(DomainError):approve_decision(con,self.clinician,p,e,{'decision':'Maintained','recommended_regimen':p['regimen'],'decision_notes':'Clinical review completed.'})

    def test_changed_evidence_discards_inflight_response(self):
        self.queue()
        def changed(*args):
            with database.connect() as con:con.execute('UPDATE episodes SET version=version+1 WHERE patient_id=1')
            return self.result()
        with patch('app.services.stanford_service.analyze',side_effect=changed):process_pending(1)
        with database.connect() as con:
            _,e=self.rows(con);self.assertIsNone(e['interpretation_json'])
            self.assertEqual(con.execute('SELECT status FROM interpretation_jobs').fetchone()[0],'superseded')

    def test_missing_input_does_not_call_api_or_invent_susceptibility(self):
        with database.connect() as con:
            con.execute("UPDATE patients SET source_overrides_json='{}' WHERE id=1")
            con.execute("UPDATE episodes SET mutations='none' WHERE patient_id=1")
        self.queue()
        with patch('app.services.stanford_service.analyze') as analysis:process_pending(1)
        analysis.assert_not_called()
        with database.connect() as con:
            _,e=self.rows(con);self.assertEqual(state(con,e)['status'],'needs_input')

    def test_duplicate_queue_is_idempotent_and_retry_after_failure_is_possible(self):
        first=self.queue();self.assertEqual(self.queue(),first)
        with patch('app.services.stanford_service.analyze',side_effect=TimeoutError):process_pending(1)
        second=self.queue();self.assertNotEqual(first,second)
        with patch('app.services.stanford_service.analyze',return_value=self.result()):process_pending(1)
        with database.connect() as con:
            _,e=self.rows(con);self.assertEqual(state(con,e)['status'],'ready')

    def test_clinician_acknowledges_current_evidence_and_approval_is_audited(self):
        self.queue()
        with patch('app.services.stanford_service.analyze',return_value=self.result()):process_pending(1)
        with database.connect() as con:
            p,e=self.rows(con)
            body={'decision':'Maintained','decision_notes':'Reviewed resistance and patient clinical history.','recommended_regimen':p['regimen'],
                  'expected_version':e['version'],'expected_data_version':p['data_version'],'evidence_reviewed':True}
            with self.assertRaises(DomainError):approve_decision(con,self.lab,p,e,body)
            with self.assertRaises(DomainError):approve_decision(con,self.clinician,p,e,{**body,'expected_version':e['version']-1})
            with self.assertRaises(DomainError):approve_decision(con,self.clinician,p,e,{**body,'evidence_reviewed':False})
            approve_decision(con,self.clinician,p,e,body)
            self.assertEqual(con.execute('SELECT decision FROM episodes WHERE patient_id=1').fetchone()[0],'Maintained')
            self.assertEqual(state(con,self.rows(con)[1])['status'],'approved')
            self.assertEqual(con.execute("SELECT count(*) FROM audit WHERE action='clinical decision approved'").fetchone()[0],1)

    def test_partial_coverage_and_multi_anchor_regimens_do_not_get_automatic_actions(self):
        self.assertIsNone(suggest({'regimen':'TDF-3TC-DTG'},{'status':'Usable result'}, {'Resistance to DTG':'Susceptible'})['action'])
        self.assertIsNone(suggest({'regimen':'DTG-DRV/r'},{'status':'Usable result'}, {'Resistance to DTG':'Susceptible','Resistance to DRV/r':'Susceptible'})['action'])
