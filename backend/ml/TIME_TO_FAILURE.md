# Time to treatment failure — option B (descriptive) and the early-failure model test

## What is shown in the system
The dashboard card **Time to treatment failure** shows how many months patients stayed on their
current regimen before the first viral load ≥1000 copies/mL, by treatment line and anchor drug
(median, 25th–75th percentile, share failing within 12 months).

- Regimen start = `ART@VL@DR start date`; failure = first VL ≥1000 at least 1 month after that start
  (an earlier high VL is failure carried over from the previous regimen). Computed per patient in
  `eligibility_service.py` (`time_to_failure`), stored in `episodes.ttf`.
- To avoid follow-up bias the card uses regimens started from 2019 and at least 36 months before the
  latest data, and failures within 36 months, so every patient had the same window to be seen.
- **Limitation:** the CPHL extract contains only patients who failed. The card describes timing
  *among patients who failed*; it does not give anyone's chance of failing.

## Early-failure model (tested, not deployed)
Question: among patients who failed, can routine data tell who fails within 12 months of starting a
regimen? Cohort 6,139 patients (45% early), 829 facilities, facility-grouped 5-fold cross-validation
(`ml/analysis/early_failure_model.py`).

| Model | AUROC (mean, range across folds) |
| --- | --- |
| Logistic regression | 0.56 (0.53–0.59) |
| Random forest | 0.59 (0.57–0.61) |
| Gradient boosting | 0.58 (0.56–0.60) |

A first run reached 0.66, but almost all of that came from the regimen start year, an artefact of who
entered the DR database (the programme scaled up from 2019). With that removed, the model is barely
better than chance, so it is **not used** for individual patients.

## Option A (to do when data arrive)
With viral loads for all patients on ART, including those who stay suppressed (CPHL VL database or
UgandaEMR), fit a survival model (Cox or survival forest) for the chance of failing within 6, 12 and
24 months of a regimen start, validated across facilities and over time. The system's own records
(every registered patient's viral loads) will also build this dataset.
