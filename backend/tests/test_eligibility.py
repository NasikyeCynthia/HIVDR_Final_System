"""MoH DR-testing eligibility rules (see app/services/eligibility_service.py for sources)."""
import unittest
from datetime import date
from app.services.eligibility_service import assess, adherence_tier, parse_vl, vl_timeline

TODAY = date(2026, 11, 1)


def adult(**raw):
    base = {'Treatment Initiation Date': '01/01/2020', 'ART at sample collection(ART@VL@DR)': 'TDF-3TC-DTG',
            'Treatment Line at Sample collection': 'First Line', 'Age(yrs)': '35'}
    base.update(raw)
    return {'age': float(base['Age(yrs)']), 'regimen': base['ART at sample collection(ART@VL@DR)'], 'treatment_line': None}, base


def sessions(*pcts, start=date(2026, 5, 10)):
    return [{'id': i, 'session_date': date(start.year, start.month + i, start.day).isoformat(), 'adherence_pct': p}
            for i, p in enumerate(pcts)]


class EligibilityRules(unittest.TestCase):
    def test_adherence_tiers_follow_manual_table_1(self):
        self.assertEqual([adherence_tier(x) for x in (84.9, 85, 94.9, 95, 100, 105, 106)],
                         ['Poor', 'Fair', 'Fair', 'Good', 'Good', 'Good', 'Investigate (>105%)'])

    def test_threshold_is_1000_or_more_as_in_who(self):
        p, raw = adult(**{'VL Leading to DR': '999 Copies / mL', 'VL Test Date': '01/10/2026'})
        self.assertEqual(assess(p, raw, today=TODAY)['status'], 'suppressed')
        p, raw = adult(**{'VL Leading to DR': '1,000 Copies / mL', 'VL Test Date': '01/10/2026'})
        self.assertNotEqual(assess(p, raw, today=TODAY)['status'], 'suppressed')

    def test_vl_text_formats(self):
        self.assertEqual(parse_vl('19,900 Copies / mL'), (19900.0, ''))
        self.assertEqual(parse_vl('> 10,000,000 Copies / mL'), (10000000.0, '>'))
        self.assertEqual(parse_vl('<20'), (20.0, '<'))
        self.assertEqual(parse_vl('Target Not Detected'), (0.0, '<'))
        self.assertIsNone(parse_vl('Failed'))

    def test_first_nonsuppressed_after_suppressed_starts_iac(self):
        p, raw = adult(**{'vl_1_Prior_To_DR': '<20', 'VL_1_Prior_To_DR_TestDate': '01/10/2025',
                          'VL Leading to DR': '25,000', 'VL Test Date': '01/09/2026'})
        result = assess(p, raw, today=TODAY)
        self.assertEqual(result['status'], 'not_yet')
        self.assertIn('IAC', result['next_step'])

    def test_single_vl_without_history_asks_for_documentation_not_eligibility(self):
        p, raw = adult(**{'VL Leading to DR': '25,000', 'VL Test Date': '01/09/2026'})
        self.assertEqual(assess(p, raw, today=TODAY)['status'], 'needs_documentation')

    def test_two_nonsuppressed_with_three_good_iac_is_eligible(self):
        p, raw = adult(**{'vl_1_Prior_To_DR': '200,000', 'VL_1_Prior_To_DR_TestDate': '01/05/2026',
                          'VL Leading to DR': '30,000', 'VL Test Date': '15/08/2026'})
        result = assess(p, raw, sessions=sessions(96, 98, 100), today=TODAY)
        self.assertEqual(result['status'], 'eligible', result['criteria'])
        self.assertFalse(result['log_drop']['significant'])

    def test_iac_not_recorded_is_documentation_gap(self):
        p, raw = adult(**{'vl_1_Prior_To_DR': '200,000', 'VL_1_Prior_To_DR_TestDate': '01/05/2026',
                          'VL Leading to DR': '30,000', 'VL Test Date': '15/08/2026'})
        self.assertEqual(assess(p, raw, today=TODAY)['status'], 'needs_documentation')

    def test_poor_adherence_during_iac_blocks_referral(self):
        p, raw = adult(**{'vl_1_Prior_To_DR': '200,000', 'VL_1_Prior_To_DR_TestDate': '01/05/2026',
                          'VL Leading to DR': '30,000', 'VL Test Date': '15/08/2026'})
        result = assess(p, raw, sessions=sessions(96, 80, 97), today=TODAY)
        self.assertEqual(result['status'], 'not_yet')

    def test_repeat_vl_too_soon(self):
        p, raw = adult(**{'vl_1_Prior_To_DR': '200,000', 'VL_1_Prior_To_DR_TestDate': '01/07/2026',
                          'VL Leading to DR': '30,000', 'VL Test Date': '15/08/2026'})
        self.assertEqual(assess(p, raw, sessions=sessions(96, 97, 98, start=date(2026, 7, 5)), today=TODAY)['status'], 'not_yet')

    def test_less_than_six_months_on_art(self):
        p, raw = adult(**{'Treatment Initiation Date': '01/03/2026', 'vl_1_Prior_To_DR': '200,000',
                          'VL_1_Prior_To_DR_TestDate': '01/05/2026', 'VL Leading to DR': '30,000', 'VL Test Date': '15/08/2026'})
        self.assertEqual(assess(p, raw, sessions=sessions(96, 98, 100), today=TODAY)['status'], 'not_yet')

    def test_child_on_nnrti_first_line_needs_single_vl(self):
        p, raw = adult(**{'Age(yrs)': '8', 'ART at sample collection(ART@VL@DR)': 'ABC-3TC-EFV',
                          'VL Leading to DR': '5,000', 'VL Test Date': '01/10/2026'})
        result = assess(p, raw, today=TODAY)
        self.assertEqual(result['status'], 'eligible')
        self.assertIn('Child', result['pathway'])

    def test_child_on_dtg_follows_iac_pathway(self):
        p, raw = adult(**{'Age(yrs)': '8', 'ART at sample collection(ART@VL@DR)': 'ABC-3TC-DTG',
                          'VL Leading to DR': '5,000', 'VL Test Date': '01/10/2026'})
        self.assertNotEqual(assess(p, raw, today=TODAY)['status'], 'eligible')

    def test_duplicate_and_out_of_order_columns_are_ordered_by_date(self):
        raw = {'VL Leading to DR': '13,500', 'VL Test Date': '08/05/2025', 'vl_1_Prior_To_DR': '4,960',
               'VL_1_Prior_To_DR_TestDate': '30/10/2025', 'vl_2_Prior_To_DR': '13,500', 'VL_2_Prior_To_DR_TestDate': '08/05/2025'}
        timeline = vl_timeline(raw)
        self.assertEqual([o['copies'] for o in timeline], [13500, 4960])

    def test_already_referred_is_in_process(self):
        p, raw = adult(**{'VL Leading to DR': '25,000', 'VL Test Date': '01/09/2026'})
        self.assertEqual(assess(p, raw, {'referred_at': '2026-09-10'}, today=TODAY)['status'], 'in_process')


if __name__ == '__main__':
    unittest.main(verbosity=2)
