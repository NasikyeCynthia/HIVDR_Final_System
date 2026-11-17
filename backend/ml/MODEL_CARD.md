# Active HIVDR history model — research estimate

Activated on 17 November 2026 as `hivdr-panel-v2-history`. The retrained forest from `experiments/history-v2/model.json` is selected by a fingerprint-pinned `artifacts/active_model.json`. The original `artifacts/model.json` remains unchanged for rollback and historical comparisons.

## Purpose and target

Estimate the probability of **any low-level-or-greater resistance across the fully observed 12-drug RT/IN panel** among referred and tested patients. This is a research estimate that can support exploration of prioritisation; it is not a validated standalone clinical prioritisation policy, a diagnosis, testing eligibility or a treatment recommendation.

Panel: BIC, CAB, DTG, RAL, 3TC, ABC, AZT, TDF, DOR, EFV, ETR, NVP. Target 1 means any Low-Level, Intermediate or High-Level Resistance result; target 0 means every panel result is Susceptible or Potential Low-Level Resistance. PI-only resistance is not included in the target. Failed amplification or incomplete panel outcomes were excluded, not labelled negative.

## Feature variables

There are 31 numeric/indicator variables plus two categorical variables before encoding:

- Original numeric variables: log-transformed index VL, age, treatment line, ART duration at sample collection, log-transformed latest dated prior VL, prior VL observation count.
- Categorical variables: sex and regimen.
- Additional history variables: years on the indexed regimen, time since the latest dated prior VL, maximum and mean log prior VL, fraction of prior results ≥1000, log change from the latest prior VL to index VL, consecutive prior results ≥1000, duration of ongoing non-suppression.
- Seventeen current-regimen drug-component indicators: DTG, BIC, CAB, RAL, LPV, ATV, DRV, EFV, NVP, DOR, ETR, TDF, TAF, AZT, ABC, 3TC, FTC. The artifact preprocessing defines the exact feature schema.

For exact machine-readable names and order, inspect the artifact preprocessing and `app/services/ml_history_features.py`. Indicators describe drugs in the indexed regimen, not the dataset's historical exposure columns. Missing optional numeric inputs use stored training medians with missingness indicators; categorical inputs use stored categories. Viral load and treatment line are required for a live estimate. Synthetic datasets are not scored.

When a sample date is recorded, the predictor takes index VL, age, sex, treatment line and regimen from the effective source snapshot (original values plus audited corrections), rather than later core-table follow-up values. Dated prior observations after the sample are excluded. Training and serving share the same extractor. Adherence, psychosocial results, mutations, resistance results, committee decisions and post-decision outcomes are not predictors.

## Training and selection

The source CSV has 39,711 records; the amplified, complete-panel cohort has 9,934. Four-fold facility-grouped cross-validation within 6,620 training records compared seven fixed configurations. Preprocessing was fitted separately within each training fold.

The selected history model is a 300-tree random forest, maximum depth 12, minimum leaf size 8, balanced class weights. Its mean development-fold AUROC was 0.729, versus 0.717 for history-input logistic regression. The original-input original-configuration forest had mean development-fold AUROC 0.714 in the preceding experiment.

Calibration used 518 records from 94 separate facilities. The research cutoff, 0.62, maximised balanced accuracy on 1,057 other records from 95 facilities. Selection, calibration and cutoff fitting did not use legacy-test labels. All four partitions have disjoint facilities.

## Retrospective legacy comparison

The 1,739-record test cohort had already been examined during earlier development and audits. These are exploratory internal comparison results, **not a fresh independent validation**. Feature-family exploration followed the first retraining experiment. No new clinical records were added.

| Measure | Active retrained model | Original model |
| --- | ---: | ---: |
| AUROC | 0.744 | 0.721 |
| Average precision | 0.803 | 0.788 |
| Accuracy | 69.6% | 66.8% |
| Balanced accuracy | 68.3% | 67.0% |
| Sensitivity | 74.1% | 66.0% |
| Specificity | 62.5% | 68.0% |
| Precision | 75.7% | 76.5% |
| Negative predictive value | 60.4% | 55.9% |
| Brier score | 0.196 | 0.203 |

Active confusion matrix: TP 789, FN 276, TN 421, FP 253. There were 86 fewer missed positive cases and 37 additional false positives. A paired 500-replicate facility bootstrap gave an AUROC-difference interval of +0.011 to +0.036; this does not incorporate model/feature-selection uncertainty.

TDF-3TC-DTG sensitivity is 53.8%, and third-line specificity remains 0%. A below-cutoff percentage does not rule out resistance. Performance in untested clinic populations and prospective clinical utility remain unestablished. Stable patient IDs were unavailable, so cross-facility transfers cannot be excluded.

## Runtime and cached predictions

`ml_service.py` validates the selected weight fingerprint and feature schema. Runtime inference uses only Python's standard library. `ml_history_features.py` is shared with training through a compatibility import in `ml/history_features.py`. The original feature transform now follows the artifact's stored feature order.

Prediction metadata records the model version, weight fingerprint, feature schema and pipeline version. Startup refreshes stale ML caches in short batches. Computation occurs outside database write transactions; source-version and risk-snapshot checks prevent overwriting concurrent edits. Only `episodes.risk_json.ml` and `episodes.risk_ml` are replaced. Points scores, eligibility, source records, laboratory interpretations and decisions are preserved.

To roll back, select `{"model":"v1"}` in `ml/artifacts/active_model.json` and restart the backend. Startup will recalculate cached probabilities for that version. Restoring the original selector is a model rollback, not retraining.

## Evidence and limitations

Exact training settings, metrics, calibration bins and subgroup checks remain in `experiments/history-v2/`. The active evaluation endpoint identifies these as legacy comparison results and does not attach the old v1 validation report to v2. No independent clinical validation is claimed by activation. A new external/later cohort and clinically agreed operating trade-offs are still needed before clinical deployment.

For the original model, see `MODEL_CARD_V1.md`. For experiment reproduction, see `RETRAINING.md` and `requirements-retraining.txt`.
