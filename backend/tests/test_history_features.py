"""Ensure new predictors use pre-sample information only."""
import unittest
from ml.history_features import extract

class HistoryFeatureTests(unittest.TestCase):
    def raw(self):
        return {'Sample collection Date':'01/06/2026','ART@VL@DR start date':'01/06/2025',
                'VL Leading to DR':'5000','ART at sample collection(ART@VL@DR)':'TDF+3TC+DTG',
                'vl_1_Prior_To_DR':'2000','VL_1_Prior_To_DR_TestDate':'01/05/2026',
                'vl_2_Prior_To_DR':'100','VL_2_Prior_To_DR_TestDate':'01/04/2026'}

    def test_future_observations_and_outcomes_do_not_affect_features(self):
        raw=self.raw();before=extract(raw)
        raw.update({'vl_3_Prior_To_DR':'999999','VL_3_Prior_To_DR_TestDate':'01/07/2026',
                    'Resistance to DTG':'High-Level Resistance','PI':'M46I','Decision':'Switched',
                    'VL 6 Months Post Decision':'99999'})
        self.assertEqual(before,extract(raw))

    def test_dated_history_and_drug_components(self):
        f=extract(self.raw())
        self.assertEqual(f['on_DTG'],1);self.assertEqual(f['on_AZT'],0)
        self.assertEqual(f['consecutive_prior_nonsuppressed'],1)
        self.assertEqual(f['prior_nonsuppressed_fraction'],.5)
        self.assertAlmostEqual(f['current_regimen_years'],365/365.25)

    def test_future_regimen_start_and_undated_history_are_missing(self):
        raw=self.raw();raw['ART@VL@DR start date']='01/07/2026'
        raw['VL_1_Prior_To_DR_TestDate']='';raw['VL_2_Prior_To_DR_TestDate']=''
        f=extract(raw)
        self.assertIsNone(f['current_regimen_years']);self.assertIsNone(f['prior_log_mean'])
        self.assertIsNone(f['consecutive_prior_nonsuppressed'])

    def test_duplicate_observations_do_not_inflate_streak(self):
        raw=self.raw();raw.update({'vl_3_Prior_To_DR':'2000','VL_3_Prior_To_DR_TestDate':'01/05/2026'})
        self.assertEqual(extract(raw)['consecutive_prior_nonsuppressed'],1)

    def test_missing_regimen_is_not_assumed_unexposed(self):
        f=extract({})
        self.assertIsNone(f['on_DTG'])

if __name__=='__main__':unittest.main()
