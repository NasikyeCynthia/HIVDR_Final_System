# HIVDR panel model â€” research baseline

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

## Additional frozen-model audit

`validate_model.py` reproduces the original cohort and facility splits, verifies the exact CSV hash and original held-out metrics, and evaluates the installed artifact without refitting or changing its cutoff. It exports aggregate results only; patient rows and facility names are not exported.

```powershell
python ml/validate_model.py "C:\path\to\original.csv" --output ml/artifacts/validation.json --bootstrap 500
```

The audit adds facility-cluster bootstrap 95% intervals, probability calibration bins, training-prevalence / majority-class baselines, precision, negative predictive value, and descriptive age, sex, treatment-line and regimen subgroup checks. Subgroup metrics are suppressed below 30 records or fewer than 10 positive or negative outcomes. Missing-age and other/missing-regimen groups remain visible.

Intervals describe uncertainty in the fixed model on this selected test population; they do not include model-development uncertainty. Subgroups overlap and do not establish fairness. Reusing the test set for this descriptive audit does not create a new external validation. The validation set was used for model selection, calibration and cutoff choice; future candidate models need a predeclared development protocol and a new untouched evaluation before promotion.

The backend exposes this audit only when its model and dataset fingerprints match the installed artifact. The live model and training artifact are unchanged by the audit.

Methods: https://scikit-learn.org/stable/modules/calibration.html and https://scikit-learn.org/stable/modules/model_evaluation.html

### Audit findings (frozen model)

The 500-replicate facility-cluster audit reproduced all original test metrics. AUROC 95% interval: 0.695–0.746; sensitivity 60.8–70.5%; specificity 62.2–74.1%. Brier score 0.203 compares with 0.238 for a constant training-prevalence prediction. Precision is 76.5% and negative predictive value 55.9% in this referred/tested cohort.

Performance differs substantially by subgroup at the unchanged 0.64 research cutoff. TDF-3TC-DTG sensitivity is 39.5% (221/559 positives detected), while all 87 third-line test records are flagged, yielding 0% specificity in that group. These descriptive results reinforce that this cutoff must not serve as a clinical gatekeeper. No subgroup-specific thresholds were fitted using this test set.

The next model-development phase should define the intended clinical use and acceptable trade-offs with clinicians, then use development data for grouped model/calibration/threshold selection and a new untouched external or temporal evaluation. The present audit does not justify claiming improved model accuracy.

## Retraining experiment

See `RETRAINING.md` and `experiments/history-v2/metrics.json` for the newer history-based research candidate. It improved legacy-test AUROC to 0.744 and sensitivity to 74.1%, with specificity reduced to 62.5%. This candidate is not deployed and has not received fresh independent validation. The active model and all v1 results above remain unchanged.
