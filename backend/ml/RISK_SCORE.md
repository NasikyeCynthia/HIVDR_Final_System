# Risk score and decision support — derivation and validation

## 1. Risk of drug resistance (points score) — `app/services/risk_service.py`

**Purpose.** Prioritise non-suppressed patients. It does not decide DR-test eligibility
(MoH/WHO criteria in `eligibility_service.py` do) and does not replace the clinician.

**Data.** CPHL HIVDR extract, 9,934 records with an amplified result and a complete
12-drug RT/IN panel (BIC, CAB, DTG, RAL, 3TC, ABC, AZT, TDF, DOR, EFV, ETR, NVP).
Outcome: any low-level-or-higher resistance (Stanford score ≥15). Prevalence 59%.

**Method.** Logistic regression on candidate factors chosen from the literature, with a
facility-grouped split (75% derivation / 25% held-out facilities). Coefficients converted to
integer points (1 point ≈ 0.35 log-odds). Reproduce with `ml/analysis/derive_score.py`
and `score_eval.py` (`HIVDR_DB=path/to/surveillance.sqlite3`).

| Factor | Odds ratio | Points |
|---|---|---|
| Second- or third-line regimen | 2.6–3.0 | 3 |
| NNRTI-based regimen (EFV/NVP) | 2.7 | 3 |
| Child under 10 | 3.1 | 3 |
| Adolescent 10–19 | 1.5 | 1 |
| On ART ≥5 years | 1.4 | 1 |
| ≥3 consecutive VL ≥1000 (≥2 before the current) | 1.5 | 1 |
| Previously exposed to both AZT and ABC | 1.3 | 1 |

Guideline modifiers (not validated — adherence is not in the extract):
still ≥1000 after 3 good IAC sessions (+2, MoH Job Aid slide 161); <1-log drop after IAC
(+1, Participants' Manual §2.4); poor adherence on NNRTI (+1, Manual §4).

**Viral load.** Only patients with VL ≥1000 are scored — that is the entry gate, not a point.
Within VL ≥1000, resistance was found in 64% at 1,000–9,999, 59% at 10,000–99,999 and 54% at
≥100,000 copies/mL. A point for the lower band was tested and removed: it added almost nothing
(AUROC 0.714 vs 0.710) and was counter-intuitive for clinicians.

**Performance.** AUROC 0.710 on held-out facilities (random forest 0.721; full logistic
regression 0.717); 0.696 on all 9,805 records as implemented (`validate_impl.py`).

| Band | Points | Share with resistance |
|---|---|---|
| Low | 0–2 | 41% |
| Moderate | 3–4 | 67% |
| High (flagged) | ≥5 | 78% |

**Caveats.** Derived among patients already referred and tested, so it ranks risk *within*
that group. Re-derive when adherence and IAC
data accumulate.

## 2. Suggested committee action — `app/services/suggestion_service.py`

Inputs: Stanford levels for the drugs in the current regimen. Rules: NNRTI anchor with
≥ low-level resistance → Switch (WHO 2021); INSTI/PI anchor ≥ intermediate → Switch
(third line guided by resistance, MoH); anchor active and both NRTIs ≥ intermediate →
Switch (alternative Substitute); anchor active and one NRTI compromised → Maintain
(alternative Substitute); no meaningful resistance → Maintain with adherence support.

Agreement with 11,105 past Ugandan committee decisions (`agreement.py`): 78.5% exact,
82.7% counting the alternative. The clinician must approve; a different decision requires
a written reason, and whether the suggestion was followed is stored.
