# v0.4: complete records, staff access and a trained model

The update has been prepared separately. It has not automatically changed your existing Desktop project.

## Apply without another download

Stop the frontend and backend terminals with Ctrl+C. In your existing project terminal, run:

```powershell
python .\APPLY_UPDATE.py "C:\path\to\existing\hivdr-system"
```

The staged updater copies the v0.4 source and model artifacts, makes source/database backups, and preserves your existing data, credentials, virtual environment and installed packages. Restart both servers as before. The first backend startup maps documented history into untouched original records; allow about half a minute for the initial migration of 39,711 records.

## Make the real hospital accounts usable

1. Sign in as admin and open Settings.
2. Create individual nurse, counsellor, lab and clinician accounts. Choose the exact hospital name from the imported data. Alternatively configure the existing accounts' hospital there.
3. Record the generated password shown once. Sign in with that staff account to enter clinical data.
4. An administrator manages access and assignments; the admin account deliberately does not edit clinical values.

All five old sample accounts were assigned to Demo Facility. Nurses can view all facilities in the active shared dataset, but can edit only at their assigned hospital. Other roles need an explicit all-facility view grant. The shared dataset selection is set by an administrator on the Dashboard and applies to every role until changed. Staff collaborate on permitted fields and each change is audited. Assign actual hospital names to staff accounts before they register or edit Original-data records.

## Patient records

Open a patient and choose **Full record**, or scroll below the basic Profile form. All 119 source columns are loaded into organised sections. Adherence, DBS justification and laboratory failure reason are separate supplemental fields. Nurses/counsellors can add or clear background, treatment, viral-load, psychosocial and follow-up values. Lab staff can edit laboratory fields. Decisions use clinician approval forms.

Clearing a field changes the effective record, not the imported source snapshot. Changes are audited and conflicting saves are rejected. Registry archiving hides a record from active lists; it can be restored. Approved laboratory evidence remains locked until a clinician opens an audited amendment under Decision; previous decision versions remain accessible.

Documented historical sample/results/decision fields are mapped only into untouched episodes. Existing staff-entered workflows are preserved. Missing values, including adherence absent from every original row, are not fabricated. A known risk-score subtotal of at least 60 can still flag high risk while another input is missing; low/intermediate categories require complete scoring inputs.

## Machine learning

The original-data model is available in each patient's Risk assessment tab; model evaluation is shown on the Risk assessment page and in Settings. It predicts a defined 12-drug-panel outcome and is separate from the rules-based score and clinician decision.

Random Forest was selected over Logistic Regression, trained/evaluated using 9,934 complete-panel records and disjoint hospital partitions. Held-out AUROC is 0.721, sensitivity 66.0%, and specificity 68.0%. It is a research baseline, not a clinical gatekeeper. Read `backend/ml/MODEL_CARD.md` for the target, inputs, exclusions and limitations. The backend does not require additional ML packages to run the portable JSON model.

## Verification

Backend regression tests cover permissions, records, clearing, conflict detection, archiving/restoration, staff creation, historical mapping, lab reasons, amendments and model endpoints. The full React production build was checked. A private copy of the actual database was used to verify hospital-scoped login, reading, edits, clearing, source preservation and model prediction. No live patient records were changed during these tests.

The patient list previously returned about 64 MB. Summary records and compression reduce transfer size to about 1.2 MB for the 40,210-record copy. Full records load separately. Browser visual interaction verification remains incomplete.
