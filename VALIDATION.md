# v0.4 validation

- React/Vite production build passed.
- 23 backend/API regression checks passed. They cover field preservation, clearing, role and facility permissions, concurrent save conflicts, account creation, archiving/restoration, clinician amendments, laboratory reason requirements and model inference.
- Actual-data private-copy smoke test passed: hospital-specific account login, scoped record access, field edits/clearing, source preservation and prediction. No live Desktop records changed.
- Random Forest and Logistic Regression compared on facility-disjoint validation data. Random Forest selected; held-out AUROC 0.721 on 1,739 records. Detailed metrics and limitations: backend/ml/MODEL_CARD.md.
- Portable model export verified against sklearn held-out predictions to 1e-8 probability.
- First automatic historical mapping tested on a private copy of 39,711 original records.
- Compact patient list measured at 1.17 MB compressed for 40,210 active records.
- Browser visual/interaction verification remains incomplete. Production identity, deployment and prospective clinical model validation are not established by these checks.
