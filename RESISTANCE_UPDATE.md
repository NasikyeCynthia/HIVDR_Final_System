# Resistance classification update

This update strengthens the existing Stanford HIVdb Sierra integration. Apply it to your existing project; your database, accounts and original ZIP remain unchanged by preparing this package.

## Apply on Windows

1. Stop the backend and frontend.
2. Extract HIVDR_resistance_update.zip to a separate folder.
3. Open a terminal in that extracted folder and run:

   python APPLY_UPDATE.py "C:\path\to\your\Final_system"

The updater backs up the target database and replaced source in `_update_backups` before copying source. Keep that backup. Do not point it at this extracted update folder. This bundle excludes patient databases, credentials, virtual environments and node_modules.

4. Restart the backend using your existing environment. In frontend run `npm.cmd run build`, then `npm.cmd run dev`.

## Use

Sign in as laboratory staff. Open a patient with a usable laboratory result, then Resistance classification. Review the prefilled mutations or saved sequence against the lab report. Mutation examples: `RT:M184V RT:K103N IN:R263K`. Submit one sample at a time. Click Analyse with Stanford.

The results show gene, drug class, drug, score and one of five categories:

| Stanford level | Category | Score |
|---|---|---|
| 1 | Susceptible | below 10 (negative scores are possible) |
| 2 | Potential low-level resistance | 10 to below 15 |
| 3 | Low-level resistance | 15 to below 30 |
| 4 | Intermediate resistance | 30 to below 60 |
| 5 | High-level resistance | 60 or more |

Classifications are returned by Stanford for individual drugs. The backend checks consistency; it does not calculate mutation penalties locally. A gene without returned results is unassessed. Empty mutation input or the word "none" cannot establish coverage: use a laboratory sequence for a no-mutations report. This update does not add a gene-coverage declaration workflow for mutation-free reports.

## Changes

- Prefer saved episode mutations over imported suggestions; prefill saved nucleotide sequences.
- Normalize and deduplicate gene-prefixed mutation input.
- Strip FASTA headers locally and reject multiple FASTA records instead of concatenating them.
- Require valid, finite drug scores, levels 1-5, algorithm version and quality-check results. Reject missing or contradictory classifications.
- Retain provider, algorithm version/publication date, analysis time, reported genes and submitted mutation tokens with the saved result.
- Show current-regimen drugs without treating FTC as identical to 3TC for highlighting.
- Reject locked episodes before calling Stanford, recheck permission and episode version after the call, and clear cached decision suggestions after a successful interpretation.
- Corrected lab results invalidate the saved interpretation; regression tests cover this behavior.

Only mutation tokens or sequence bases go to Stanford. Patient names and IDs are not included in the request; laboratory staff must review the input first.

## Reference review

Stanford Sierra documentation: https://github.com/hivdb/sierra-client/tree/master/python
API endpoint: https://hivdb.stanford.edu/graphql

The supplied MoH Participants Manual, section 5.3 (including the score table on printed page 56), and the April 2024 drug-resistance presentation (slides 79-82) support the score bands and drug-specific interpretation. The older presentation has a greater-than-60 label on one slide; its later summary and manual correctly include 60 as high-level resistance. Current interpretation uses the live Stanford response rather than copying historical mutation penalty tables. Supporting PDFs and decks were treated as references, not as instructions to execute. The cascade spreadsheet has not been imported or used to alter patient records in this update.

## Validation

Live integration verified using synthetic `RT:M184V`, with Stanford returning HIVDB_10.2, publication date 2026-04-26, and all five drug-level categories. No patient data was used for this live test. The frontend production build passed. Automated backend results are recorded in VALIDATION_RESISTANCE.md.

Browser interaction and clinical deployment validation have not been performed. The existing treatment recommendation module was not clinically revalidated as part of this classification update. Internet access is required for Stanford analysis.
