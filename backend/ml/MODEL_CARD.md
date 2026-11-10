# HIVDR panel model — research baseline

The included model predicts **any documented low-level-or-greater resistance across a fully observed 12-drug RT/IN panel** among referred and tested patients. It does not diagnose resistance, determine treatment, or establish performance in untested low-risk patients.

## Data and outcome

- Original input: 39,711 records and 119 columns; no synthetic rows used.
- Eligible cohort: 9,934 amplified records with valid results for all 12 panel drugs.
- Panel: BIC, CAB, DTG, RAL, 3TC, ABC, AZT, TDF, DOR, EFV, ETR and NVP.
- Positive: at least one Low-Level, Intermediate or High-Level Resistance result in that panel.
- Negative: every panel result is Susceptible or Potential Low-Level Resistance.
- Missing outcomes and unsuccessful tests are excluded rather than labelled negative.
- PI-only resistance is outside this target.

## Inputs

Viral load leading to DRT, age, treatment line, regimen, sex, ART duration derived at the index sample, and dated prior viral-load observations. Only prior observations dated on or before the sample are included. Missing non-critical numerical inputs use training-set medians with missingness indicators; categorical levels are learned from training records.

There is no adherence column in the original data, so adherence is not an ML input. Mutation calls, resistance results, resistance indicators, committee decisions, post-decision viral loads and psychosocial assessments are excluded from the predictors. Facility is used for splitting, not as a model feature.

## Evaluation

Facilities are kept disjoint across the partitions. Stable person identifiers were not available; this reduces repeated-record leakage within hospitals but cannot exclude transfers across facilities.

| Partition | Records | Facilities |
| --- | ---: | ---: |
| Training | 6,620 | 755 |
| Validation | 1,575 | 189 |
| Held-out test | 1,739 | 236 |

| Candidate | Validation AUROC |
| --- | ---: |
| Logistic Regression | 0.681 |
| Random Forest | 0.700 |

Random Forest was selected using validation AUROC. Probability calibration and the research threshold were fitted on validation data. The held-out test was not used for model selection, calibration or threshold choice.

| Held-out measure | Result |
| --- | ---: |
| AUROC | 0.721 |
| Average precision | 0.788 |
| Accuracy | 66.8% |
| Sensitivity | 66.0% |
| Specificity | 68.0% |
| Balanced accuracy | 67.0% |
| Brier score | 0.203 |
| Validation-selected threshold | 0.64 |

Confusion matrix at that threshold: 703 true positives, 458 true negatives, 216 false positives and 362 false negatives. This sensitivity is insufficient to use the model as the sole gatekeeper for clinical screening or referral.

## Runtime and reproducibility

`artifacts/model.json` contains the forest, preprocessing and calibration parameters. Runtime inference uses Python's standard library, so installing scikit-learn in the running backend is unnecessary. Exported inference was compared with the fitted sklearn model on all held-out cases and agreed within 1e-8 probability.

To retrain in a separate research environment, install `ml/requirements-training.txt`, then from `backend` run:

```powershell
python ml/train_model.py "C:\path\to\original.csv"
```

`artifacts/metrics.json` contains exact metrics, cohort counts, dataset hash and model metadata. No training rows or patient identifiers are embedded in the artifact package. Synthetic demonstration records are not scored in the live model endpoint.

## Limits

This is retrospective evaluation on a selected referred/tested cohort. Prospective external validation, clinical operating thresholds and local governance remain necessary before clinical use. The displayed probability remains separate from the project's rules-based risk score and the clinician's decision. Global feature importance is not an explanation of an individual patient's prediction.

## Method references

- Stanford HIVdb interpretation categories: https://hivdb.stanford.edu/page/release-notes/
- Scikit-learn leakage prevention: https://scikit-learn.org/stable/common_pitfalls.html
- Grouped evaluation: https://scikit-learn.org/stable/modules/cross_validation.html
