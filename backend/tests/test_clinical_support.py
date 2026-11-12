"""Risk score, decision suggestion, psychosocial recommendations and role permissions."""
import unittest
from datetime import date
from app.core.permissions import ACTIONS, can, for_user
from app.services.risk_service import score
from app.services.suggestion_service import suggest
from app.services.psychosocial_service import recommendations
from app.services.eligibility_service import assess

def patient(**kw):
    raw = {'Treatment Initiation Date': '01/01/2015', 'ART at sample collection(ART@VL@DR)': 'TDF-3TC-DTG',
           'Treatment Line at Sample collection': 'First Line', 'Age(yrs)': '35',
           'vl_1_Prior_To_DR': '20,000', 'VL_1_Prior_To_DR_TestDate': '01/05/2026', 'VL Leading to DR': '8,000', 'VL Test Date': '15/08/2026'}
    raw.update(kw)
    p = {'age': float(raw['Age(yrs)']), 'regimen': raw['ART at sample collection(ART@VL@DR)'], 'treatment_line': None, 'source': 'synthetic'}
    return p, raw

class RiskScore(unittest.TestCase):
    def test_points_and_bands(self):
        p, raw = patient()
        result = score(p, raw, [], assess(p, raw, today=date(2026, 11, 1)))
        named = {f['name']: f['points'] for f in result['factors']}
        self.assertEqual(named['On ART 5 years or more'], 1)
        self.assertEqual(named['Less than 1-log drop after IAC'], 1)  # 20,000 → 8,000 is 0.4 log
        self.assertEqual((result['total'], result['category']), (2, 'Low'))

    def test_second_line_child_is_high_and_flagged(self):
        p, raw = patient(**{'Age(yrs)': '8', 'Treatment Line at Sample collection': 'Second Line', 'ART at sample collection(ART@VL@DR)': 'ABC-3TC-LPV/r'})
        p['treatment_line'] = 2
        result = score(p, raw, [], assess(p, raw, today=date(2026, 11, 1)))
        self.assertEqual(result['category'], 'High')
        self.assertTrue(result['flagged'])
        self.assertIn('DR test', result['reason'])

    def test_good_adherence_with_persistent_viraemia_adds_guideline_points(self):
        p, raw = patient()
        sessions = [{'session_date': f'2026-0{m}-10', 'adherence_pct': 98} for m in (5, 6, 7)]
        result = score(p, raw, sessions, assess(p, raw, sessions=sessions, today=date(2026, 11, 1)))
        self.assertEqual(result['clinical_points'], 3)  # +2 persistent despite good IAC, +1 <1-log drop

    def test_suppressed_patient_is_not_scored(self):
        p, raw = patient(**{'VL Leading to DR': '<20'})
        self.assertEqual(score(p, raw, [], {})['category'], 'Not applicable')

class Suggestion(unittest.TestCase):
    def rec(self, regimen, **levels):
        raw = {'Resistance to ' + k.replace('_', '/'): v for k, v in levels.items()}
        return suggest({'regimen': regimen}, {'status': 'Usable result'}, raw)

    def test_no_resistance_maintain(self):
        s = self.rec('TDF-3TC-DTG', DTG='Susceptible', TDF='Susceptible', **{'3TC': 'Susceptible'})
        self.assertEqual(s['action'], 'Maintained')

    def test_dtg_high_level_switch(self):
        s = self.rec('TDF-3TC-DTG', DTG='High-Level Resistance', TDF='Susceptible', **{'3TC': 'High-Level Resistance'})
        self.assertEqual(s['action'], 'Switched')

    def test_nnrti_resistance_switch(self):
        s = self.rec('TDF-3TC-EFV', EFV='High-Level Resistance', TDF='Susceptible', **{'3TC': 'Susceptible'})
        self.assertEqual(s['action'], 'Switched')

    def test_single_nrti_on_dtg_maintain_with_substitute_alternative(self):
        s = self.rec('TDF-3TC-DTG', DTG='Susceptible', TDF='Susceptible', **{'3TC': 'High-Level Resistance'})
        self.assertEqual((s['action'], s['alternative']), ('Maintained', 'Substituted'))

    def test_no_result_no_suggestion(self):
        self.assertIsNone(suggest({'regimen': 'TDF-3TC-DTG'}, {'status': 'Pending'}, {}))

class Psychosocial(unittest.TestCase):
    def test_denial_recommends_counselling(self):
        recs = recommendations({'assessed': True, 'factors': ['Denial/coping with results']}, age=16)
        self.assertIn('Counselling', recs[0]['action'])
        self.assertTrue(any('HEADSS' in r['action'] for r in recs))

class Permissions(unittest.TestCase):
    def test_role_matrix(self):
        nurse, lab, clin = {'role': 'nurse'}, {'role': 'lab'}, {'role': 'clinician'}
        self.assertTrue(can(nurse, 'edit_patient_record') and can(nurse, 'implement_decision'))
        self.assertFalse(can(clin, 'implement_decision') or can(clin, 'edit_patient_record'))
        self.assertFalse(can(nurse, 'review_and_decide') or can(lab, 'review_and_decide'))
        self.assertEqual(for_user(lab), ['interpret_resistance', 'record_lab', 'refer_on_clinical_indication', 'request_dr_test'])
        self.assertEqual(for_user(clin), ['discuss', 'review_and_decide'])
        self.assertFalse(can(nurse, 'request_dr_test'))
        self.assertTrue(all(roles for roles in ACTIONS.values()))

if __name__ == '__main__':
    unittest.main()
