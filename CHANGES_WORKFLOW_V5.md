# Clinical refinement — complete workflow (supersedes CHANGES_ASPECTS_1_2.md)

## Apply
1. Back up `backend/data/surveillance.sqlite3`.
2. Copy this zip over `Final_system` (same paths). It replaces `risk_service.py` with the new
   points score; no files need deleting.
3. Start the backend: new columns are added and eligibility, risk and ML estimates are computed
   once for every record (about 30–40 s for 40,210 records).
4. `python -m pytest tests` (49 pass) and `npm run build`.

## Workflow and roles (enforced in `backend/app/core/permissions.py`)
Everyone can view; only the responsible role can change a step; edits only at one's own facility.
Dashboard → Patient records (nurse/counsellor) → Risk & eligibility → DR-test request and Laboratory (lab; the requesting officer is accountable) →
Resistance (Stanford; lab) → Discussion & decision (clinician approves) →
Implementation & 6-monthly follow-up (assigned nurse/counsellor). Psychosocial assessment
(nurse/counsellor) with recommended support.

## Clinical rules
- Eligibility: MoH (April 2024; Job Aid 2020) with WHO 2021 threshold VL ≥1000.
- Risk points score: see `backend/ml/RISK_SCORE.md`. ML estimate shown with every score.
- Laboratory: MoH sample rules; officer in charge + phone required; amplified results need
  mutations or a pol sequence; repeat sample as a new attempt.
- Decision support: suggested Maintain/Substitute/Switch from Stanford levels for the current
  regimen; profile (incl. adherence and psychosocial assessment) must be complete to approve.
- Implementation: start date, regimen started, previous regimen stop date; follow-up every
  6 months (VL, regimen, care status, psychosocial issues), as in the MoH HIVDR database.

## Dashboard
Nothing removed. Added: flagged-high-risk tile, eligibility chart, HIVDR cascade (MoH report
layout), lab pipeline, and extra "Needs attention" rows.

## Update (roles and score)
- DR tests are requested only by laboratory staff; the requester becomes the patient's accountable
  laboratory officer. Requests outside the automated criteria need a written indication.
- Clinicians: committee discussion and decisions only. Nurses/counsellors: registration, records
  (incl. IAC and psychosocial), implementation and follow-up. Everyone can view everything.
- Risk score: the "VL below 10,000" point was removed. VL ≥1000 is the gate for scoring;
  held-out AUROC 0.710; bands Low 41%, Moderate 67%, High 78% with resistance.
