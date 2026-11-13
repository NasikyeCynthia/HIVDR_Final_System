# Resistance interface update

The Resistance classification overview now shows patient ID, regimen, current drugs, seven recorded drug-exposure fields and the 15 requested drug results grouped into INSTIs, protease inhibitors, NRTIs and NNRTIs. Additional variables are optional. The patient ID and Open / analyse action stay visible while scrolling horizontally.

Exposure comes from recorded history. Blank remains Not recorded; 0/No remains No. Current treatment is marked separately. Drugs outside the current regimen remain visible.

Result sources are explicit: saved Stanford API analysis or recorded laboratory report. A saved API analysis takes precedence, and drugs omitted from that analysis remain Not assessed rather than inheriting earlier report values. Earlier report values remain available separately in the patient detail view.

To see the API working:
1. Restart the backend to load the new connection-check route, then refresh the browser.
2. Open Resistance classification and click Check live API connection. This sends only a version query and shows the returned version and check time.
3. Select Open / analyse for a patient. Review exposure and genotype, then choose Analyse with Stanford as laboratory staff for a usable, unlocked result.
4. The request state is visible. After success, the results show the algorithm version, publication date, saved time, reported genes, drug scores and categories.

The connection check is not a patient interpretation. Exposure, regimen and patient identifiers are not sent to Stanford; the genotype is used for scoring.

Validation: 64 backend tests passed; five frontend display tests passed; production build passed. In an isolated browser preview using synthetic patients, the live connection check returned HIVDB_10.2, and RT:M184V was submitted, interpreted, saved and shown on the patient detail and overview pages. Real patient data was not used in this preview. Screens and result source labels were visually checked. This does not constitute clinical validation of treatment recommendations.

## Mutation mapping and entry correction

The default overview now requests the original PI, INSTI, NRTI and NNRTI mutation columns and supported legacy aliases. Mutation notation and percentages are shown as recorded. Existing mutation evidence without a drug interpretation is labeled Awaiting interpretation instead of suggesting that no genotype was recorded.

Treatment Line at Sample collection and ART at sample collection(ART@VL@DR) are separate fields. Both now appear under their source labels; the list of drugs is derived from ART at sample collection. It is not derived from the treatment-line category.

Each patient row has Add / update mutations. It opens a prefilled four-group form on the Resistance tab. Laboratory accounts may save new entries or corrections in an unlocked record. Failed or rejected laboratory outcomes require correction through the laboratory workflow first. Saving mutation evidence does not mark a pending test usable or create test dates. A usable laboratory outcome is still required before Stanford analysis.

The new mutation save requires record and laboratory version checks plus an entry/correction note. It preserves source snapshots and frequencies, maps PI to PR, INSTI to IN, and NRTI/NNRTI to RT, and updates the Stanford input. The original source report remains intact. Previous drug interpretations and sequence are cleared from the active result when mutation evidence is saved; interpretation must be rerun for the revised pattern.

Validation: 71 backend tests passed, seven frontend tests passed, and the production build passed. The API suite was rerun after the final stale-interpretation safeguard. In an isolated browser preview, imported percentage-bearing mutation fields and the two sample-collection treatment fields were checked, and a synthetic mutation addition was saved and confirmed in the gene-qualified Stanford input. Real patient records were inspected only for aggregate mapping counts and were not changed.
