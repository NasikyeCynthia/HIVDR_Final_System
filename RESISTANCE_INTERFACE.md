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

## Complete records and focused workflow views

Patient records now opens with all 119 source columns in exactly the dataset order. Risk score and DR-test eligibility are appended after the source columns. Values are shown as recorded, including sample/amplification codes. Optional field hiding retains dataset order. The Full record editor also opens with all fields in dataset order, with a section filter and risk details. Profile editing is scoped to patient background and treatment history.

Risk shows risk inputs, score, eligibility and model outputs. Detailed rules and methodology are expandable below the worklist. Laboratory opens on all laboratory records, with direct result and mutation actions; its summary chart is expandable. Resistance has one Drugs column using the dataset regimen value, not a duplicate split-drugs and ART display. Additional resistance variables are restricted to relevant treatment, specimen and mutation fields. Discussion retains its decision and implementation view.

The Laboratory tab has visible Enter result or Edit result controls and Add / update mutations. Existing result correction prefills the four mutation groups, sequence, subtype, test/release dates and report drug levels. PI is supported directly without mislabeling every protease mutation as major. Percentages are accepted and retained. Corrections need a reason; role permissions and reviewed-record locks remain enforced. Result entry before DR-lab referral is visible but disabled with an explanation. The mutation-entry form is available directly in Laboratory as well as Resistance.

Validation: the source column catalogue was checked against original_columns.csv and all 119 columns match exactly. All 73 backend tests and seven frontend display tests passed; production build passed. Synthetic browser checks confirmed full source ordering, visible laboratory actions, saving a result correction, and repopulating the saved drug level when reopening it. The actual patient database was not changed by verification.

## Automatic interpretation and clinician approval

New usable laboratory results and mutation corrections now create durable Stanford interpretation jobs. The backend processes them automatically after saving the laboratory evidence; interrupted jobs resume on backend restart. Existing imported results are not bulk-submitted. Laboratory staff or clinicians can explicitly request analysis of a saved result from Discussion. Only genotype tokens or sequence bases go to Stanford.

Discussion now follows evidence, clinical context, a system-generated draft and clinician approval. Stanford supplies drug scores, susceptibility levels, version and comments. Maintain/Substitute/Switch are local decision-support actions, not treatment instructions returned by Sierra. The draft includes its rule version and rationale. Missing regimen-drug coverage or multi-anchor regimens receive no automatic action. The clinician must specify the complete regimen, acknowledge current evidence and provide rationale. Version checks prevent approval against changed laboratory or patient data. No treatment is implemented automatically; the existing nurse/counsellor implementation step remains separate.

API failures retain the laboratory report and expose a retry state; missing genotype coverage never becomes susceptibility. Old in-flight responses are discarded if the laboratory record changes. Clinical decisions and source versions are audited. Original historical decisions remain preserved.

## Help, Notifications and Settings

Help & support now contains workflow guidance, roles, source/algorithm limits, troubleshooting and model details. Explanatory copy has been reduced on working screens. Navigation and dashboard icons are consistent SVG symbols; Notifications uses a bell with an unread count.

Notifications is now a paginated inbox with All/Unread/Read views, categories, patient links and read/unread actions. Read acknowledgements are stored per account in SQLite. The inbox follows outstanding work for the selected dataset/facility; marking an alert read does not complete clinical work. Settings is divided into account details, functional browser preferences, workspace dataset, integrations and administrator-only users/data/audit sections. There are no pretend email/SMS delivery controls.

Validation: the interrupted API check was successfully rerun. The combined backend suite passed 82 tests, frontend checks passed 10 tests and production builds passed. Additional focused API and automation checks cover the final state/count corrections. Synthetic browser verification confirmed result save → live Stanford HIVDB_10.2 response → draft action → clinician acknowledgement and approval, with implementation left pending. Notification read state and display preferences persisted after reload; Help search and role-specific Settings were checked. Actual patient records were not used for this preview. This verifies software behaviour, not clinical validation of the decision-support rule set.
