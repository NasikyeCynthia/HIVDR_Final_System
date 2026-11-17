# HIVDR model-family comparison — 17 November 2026

**The random-forest configuration ranked first on development cross-validation; CatBoost was very close. The active application model was not replaced.**

All 12 model families completed four facility-grouped training folds. This is exploratory internal research with one fixed configuration per family, not proof that one algorithm is universally best.

## Main comparison

Rows are ranked by mean training-only cross-validation AUROC. The previously examined legacy cohort was not used to rank models or select their cutoffs.

| Model | Mean CV AUROC | Fold SD | Legacy AUROC | Sensitivity | Specificity | Accuracy | Cutoff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Random forest (refit control) | 0.7300 | 0.0167 | 0.7438 | 70.2% | 66.9% | 68.9% | 65% |
| CatBoost | 0.7294 | 0.0203 | 0.7455 | 68.9% | 67.2% | 68.3% | 64% |
| Gradient boosting | 0.7282 | 0.0170 | 0.7465 | 81.9% | 52.7% | 70.6% | 53% |
| LightGBM | 0.7272 | 0.0216 | 0.7408 | 68.3% | 68.0% | 68.1% | 64% |
| XGBoost | 0.7269 | 0.0205 | 0.7426 | 71.1% | 65.3% | 68.8% | 62% |
| Histogram gradient boosting | 0.7267 | 0.0207 | 0.7469 | 78.4% | 56.5% | 69.9% | 57% |
| Neural network (MLP) | 0.7232 | 0.0216 | 0.7317 | 76.3% | 59.9% | 70.0% | 59% |
| SVM (RBF) | 0.7200 | 0.0173 | 0.7350 | 73.4% | 62.9% | 69.4% | 59% |
| Logistic regression | 0.7180 | 0.0180 | 0.7366 | 77.2% | 60.8% | 70.8% | 57% |
| AdaBoost | 0.7101 | 0.0171 | 0.7208 | 77.2% | 59.2% | 70.2% | 54% |
| Nearest neighbours | 0.7081 | 0.0112 | 0.7153 | 63.7% | 70.5% | 66.3% | 66% |
| Gaussian naive Bayes | 0.6890 | 0.0135 | 0.6869 | 75.7% | 56.7% | 68.3% | 56% |

The existing deployed model is a frozen artifact, whereas the random-forest row above is a new fit with the same hyperparameters and the comparison environment/calibration protocol. Its cutoff is 65%; the deployed model remains at 62%. Do not interpret this row as a change to the deployed model.

The unchanged deployed model reproduced AUROC **0.7443**, sensitivity **74.1%**, specificity **62.5%**, and accuracy **69.6%** on the same legacy records.

## What the results mean

- Random forest mean CV AUROC was 0.7300; CatBoost was 0.7294. The difference is only 0.0006, so these results do not demonstrate a meaningful advantage for either family.
- Histogram gradient boosting had the largest legacy-test AUROC (0.7469), versus 0.7443 for the actual deployed forest. This is a small difference on reused data; that legacy result was not the model-selection criterion.
- Standard gradient boosting had higher legacy sensitivity (81.9%) but lower specificity (52.7%). It detects more positives while flagging more negatives; higher sensitivity alone does not establish a better model.
- Logistic regression had the largest accuracy in this run (70.8%), but a lower mean CV AUROC (0.7180). Accuracy alone is not a sufficient selection criterion.
- The neural network, SVM, nearest neighbours and naive Bayes did not improve development ranking over the forest under these fixed settings.
- No new model was deployed. More hyperparameter tuning could change the ranking, but further development needs grouped validation and an independent later/external evaluation before clinical conclusions.

## Protocol

The same 9,934-record complete-panel cohort and original top-level facility partitions were reproduced: 6,620 training, 518 calibration, 1,057 cutoff-selection and 1,739 legacy-test records. All families used the same history-v2 numeric and one-hot categorical representation. Preprocessing was learned separately inside each CV training fold.

Scikit-learn 1.6.1 was used in an isolated Python 3.13 environment because the earlier Python 3.14 research installation had Windows binary-load failures. All 12 model families loaded and trained successfully in the isolated environment. Within this run all models used identical CV folds. The older experiment used scikit-learn 1.9.1; version-dependent fold assignment and estimator details can differ, so compare CV values within this benchmark rather than treating its mean as a new estimate for the earlier fold assignment. The active frozen artifact was evaluated directly and reproduced its saved legacy metrics.

SVC internal probability calibration and model early-stopping validation were disabled. Each final model was fitted on training records, its raw margins standardised and calibrated on separate calibration facilities, and its cutoff chosen to maximise balanced accuracy on separate cutoff facilities. Ties preferred sensitivity. All operating points were saved before legacy evaluation.

The dataset hash was verified. No patient rows, identifiers, per-patient predictions, support vectors, nearest-neighbour examples, or fitted model files were exported. Only aggregate results and fixed settings were saved. Native categorical CatBoost inputs were not tested; its input representation was shared with the other families.

## Reproduce

Use an isolated Python 3.13 environment and install `backend/ml/requirements-comparison.txt`. From `backend`:

```powershell
python ml/compare_models.py "C:\path\to\original.csv" --output "C:\research\new-comparison"
python -m unittest discover -s tests -p test_model_comparison.py -v
```

The output directory must be new/empty and outside the active artifact directory. The benchmark never changes the model selector. Full settings, environment versions, convergence-warning counts, calibration bins and subgroup metrics are in `ml/experiments/model-family-comparison-v1/`. There were no fitting warnings recorded for the four-fold runs; LightGBM emitted a feature-name warning when predicting from the shared numeric arrays.

Method references: [XGBoost classifier API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.XGBClassifier), [histogram gradient boosting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html), and [grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html).
