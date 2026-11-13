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
