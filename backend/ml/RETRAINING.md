# HIVDR retraining results — 14 November 2026

A new research candidate improved retrospective performance. It has not replaced the deployed model. No raw patient rows or identifiers are included in these experiment outputs.

## What was trained

Two development experiments compared seven fixed configurations each: logistic regression, three random-forest configurations, extra trees, and two gradient-boosting configurations. Each used four facility-grouped cross-validation folds with preprocessing fitted separately in each training fold.

The first experiment retained the original inputs and selected the original random-forest configuration again; discrimination did not improve. The second added pre-sample history features and selected a 300-tree random forest, maximum depth 12, minimum leaf size 8, balanced class weights.

Additional inputs: duration on the current regimen, dated prior VL maximum/mean, VL change, gap since previous VL, consecutive non-suppressed observations, ongoing non-suppression duration, and current drug-component indicators. These indicators describe the current regimen, not historical drug exposure. Future observations, mutations, resistance results and committee decisions are excluded.

The target remains any low-level-or-greater resistance across the same fully observed 12-drug RT/IN panel. PI-only resistance is excluded; potential low-level resistance remains below the positive target definition.

## Evaluation protocol

The original dataset hash, cohort and facility splits were reproduced. There were 6,620 fitting records, 518 calibration records, 1,057 cutoff-selection records and 1,739 legacy-test records. These partitions have disjoint facilities. Candidate configuration was chosen by mean training-fold AUROC. Logistic calibration used only calibration facilities; the research cutoff (0.62) maximised balanced accuracy on separate cutoff facilities. Neither was selected on the legacy test.

The legacy test was previously examined, including during the first retraining experiment. Feature-family exploration is therefore iterative, and this comparison is exploratory internal evidence, not a fresh independent validation. No new clinical records were added.

## Comparison on the same 1,739 legacy records

| Measure | Deployed model | History candidate |
| --- | ---: | ---: |
| AUROC | 0.721 | 0.744 |
| Average precision | 0.788 | 0.803 |
| Accuracy | 66.8% | 69.6% |
| Balanced accuracy | 67.0% | 68.3% |
| Sensitivity | 66.0% | 74.1% |
| Specificity | 68.0% | 62.5% |
| Precision | 76.5% | 75.7% |
| Negative predictive value | 55.9% | 60.4% |
| Brier score (lower is better) | 0.203 | 0.196 |

The candidate detected 789/1,065 positive cases, versus 703 previously: 86 fewer missed cases. It incorrectly flagged 253/674 negative cases, versus 216 previously: 37 additional false positives. Improved sensitivity comes with lower specificity at the selected cutoffs.

Mean development-fold AUROC rose from 0.714 for the original configuration with original inputs to 0.729 for the selected history candidate. These are development comparisons after selection, not unbiased final validation estimates.

A paired 500-replicate facility-cluster bootstrap estimated the legacy-test AUROC difference as +0.023, with a descriptive 95% interval of +0.011 to +0.036. This conditions on the fitted models and the reused cohort; it does not account for feature/model-selection uncertainty.

## Subgroups and remaining limitations

TDF-3TC-DTG sensitivity improved from 39.5% to 53.8%, while specificity fell from 86.6% to 80.3%. Third-line specificity remains 0%: all 87 third-line test records were flagged. Overall improvement does not make the model suitable as a sole testing gatekeeper.

The population remains selected, referred and tested patients; generalisation to all clinic attendees is unestablished. Stable patient identifiers were unavailable, so cross-facility transfers cannot be excluded. No prospective validation, independent external cohort or clinician-approved clinical cutoff is available.

## Files and reproducibility

- `backend/ml/retrain_model.py`: candidate grid, grouped training, calibration, cutoff selection, legacy comparison and portable JSON export.
- `backend/ml/history_features.py`: additional pre-sample predictors; the active application extractor is unchanged.
- `backend/ml/experiments/history-v2/model.json`: exported candidate weights and preprocessing.
- `backend/ml/experiments/history-v2/metrics.json`: exact aggregate metrics, subgroup checks and environment versions.
- `backend/ml/experiments/original-features/`: original-input comparison results.
- `backend/ml/requirements-retraining.txt`: exact research package versions.
- `backend/tests/test_retraining.py` and `test_history_features.py`: partition, preprocessing, future-data exclusion and portable-export checks.

Use an isolated research environment with `pip install -r ml/requirements-retraining.txt`. From `backend`:

```powershell
python ml/retrain_model.py "C:\path\to\original.csv" --features original --output "C:\research\original-run"
python ml/retrain_model.py "C:\path\to\original.csv" --features history --output "C:\research\history-run"
```

Output directories must be new/empty. The script refuses the wrong dataset hash and refuses to overwrite the active model. Only aggregate results and model parameters are exported. Portable candidate inference agreed with the fitted estimator within 1.2e-15 on all 1,739 legacy records.

## Deployment status

The app continues to use `backend/ml/artifacts/model.json` (v1). The candidate is not a drop-in replacement: it requires its history extractor and matching feature order, runtime integration, recalculation of cached predictions, and updated model evaluation metadata. Do not copy its JSON over the active artifact.

Before promotion, evaluate the frozen candidate on a genuinely independent later/external cohort and agree the intended use and sensitivity/specificity trade-off with clinical reviewers. The application points score, Stanford API and treatment recommendations were not changed by this retraining.

Method references: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html and https://scikit-learn.org/stable/modules/calibration.html
