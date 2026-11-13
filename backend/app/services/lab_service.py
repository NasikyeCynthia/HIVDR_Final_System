"""HIVDR sample and laboratory workflow, staged as in the MoH process.

Stages (one episode may have several sample attempts):
  1. Collection at the facility     -> collected_at, sample type, separation, storage
  2. Dispatch (hub pick-up)         -> dispatched_at
  3. Receipt at CPHL                -> referred to the DR lab (JCRC plasma / UVRI DBS),
                                       deferred back to the facility, or rejected
  4. DR-lab result                  -> tested, released, amplified / not amplified / failed
  5. Repeat sample                  -> a new attempt after rejection, deferral or failure

Rules and their sources (MoH HIVDR Participants' Manual unless stated):
  [M-5.2.1]  Plasma is the recommended sample type; plasma must be separated from red cells
             within 6 hours of collection; 5-8 mL whole blood.
  [M-5.2.2]  Collect into two BD PPT tubes; store processed plasma at 4-8 °C; hub pick-up
             within 2 days; sample should reach CPHL 1-7 days from collection; avoid -20/-80 °C.
  [M-5.2a]   Rejection criteria: haemolysed plasma; ART number mismatch between sample and
             form; empty PPT; <1 mL plasma; request form without patient identification.
  [M-5.4]    DBS has a high failure rate, so plasma is used for HIVDR testing; plasma to JCRC,
             DBS to UVRI; HIVDR turnaround time 30 days.
  [M-7.3.1]  CPHL refers viable samples to the DR lab or defers them to the facility:
             'Sample is used up' or 'Below threshold for HIVDR testing'.
  [JOBAID-154] Infants born to mothers failing treatment: 2 DBS at confirmation, one for HIVDR.
"""
import json
import re
from datetime import date, datetime
from ..core.errors import DomainError
from ..core.database import now
from .audit_service import audit
from .discussion_status import classify_discussion

SEPARATION_HOURS = 6
MIN_PLASMA_ML = 1.0
WHOLE_BLOOD_ML = (5.0, 8.0)
PLASMA_TUBES = 2
PICKUP_DAYS = 2
ARRIVAL_DAYS = 7
DR_TAT_DAYS = 30
STORAGE = ('2–8 °C', 'Room temperature', 'Frozen (−20 °C or −80 °C)')
DBS_REASONS = ('Infant born to a mother failing treatment (DBS at HIV confirmation)',
               'Plasma processing or cold chain not available', 'Other (explain)')
REJECTION_REASONS = ('Haemolysed plasma', 'ART number on sample and form do not match',
                     'Empty plasma preparation tube (PPT)', 'Insufficient sample (less than 1 mL plasma)',
                     'Request form without patient identification (ART or other number)', 'Other (explain)')
DEFERRAL_REASONS = ('Sample is used up', 'Below threshold for HIVDR testing', 'Other (explain)')
REJECT_FOR_CHECK = {'id_matches': REJECTION_REASONS[1], 'form_has_id': REJECTION_REASONS[4],
                    'not_haemolysed': REJECTION_REASONS[0], 'tube_not_empty': REJECTION_REASONS[2], 'volume_ok': REJECTION_REASONS[3]}
DR_LAB = {'Plasma': 'JCRC', 'DBS': 'UVRI'}
OUTCOMES = ('Usable result', 'Unamplified', 'Sequencing failed')
FINAL_FAILURES = ('Unamplified', 'Sequencing failed', 'Rejected', 'Deferred')

SOURCES = {
    'M-5.2.1': 'HIVDR Participants’ Manual §5.2.1 — sample quality indicators',
    'M-5.2.2': 'HIVDR Participants’ Manual §5.2.2 — processing, storage and transport',
    'M-5.2a': 'HIVDR Participants’ Manual §5.2(a) — sample rejection criteria',
    'M-5.4': 'HIVDR Participants’ Manual §5.4 — FAQs (sample type, DR labs, turnaround)',
    'M-7.3.1': 'HIVDR Participants’ Manual §7.3.1 — refer/defer at CPHL',
}


# ---------------------------------------------------------------- time helpers

def stamp(value, label):
    """Parse a date or date-time; store as local ISO text without time zone."""
    if value in (None, ''):
        return None
    text = str(value).strip().replace('Z', '')
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
        except ValueError:
            raise ValueError(f'{label}: enter a valid date')
    parsed = parsed.replace(tzinfo=None)
    if parsed.date() > date.today():
        raise ValueError(f'{label} cannot be in the future')
    return parsed.isoformat(timespec='minutes')


def as_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '')).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(str(value)[:10]), datetime.min.time())
        except ValueError:
            return None


def not_before(later, earlier, later_label, earlier_label):
    a, b = as_dt(later), as_dt(earlier)
    if a and b and a < b:
        raise ValueError(f'{later_label} cannot be before {earlier_label}')


# ---------------------------------------------------------------- assessment (read side)

def assess(e):
    """Stage, quality flags and turnaround for the current sample attempt."""
    flags = []

    def flag(level, text, source):
        flags.append({'level': level, 'text': text, 'source': source})

    kind = e.get('sample_type')
    collected, centrifuged = as_dt(e.get('sample_at')), as_dt(e.get('centrifuged_at'))
    dispatched, received = as_dt(e.get('dispatched_at')), as_dt(e.get('received_at'))
    tested, released = as_dt(e.get('tested_at')), as_dt(e.get('report_at'))
    status = e.get('status') or 'Not collected'

    if kind == 'DBS':
        flag('warning', 'DBS used: plasma is the recommended HIVDR sample because DBS has a high failure rate.', 'M-5.4')
        if not str(e.get('dbs_reason') or '').strip():
            flag('error' if e.get('workflow_collection') else 'warning', 'Reason for using DBS is not recorded.', 'M-5.4')
    if kind == 'Plasma' and collected:
        if centrifuged:
            hours = (centrifuged - collected).total_seconds() / 3600
            if hours > SEPARATION_HOURS:
                flag('error', f'Plasma separated {hours:.1f} h after collection (limit {SEPARATION_HOURS} h). Sample integrity is compromised; recollect.', 'M-5.2.1')
        elif e.get('workflow_collection'):
            flag('warning', 'Centrifugation time not recorded; the 6-hour separation limit cannot be checked.', 'M-5.2.1')
        tubes = e.get('tubes')
        if tubes is not None and tubes < PLASMA_TUBES:
            flag('warning', f'{tubes} PPT tube recorded; two tubes are expected.', 'M-5.2.2')
        volume = e.get('whole_blood_ml')
        if volume is not None and not WHOLE_BLOOD_ML[0] <= volume <= WHOLE_BLOOD_ML[1]:
            flag('warning', f'{volume:g} mL whole blood collected; 5–8 mL is required for sufficient plasma.', 'M-5.2.1')
    if e.get('storage_temp') and e['storage_temp'] != STORAGE[0]:
        flag('error' if 'Frozen' in e['storage_temp'] else 'warning',
             f'Stored at {e["storage_temp"]}; processed plasma should be kept at 4–8 °C and not frozen.', 'M-5.2.2')
    if collected and dispatched and (dispatched - collected).days > PICKUP_DAYS:
        flag('warning', f'Hub pick-up {(dispatched - collected).days} days after collection (target within {PICKUP_DAYS} days).', 'M-5.2.2')
    if collected and received and (received - collected).days > ARRIVAL_DAYS:
        flag('warning', f'Reached CPHL {(received - collected).days} days after collection (should be within {ARRIVAL_DAYS} days).', 'M-5.2.2')
    if e.get('plasma_volume_ml') is not None and e['plasma_volume_ml'] < MIN_PLASMA_ML:
        flag('error', f'{e["plasma_volume_ml"]:g} mL plasma received; less than 1 mL is a rejection criterion.', 'M-5.2a')
    for later, earlier, a, b in ((released, collected, 'Result release', 'collection'), (tested, collected, 'Testing', 'collection'),
                                 (received, collected, 'CPHL receipt', 'collection')):
        if later and earlier and later.date() < earlier.date():
            flag('error', f'{a} date is before {b} date; check the dates.', 'M-5.2.2')

    tat = {}
    start = received or as_dt(e.get('dr_referred_at'))
    if released and start:
        tat['lab_days'] = (released.date() - start.date()).days
    if released and collected:
        tat['total_days'] = (released.date() - collected.date()).days
    if start and not released and status == 'Pending':
        waited = (date.today() - start.date()).days
        tat['waiting_days'] = waited
        if waited > DR_TAT_DAYS:
            contact = f" Contact {e.get('officer_name')} ({e.get('officer_phone')})." if e.get('officer_phone') else ''
            flag('warning', f'No result {waited} days after CPHL receipt (HIVDR turnaround target {DR_TAT_DAYS} days).{contact}', 'M-5.4')
    if tat.get('lab_days') is not None and tat['lab_days'] > DR_TAT_DAYS:
        flag('info', f'Result released {tat["lab_days"]} days after CPHL receipt (target {DR_TAT_DAYS} days).', 'M-5.4')

    if status in OUTCOMES or (released and status not in ('Rejected', 'Deferred')):
        stage = 'Result released'
    elif status in ('Rejected', 'Deferred'):
        stage = 'Returned to facility'
    elif e.get('cphl_outcome') == 'Referred to DR lab':
        stage = 'At DR laboratory'
    elif received:
        stage = 'At CPHL'
    elif dispatched:
        stage = 'In transit'
    elif collected:
        stage = 'Collected at facility'
    elif e.get('referred_at') or e.get('repeat_requested_at'):
        stage = 'Requested'
    else:
        stage = 'Not requested'
    return {'stage': stage, 'flags': flags, 'tat': tat, 'attempt': e.get('attempt_no') or 1,
            'officer': {'name': e.get('officer_name') or '', 'phone': e.get('officer_phone') or ''},
            'dr_lab': e.get('dr_lab') or None, 'sources': SOURCES}


# ---------------------------------------------------------------- write side

def _guard(user, e):
    from ..core.permissions import require
    require(user, 'record_lab')
    if e.get('reviewed_at') or e.get('decision'):
        raise DomainError('This episode has been reviewed; its laboratory record is locked. Use the amendment workflow.', 409)


def _correction(data):
    """Returns the correction reason when a recorded step is being corrected (audited), else ''."""
    reason = str((data or {}).get('correction_reason') or '').strip()
    if reason and len(reason) < 10:
        raise ValueError('Explain the correction (at least 10 characters)')
    return reason


DRUGS = ('BIC', 'CAB', 'DTG', 'RAL', 'ATV/r', 'DRV/r', 'LPV/r', '3TC', 'ABC', 'AZT', 'TDF', 'DOR', 'EFV', 'ETR', 'NVP')
LEVELS = ('Susceptible', 'Potential Low-Level Resistance', 'Low-Level Resistance', 'Intermediate Resistance', 'High-Level Resistance')
# Mutation fields as in the CPHL report: (form key, CPHL column, Stanford gene prefix)
GENE_FIELDS = (('nrti', 'NRTI Mutations', 'RT'), ('nnrti', 'NNRTI Mutations', 'RT'), ('pi','PI','PR'), ('pi_major', 'PiMajor Mutations', 'PR'),
               ('pi_minor', 'PiMinor Mutations', 'PR'), ('insti', 'INSTI Mutations', 'IN'), ('other', 'Other Mutations', None))
TOKEN = re.compile(r'[A-Z]?\d+[A-Za-z*_/-]+', re.I)


def _snapshot(con, user, pid, e):
    con.execute('INSERT INTO lab_attempts(patient_id,actor_id,created_at,snapshot_json) VALUES(?,?,?,?)',
                (pid, user['id'], now(), json.dumps(e)))


def _overlay(con, pid, changes):
    from .record_service import overlay_changes
    overlay_changes(con, pid, changes)


def record_mutations(con,user,p,e,data):
    """Save genotype evidence separately from sample dates and laboratory outcome."""
    _guard(user,e)
    if p['data_version']!=data['expected_version'] or e['version']!=data['expected_lab_version']:
        raise DomainError('The laboratory record changed. Reload before saving mutations.',409)
    if e.get('status') in ('Unamplified','Sequencing failed','Rejected','Deferred'):
        raise DomainError('Correct the unsuccessful laboratory outcome before adding a mutation result.',409)
    reason=str(data['reason']).strip()
    if len(reason)<10:raise ValueError('Explain the mutation entry or correction (at least 10 characters).')
    from .mutation_inputs import GROUPS,validate_group_input
    tokens=[];changes={}
    for group,(gene,columns) in GROUPS.items():
        value=str(data.get(group.lower()) or '').strip()
        parsed=validate_group_input(value,gene)
        for token in parsed:
            if token not in tokens:tokens.append(token)
        # Save source notation (including frequencies); clear obsolete alternate fields for this group.
        for column in columns:changes[column]=value if column==group else ''
    if not tokens:raise ValueError('Enter at least one reported mutation. For a mutation-free report use the laboratory sequence.')
    _snapshot(con,user,p['id'],e)
    changes['All Mutations Combined']=' '.join(tokens)
    # Older report classifications must not masquerade as interpretations of revised mutations.
    from .record_service import effective_record
    changes.update({key:'' for key in effective_record(p) if key.startswith('Resistance to ')})
    _overlay(con,p['id'],changes)
    con.execute("UPDATE episodes SET mutations=?,sequence='',interpretation_json=NULL,interpreted_at=NULL,suggestion_json=NULL,version=version+1 WHERE patient_id=?",(' '.join(tokens),p['id']))
    audit(con,user,'laboratory mutations saved',p['id'],{'mutations':e.get('mutations')},
          {'fields':{key:changes[key] for key in GROUPS},'reason':reason})


def record_collection(con, user, p, e, data):
    _guard(user, e)
    pid = p['id']
    correcting = _correction(data)
    if correcting and not e.get('sample_at'):
        raise ValueError('There is no recorded collection to correct')
    if not correcting and e.get('status') not in (None, 'Not collected'):
        raise ValueError('A sample is already recorded for this attempt. Correct it, or request a new sample to start a new attempt.')

    eligibility = json.loads(e.get('eligibility_json') or '{}')
    # MoH order: the DR test is requested first (request form, accountable officer). The one exception is the
    # repeat-VL bleed after 3 good IAC sessions, when 2 plasma samples are drawn before the repeat VL result is known.
    if not correcting and not (e.get('referred_at') or e.get('repeat_requested_at') or eligibility.get('sample_due')):
        raise ValueError('Request the DR test first (step 1), so the request form and the accountable officer are recorded. '
                         + str(eligibility.get('next_step', '')))
    kind = data.get('sample_type')
    if kind not in DR_LAB:
        raise ValueError('Choose plasma or DBS')
    collected = stamp(data.get('collected_at'), 'Collection date and time')
    if not collected:
        raise ValueError('Collection date and time are required')
    dbs_reason = ''
    if kind == 'DBS':
        choice, note = str(data.get('dbs_reason') or '').strip(), str(data.get('dbs_note') or '').strip()
        if choice not in DBS_REASONS:
            raise ValueError('Choose why DBS is used instead of plasma')
        if choice.startswith('Other') and len(note) < 5:
            raise ValueError('Explain why DBS is used')
        dbs_reason = choice + (f' — {note}' if note else '')
    centrifuged = stamp(data.get('centrifuged_at'), 'Centrifugation time') if kind == 'Plasma' else None
    if kind == 'Plasma' and not centrifuged:
        raise ValueError('Record when the plasma was centrifuged (must be within 6 hours of collection)')
    not_before(centrifuged, collected, 'Centrifugation', 'collection')
    officer = str(data.get('officer_name') or '').strip() or user.get('name', '')
    phone = re.sub(r'[\s-]', '', str(data.get('officer_phone') or ''))
    if not re.fullmatch(r'\+?\d{9,15}', phone):
        raise ValueError('Give a phone number for the laboratory officer in charge, so the facility can follow up delayed results')
    storage = data.get('storage_temp') or STORAGE[0]
    if storage not in STORAGE:
        raise ValueError('Choose a storage temperature')
    _snapshot(con, user, pid, e)
    if correcting:
        con.execute('''UPDATE episodes SET sample_type=?,dbs_reason=?,sample_at=?,centrifuged_at=?,tubes=?,whole_blood_ml=?,storage_temp=?,
                       officer_name=?,officer_phone=?,version=version+1 WHERE patient_id=?''',
                    (kind, dbs_reason, collected, centrifuged, data.get('tubes'), data.get('whole_blood_ml'), storage, officer, phone, pid))
    else:
        con.execute('''UPDATE episodes SET sample_type=?,dbs_reason=?,sample_at=?,centrifuged_at=?,tubes=?,whole_blood_ml=?,storage_temp=?,
                       workflow_collection=1,lab_owner=?,officer_name=?,officer_phone=?,status='Pending',interpretation_json=NULL,interpreted_at=NULL,version=version+1
                       WHERE patient_id=?''',
                    (kind, dbs_reason, collected, centrifuged, data.get('tubes'), data.get('whole_blood_ml'), storage, user['id'], officer, phone, pid))
    _overlay(con, pid, {'Sample Type': 'P' if kind == 'Plasma' else 'D', 'Sample collection Date': collected[:10],
                        'DBS justification': dbs_reason})
    audit(con, user, 'DR sample collection corrected' if correcting else 'DR sample collected', pid, e, data)


def record_dispatch(con, user, p, e, data):
    _guard(user, e)
    correcting = _correction(data)
    if correcting and not e.get('dispatched_at'):
        raise ValueError('There is no recorded pick-up to correct')
    if not e.get('sample_at') or (not correcting and e.get('status') != 'Pending'):
        raise ValueError('Record the sample collection first')
    if e.get('received_at') and not correcting:
        raise ValueError('The sample has already been received at CPHL')
    dispatched = stamp(data.get('dispatched_at'), 'Dispatch date')
    if not dispatched:
        raise ValueError('Dispatch date is required')
    not_before(dispatched, e['sample_at'], 'Dispatch', 'collection')
    con.execute('UPDATE episodes SET dispatched_at=?,version=version+1 WHERE patient_id=?', (dispatched, p['id']))
    audit(con, user, 'DR sample pick-up corrected' if correcting else 'DR sample dispatched', p['id'], {'dispatched_at': e.get('dispatched_at')}, data)


def record_receipt(con, user, p, e, data):
    _guard(user, e)
    pid = p['id']
    correcting = _correction(data)
    if correcting:
        if not e.get('cphl_outcome'):
            raise ValueError('There is no recorded CPHL receipt to correct')
        if e.get('status') in OUTCOMES:
            raise ValueError('A DR-lab result is already recorded; correct the result instead, or request a new sample')
    else:
        if not e.get('sample_at') or e.get('status') != 'Pending':
            raise ValueError('Record the sample collection first')
        if e.get('cphl_outcome'):
            raise ValueError('CPHL receipt is already recorded for this sample; use “Correct this step” to change it')
    received = stamp(data.get('received_at'), 'CPHL receipt date')
    if not received:
        raise ValueError('CPHL receipt date is required')
    not_before(received, e.get('dispatched_at') or e['sample_at'], 'Receipt', 'dispatch/collection')
    outcome = data.get('outcome')
    reason = str(data.get('reason') or '').strip()
    note = str(data.get('note') or '').strip()
    volume = data.get('plasma_volume_ml')
    # 1. Sample acceptance checks — the MoH rejection criteria [M-5.2a]
    checks = data.get('checks') or {}
    failed = [REJECT_FOR_CHECK[k] for k in REJECT_FOR_CHECK if checks.get(k) is False]
    if volume is not None and volume < MIN_PLASMA_ML and REJECTION_REASONS[3] not in failed:
        failed.append(REJECTION_REASONS[3])
    if failed and outcome != 'Rejected':
        raise ValueError('The sample fails an acceptance check (' + '; '.join(failed) + '): record it as rejected')
    if failed and reason not in failed:
        reason = failed[0]
    # 2. Repeat viral load from the same blood draw decides whether the DR test goes ahead [M-7.3.1]
    vl, vl_date = data.get('repeat_vl'), data.get('repeat_vl_date')
    if vl is not None and not vl_date:
        raise ValueError('Give the date of the repeat viral load')
    if vl is not None and vl < 1000 and outcome == 'Referred to DR lab':
        raise ValueError('The repeat viral load is below 1000 copies/mL: defer as "Below threshold for HIVDR testing"')
    if outcome == 'Referred to DR lab':
        if e.get('sample_type') == 'Plasma' and volume is not None and volume < MIN_PLASMA_ML:
            raise ValueError('Less than 1 mL plasma is a rejection criterion: record the sample as rejected')
        status, lab, reason = 'Pending', DR_LAB[e['sample_type']], ''
    elif outcome == 'Rejected':
        if reason not in REJECTION_REASONS:
            raise ValueError('Choose the rejection reason')
        status, lab = 'Rejected', None
    elif outcome == 'Deferred to facility':
        if reason not in DEFERRAL_REASONS:
            raise ValueError('Choose the deferral reason')
        status, lab = 'Deferred', None
    else:
        raise ValueError('Choose refer, defer or reject')
    if reason.startswith('Other') and len(note) < 5:
        raise ValueError('Explain the reason')
    full_reason = (reason + (f' — {note}' if note else '')) if reason else ''
    con.execute('''UPDATE episodes SET received_at=?,plasma_volume_ml=?,cphl_outcome=?,cphl_reason=?,dr_lab=?,dr_referred_at=?,
                   status=?,failure_reason=?,receipt_checks=?,cphl_vl=?,cphl_vl_date=?,version=version+1 WHERE patient_id=?''',
                (received, volume, outcome, full_reason, lab, received if lab else None, status, full_reason,
                 json.dumps(checks), vl, str(vl_date) if vl_date else None, pid))
    if vl is not None:
        raw = {**json.loads(p.get('original_json') or '{}'), **json.loads(p.get('source_overrides_json') or '{}')}
        n = 1 + max([int(k.rsplit('_', 1)[1]) for k in raw if re.fullmatch(r'viral_load_test_\d+', k)] or [0])
        _overlay(con, pid, {f'viral_load_test_{n}': str(vl), f'viral_load_test_{n}_date': str(vl_date)})
    if lab:
        _overlay(con, pid, {'Date referred to DR Lab': received[:10]})
    if correcting:
        _snapshot(con, user, pid, e)
    audit(con, user, 'CPHL receipt corrected' if correcting else 'DR sample received at CPHL', pid, e, data)


def record_result(con, user, p, e, data):
    _guard(user, e)
    pid = p['id']
    correcting = _correction(data)
    if correcting:
        if e.get('status') not in OUTCOMES:
            raise ValueError('There is no recorded result to correct')
    elif e.get('cphl_outcome') != 'Referred to DR lab' or e.get('status') != 'Pending':
        raise ValueError('A result can only be recorded for a sample referred to the DR laboratory')
    outcome = data.get('outcome')
    if outcome not in OUTCOMES:
        raise ValueError('Choose the laboratory outcome')
    tested = stamp(data.get('tested_at'), 'Test date')
    released = stamp(data.get('released_at'), 'Result release date')
    if not (tested and released):
        raise ValueError('Test date and result release date are required')
    not_before(tested, e['received_at'], 'Testing', 'CPHL receipt')
    not_before(released, tested, 'Release', 'testing')
    failure = str(data.get('failure_reason') or '').strip()
    if outcome != 'Usable result' and not failure:
        raise ValueError('An unsuccessful-test reason is required')
    # Mutations may be entered per gene/drug class (as on the CPHL report) and/or as one gene-prefixed list.
    groups = {}
    for key, column, gene in GENE_FIELDS:
        if gene:
            from .mutation_inputs import validate_group_input
            tokens=[token.split(':',1)[1] for token in validate_group_input(data.get(key),gene)]
        else:
            tokens = str(data.get(key) or '').replace(';', ',').replace(',', ' ').split()
        bad = [t for t in tokens if not TOKEN.fullmatch(t)]
        if bad:
            raise ValueError(f'{column}: not recognised as mutations — ' + ', '.join(bad[:5]) + ' (write e.g. M184V K65R)')
        groups[key] = [t.upper() for t in tokens]
    prefixed = [f'{gene}:{t}' for key, column, gene in GENE_FIELDS if gene for t in groups[key]]
    mutations = ' '.join(dict.fromkeys(str(data.get('mutations') or '').replace(',', ' ').split() + prefixed))  # no duplicates
    levels = data.get('drug_levels') or {}
    unknown = [d for d, v in levels.items() if d not in DRUGS or (v and v not in LEVELS)]
    if unknown:
        raise ValueError('Unrecognised drug or resistance level: ' + ', '.join(unknown))
    sequence = ''.join(line.strip() for line in str(data.get('sequence') or '').splitlines() if not line.startswith('>')).replace(' ', '').upper()
    if outcome == 'Usable result':
        # Genotypic testing (Sanger sequencing of pol) gives a sequence and its mutation list; phenotype is not used.
        if not mutations and not sequence and not any(groups.values()):
            no_mut = str(data.get('mutations') or '').strip().lower() in ('none', 'no mutations')
            if not no_mut:
                raise ValueError('An amplified result needs the reported mutations (per drug class or as a list), or the pol nucleotide sequence')
        bad = [t for t in mutations.split() if not re.fullmatch(r'(PR|RT|IN):[A-Z]?\d+[A-Za-z*_/-]+', t, re.I)]
        if bad and not mutations.lower() in ('none', 'no mutations'):
            raise ValueError('Write mutations with the gene, e.g. RT:K103N IN:G118R. Not recognised: ' + ', '.join(bad[:5]))
        if sequence and (len(sequence) < 30 or not re.fullmatch('[ACGTRYSWKMBDHVN-]+', sequence)):
            raise ValueError('The sequence must contain at least 30 nucleotide (IUPAC) letters')
    amplified = 0 if outcome == 'Unamplified' else 1
    _snapshot(con, user, pid, e)
    discussion = classify_discussion(None, e.get('decision'), amplified if outcome == 'Usable result' else None)
    con.execute('''UPDATE episodes SET tested_at=?,report_at=?,status=?,amplified=?,failure_reason=?,mutations=?,sequence=?,subtype=?,discussion_status=?,
                   interpretation_json=NULL,interpreted_at=NULL,suggestion_json=NULL,repeat_requested_at=NULL,version=version+1 WHERE patient_id=?''',
                (tested, released, outcome, amplified, failure if outcome != 'Usable result' else '', mutations, sequence,
                 str(data.get('subtype') or '').strip(), discussion, pid))
    changes = {'dateTestedForDR': tested[:10], 'DR_results_releaseDate': released[:10],
               'amplified': str(amplified), 'Lab failure reason': failure if outcome != 'Usable result' else '',
               'All Mutations Combined': '; '.join(', '.join(groups[k]) for k, _, _ in GENE_FIELDS) if any(groups.values()) else mutations}
    for key, column, gene in GENE_FIELDS:
        if groups[key] or correcting:
            changes[column] = ', '.join(groups[key])
    if groups['pi'] or groups['pi_major'] or groups['pi_minor'] or correcting:
        changes['PI Mutations Combined'] = ', '.join(groups['pi'] + groups['pi_major'] + groups['pi_minor'])
    # Keep the original dataset group columns in sync with a newly entered lab report.
    class_values={'PI':groups['pi']+groups['pi_major']+groups['pi_minor'],'INSTI':groups['insti'],
                  'NRTI':groups['nrti'],'NNRTI':groups['nnrti']}
    for column,values in class_values.items():
        if values or correcting:
            source_keys={'PI':['pi','pi_major','pi_minor'],'INSTI':['insti'],'NRTI':['nrti'],'NNRTI':['nnrti']}[column]
            changes[column]=', '.join(str(data.get(key) or '').strip() for key in source_keys if str(data.get(key) or '').strip())
    if correcting:
        from .record_service import effective_record
        changes.update({key:'' for key in effective_record(p) if key.startswith('Resistance to ')})
    for drug, level in levels.items():
        if level:
            changes['Resistance to ' + drug] = level
    _overlay(con, pid, changes)
    audit(con, user, 'DR result corrected' if correcting else 'DR result recorded', pid, e, data)


def request_repeat_sample(con, user, p, e, data):
    _guard(user, e)
    note = str((data or {}).get('note') or '').strip()
    if e.get('status') == 'Pending':
        if len(note) < 5:
            raise ValueError('Say why a new sample is needed (e.g. sample lost, leaking or broken in transit)')
    elif e.get('status') not in FINAL_FAILURES:
        raise ValueError('A new sample can be requested while a sample is in process, or after rejection, deferral or an unsuccessful test')
    reason = (e.get('failure_reason') or e.get('cphl_reason') or e.get('status') or '').strip()
    reason = f'{e.get("status")}: {reason}' if reason and reason != e.get('status') else reason
    if note:
        reason += f' — {note}'
    _snapshot(con, user, p['id'], e)
    con.execute('UPDATE episodes SET repeat_reason=? WHERE patient_id=?', (reason, p['id']))
    con.execute('''UPDATE episodes SET attempt_no=COALESCE(attempt_no,1)+1,repeat_requested_at=?,status='Not collected',sample_type=NULL,
                   dbs_reason='',sample_at=NULL,centrifuged_at=NULL,tubes=NULL,whole_blood_ml=NULL,storage_temp=NULL,workflow_collection=0,
                   dispatched_at=NULL,received_at=NULL,plasma_volume_ml=NULL,cphl_outcome=NULL,cphl_reason='',dr_lab=NULL,dr_referred_at=NULL,
                   tested_at=NULL,report_at=NULL,amplified=NULL,failure_reason='',mutations='',sequence='',subtype='',receipt_checks=NULL,cphl_vl=NULL,cphl_vl_date=NULL,officer_name='',officer_phone='',interpretation_json=NULL,interpreted_at=NULL,
                   version=version+1 WHERE patient_id=?''', (now(), p['id']))
    audit(con, user, 'repeat sample requested', p['id'], e)
