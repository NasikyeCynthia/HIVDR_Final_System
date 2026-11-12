# Resistance update validation

- Backend suite: 60 tests passed, including HTTP workflows and 7 new Stanford adapter tests.
- After the final response-validation hardening: 7 Stanford adapter tests passed again.
- Frontend: npm.cmd run build passed; 112 modules transformed.
- Live API: synthetic RT:M184V returned HIVDB_10.2 (published 2026-04-26); all five categories returned and validated. Only synthetic mutations were sent.
- Regression: saving a lab result exposes its mutations for prefill; correcting it clears the prior interpretation and updates prefill.
- Boundary tests include negative scores, 9/10, 14/15, 29/30 and 59/60.
- API failures, invalid/missing scores, quality failures, mutation identifiers, multiple FASTA records and FASTA header removal are covered.
- Tests used temporary databases; the supplied patient database was not migrated or changed.
- Browser interaction and clinical deployment validation were not performed.
- Test environment: Python 3.14; isolated FastAPI/httpx dependencies. A Starlette deprecation notice about httpx was emitted, with all tests passing.
