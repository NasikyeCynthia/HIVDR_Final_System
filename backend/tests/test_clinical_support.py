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
    """The project's original points algorithm (prototype 2.1)."""
    def test_viral_load_1000_alone_is_high(self):
        r = score({'viral_load': 1500, 'adherence': None, 'treatment_line': None})
        self.assertEqual((r['known_total'], r['category'], r['flagged']), (60, 'High', True))

    def test_bands_when_complete(self):
        self.assertEqual(score({'viral_load': 40, 'adherence': 100, 'treatment_line': 1})['category'], 'Low')
        self.assertEqual(score({'viral_load': 400, 'adherence': 100, 'treatment_line': 1})['category'], 'Intermediate')
        self.assertEqual(score({'viral_load': 400, 'adherence': 90, 'treatment_line': 1})['total'], 60)

    def test_incomplete_below_60(self):
        r = score({'viral_load': 400, 'adherence': None, 'treatment_line': 1})
        self.assertEqual(r['category'], 'Incomplete')
        self.assertIn('Adherence (%)', r['missing_inputs'])

    def test_reason_includes_eligibility(self):
        r = score({'viral_load': 5000, 'adherence': 96, 'treatment_line': 2}, eligibility={'label': 'Not yet eligible', 'next_step': 'Start IAC.'})
        self.assertIn('DR test: Not yet eligible', r['reason'])

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
