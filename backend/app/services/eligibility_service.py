"""HIV drug-resistance testing eligibility, following Uganda MoH programme guidance.

This replaces the earlier points-based "risk score" as the gate for DR-test referral.
Each rule below cites the MoH document it comes from so a reviewer can check it:

  [MOH-2024]  MoH HIV Drug Resistance training presentation, April 2024, slide 65:
              all patients failing ART (1st, 2nd, 3rd line) with 2 or more consecutive
              VL >1000 copies/mL following at least 3 consecutive good IAC sessions.
  [JOBAID-160] MoH Desktop Job Aid 2020, slide 160: virological failure = two consecutive
              VL >1000 copies/mL at least 3-6 months apart, with adherence support after
              the first VL; patient on ART for at least six months.
  [JOBAID-161] Job Aid slide 161: children on an NNRTI regimen with a non-suppressed VL are
              switched immediately with IAC done simultaneously (no IAC wait); children on
              DTG or LPV/r first line: IAC, then repeat VL after 3 months.
  [JOBAID-66]  Job Aid slide 66: continue IAC until 3 consistent sessions of >95% adherence.
  [MANUAL-T1]  Participants' manual, Table 1: adherence >=95% good, 85-94% average (fair),
              <85% poor; >105% should be investigated (possible drug sharing).
  [MANUAL-2.4] Participants' manual section 2.4: a >=1 log10 drop after the three IAC
              sessions is a significant reduction.

The engine never invents data. When a criterion cannot be checked from the record it is
reported as "unknown" and the patient is placed in "needs documentation", not in
"eligible" or "not eligible".
"""
import json
import math
import re
from datetime import date, datetime, timedelta

RULE_VERSION = 'moh-who-hivdr-eligibility-2026.2'

NONSUPPRESSED_AT = 1000             # copies/mL; WHO 2021 uses >=1000 (MoH text says >1000; the WHO bound is used) [WHO-2021]
UNDETECTABLE_BELOW = 50             # copies/mL; Hoima basic-facts slide 11
MIN_REPEAT_INTERVAL_DAYS = 90       # "at least 3-6 months apart" [JOBAID-160]
SHORT_INTERVAL_DAYS = 60            # 60-89 days: flagged for review, not silently accepted
MIN_ART_DAYS = 182                  # "on ART for at least six months" [JOBAID-160]
GOOD_ADHERENCE = 95                 # [MANUAL-T1], [JOBAID-66]
FAIR_ADHERENCE = 85                 # [MANUAL-T1]
ADHERENCE_INVESTIGATE_ABOVE = 105   # [MANUAL-T1]
REQUIRED_GOOD_IAC = 3               # [MOH-2024], [JOBAID-66]
CHILD_AGE_LIMIT = 15                # "children <15 years" [JOBAID-159], [MANUAL-5.1]
DUPLICATE_WINDOW_DAYS = 45          # same value re-entered in another column

SOURCES = {
    'MOH-2024': 'MoH HIVDR training presentation (April 2024), slide 65 — eligibility',
    'JOBAID-160': 'MoH Desktop Job Aid (2020), slide 160 — definition of virological failure',
    'JOBAID-161': 'MoH Desktop Job Aid (2020), slide 161 — prior to switch; children on NNRTI',
    'JOBAID-66': 'MoH Desktop Job Aid (2020), slide 66 — IAC flow chart',
    'MANUAL-T1': 'MoH HIVDR Participants’ Manual, Table 1 — adherence levels',
    'MANUAL-2.4': 'MoH HIVDR Participants’ Manual, section 2.4 — log drop',
    'WHO-2021': 'WHO consolidated guidelines (2021): VL ≥1000 → enhanced adherence counselling, repeat VL after 3 months; '
                'switch if still ≥1000 (consider switching after one elevated VL on NNRTI)',
}

STATUS_LABELS = {
    'eligible': 'Eligible for DR testing',
    'needs_documentation': 'Criteria met, documentation incomplete',
    'not_yet': 'Not yet eligible',
    'suppressed': 'Suppressed — not eligible',
    'insufficient_data': 'Insufficient data',
    'in_process': 'Referred / in DR process',
}

NNRTI = ('NVP', 'EFV')
PI = ('LPV', 'ATV', 'DRV')
INSTI = ('DTG', 'RAL', 'BIC', 'CAB')


# ---------------------------------------------------------------- parsing helpers

def parse_date(value):
    text = str(value or '').strip().split(' ')[0].split('T')[0]
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_vl(value):
    """Return (copies, qualifier) or None. '<20' -> (20,'<'); undetectable -> (0,'<')."""
    text = str(value or '').strip().lower()
    if not text or text in ('unknown', 'left blank', 'not applicable', 'not done', 'none', 'pending'):
        return None
    if any(word in text for word in ('not detected', 'undetect', 'tnd', 'ldl')):
        return (0.0, '<')
    if any(word in text for word in ('fail', 'invalid', 'error', 'reject')):
        return None
    match = re.search(r'([<>]=?)?\s*([\d,]+(?:\.\d+)?)', text)
    if not match:
        return None
    number = float(match.group(2).replace(',', ''))
    if not math.isfinite(number) or number < 0:
        return None
    return (number, (match.group(1) or '')[:1])


def number(value):
    match = re.search(r'\d+(?:\.\d+)?', str(value or '').replace(',', ''))
    return float(match.group()) if match else None


def regimen_drugs(regimen):
    text = str(regimen or '').upper().replace('/R', '').replace(' ', '')
    return set(re.split(r'[-+/,]', text)) - {''}


def months_between(a, b):
    return (b - a).days / 30.44


def adherence_tier(pct):
    if pct is None:
        return None
    if pct > ADHERENCE_INVESTIGATE_ABOVE:
        return 'Investigate (>105%)'
    if pct >= GOOD_ADHERENCE:
        return 'Good'
    if pct >= FAIR_ADHERENCE:
        return 'Fair'
    return 'Poor'


def nonsuppressed(obs):
    copies, qualifier = obs['copies'], obs['qualifier']
    if qualifier == '<':
        return False
    return copies >= NONSUPPRESSED_AT


# ---------------------------------------------------------------- record extraction

def vl_timeline(raw):
    """All dated VL results in the record, oldest first, with duplicates collapsed.

    Column names in the CPHL extract are not reliable about order (some "prior" tests
    are dated after the DR-leading VL), so results are ordered by their own dates.
    """
    found = []

    def add(value, when, source, kind='pre'):
        parsed = parse_vl(value)
        day = parse_date(when)
        if parsed and day:
            found.append({'date': day, 'copies': parsed[0], 'qualifier': parsed[1], 'source': source, 'kind': kind})

    add(raw.get('VL Leading to DR'), raw.get('VL Test Date') or raw.get('Sample collection Date'), 'VL leading to DR')
    for i in range(1, 11):
        add(raw.get(f'vl_{i}_Prior_To_DR'), raw.get(f'VL_{i}_Prior_To_DR_TestDate') or raw.get(f'vl_{i}_Prior_To_DR_TestDate'), f'Prior VL {i}')
    for key in raw:
        match = re.fullmatch(r'viral_load_test_(\d+)', key)
        if match:
            add(raw[key], raw.get(key + '_date'), f'Recorded VL test {match.group(1)}')
    add(raw.get('VL 6 Months Post Decision'), raw.get('VL 6 Months Post Decision: Date'), '6 months post decision', 'post')
    add(raw.get('VL 12 Months Post Decision'), raw.get('VL 12 Months Post Decision: Date'), '12 months post decision', 'post')

    found.sort(key=lambda o: (o['date'], o['source']))
    result = []
    for obs in found:
        twin = next((o for o in result if o['copies'] == obs['copies'] and o['qualifier'] == obs['qualifier']
                     and abs((obs['date'] - o['date']).days) <= DUPLICATE_WINDOW_DAYS), None)
        if twin:
            twin.setdefault('also_in', []).append(obs['source'])
            continue
        result.append(obs)
    return result


def patient_age(raw, patient, on_day):
    dob = parse_date(raw.get('Date of Birth'))
    if dob and on_day:
        return (on_day - dob).days / 365.25, 'date of birth'
    age = patient.get('age')
    if age is None:
        age = number(raw.get('Age(yrs)'))
    return (age, 'recorded age') if age is not None else (None, None)


def treatment_line(raw, patient):
    line = patient.get('treatment_line')
    if line:
        return int(line)
    text = str(raw.get('Treatment Line at Sample collection') or '').lower()
    for n, word in ((1, 'first'), (2, 'second'), (3, 'third')):
        if word in text:
            return n
    return None


# ---------------------------------------------------------------- the engine

def criterion(key, label, status, detail, source):
    return {'key': key, 'label': label, 'status': status, 'detail': detail, 'source': source}


def indication_label(age, line, raw):
    if line == 2:
        return 'Patients failing on second line'
    if line == 3:
        return 'Patients failing on third line'
    if line == 1 and age is not None:
        if age < CHILD_AGE_LIMIT:
            return 'Children failing on first line'
        if age < 20:
            return 'Adolescents failing on first line'
        return 'Adults failing on first line'
    return raw.get('drIndication') or 'Indication not determined'


def iac_window(sessions, start, end):
    """Sessions done after the first non-suppressed VL and up to the repeat VL."""
    chosen = []
    for s in sessions:
        day = parse_date(s.get('session_date'))
        if day and start <= day <= end:
            chosen.append({**s, '_day': day})
    chosen.sort(key=lambda s: (s['_day'], s.get('id', 0)))
    return chosen


def assess(patient, raw, episode=None, sessions=(), today=None):
    """Return the eligibility assessment for one patient.

    patient: patients row (dict); raw: effective source record (dict);
    episode: episodes row (dict) or None; sessions: iac_sessions rows.
    """
    today = today or date.today()
    episode = episode or {}
    warnings, info = [], []
    timeline = vl_timeline(raw)
    pre = [o for o in timeline if o['kind'] == 'pre' and o['date'] <= today]
    future = [o for o in timeline if o['date'] > today]
    if future:
        warnings.append(f'{len(future)} viral load result(s) dated in the future were ignored; check the dates.')

    regimen = patient.get('regimen') or raw.get('ART at sample collection(ART@VL@DR)')
    drugs = regimen_drugs(regimen)
    line = treatment_line(raw, patient)
    latest = pre[-1] if pre else None
    age, age_basis = patient_age(raw, patient, latest['date'] if latest else today)
    if age is not None and age >= 100:
        warnings.append(f'Recorded age {age:.0f} is implausible; verify date of birth/age.')
        age = None

    criteria = []
    result = {
        'rule_version': RULE_VERSION,
        'threshold': f'≥{NONSUPPRESSED_AT} copies/mL',
        'regimen': regimen or None,
        'treatment_line': line,
        'age': None if age is None else round(age, 1),
        'age_basis': age_basis,
        'indication': indication_label(age, line, raw),
        'timeline': [{'date': o['date'].isoformat(), 'copies': o['copies'], 'qualifier': o['qualifier'],
                      'source': o['source'], 'kind': o['kind'], 'nonsuppressed': nonsuppressed(o),
                      'also_in': o.get('also_in', [])} for o in timeline],
        'criteria': criteria,
        'warnings': warnings,
        'info': info,
        'iac': [],
        'log_drop': None,
        'pathway': None,
        'next_step': '',
        'sources': SOURCES,
    }

    # Time to treatment failure on the current regimen: first VL >=1000 at least 1 month after it started
    # (an earlier high VL reflects failure carried over from the previous regimen). Descriptive only.
    current_start = parse_date(raw.get('ART@VL@DR start date'))
    result['time_to_failure'] = None
    if current_start:
        first_fail = next((o for o in timeline if o['kind'] == 'pre' and nonsuppressed(o)
                           and (o['date'] - current_start).days >= 30), None)
        if first_fail:
            result['time_to_failure'] = {'regimen_start': current_start.isoformat(), 'failure_date': first_fail['date'].isoformat(),
                                         'months': round((first_fail['date'] - current_start).days / 30.44, 1)}

    def finish(status, next_step):
        result['status'] = status
        result['label'] = STATUS_LABELS[status]
        result['next_step'] = next_step
        result['eligible'] = status == 'eligible'
        result['sample_due'] = status == 'eligible' or result.get('sample_due', False)
        return result

    # Collection alone is not "in process": under MoH practice the DR plasma sample is drawn
    # at the repeat VL, before the repeat result confirms failure.
    in_process = bool(episode.get('referred_at') or episode.get('dr_referred_at') or episode.get('report_at')
                      or episode.get('amplified') is not None
                      or episode.get('status') in ('Usable result', 'Unamplified', 'Sequencing failed', 'Rejected', 'Deferred'))

    if not pre:
        criteria.append(criterion('vl', 'Dated viral load results', 'unknown',
                                  'No viral load with a valid date is recorded.', 'JOBAID-160'))
        if in_process:
            return finish('in_process', 'Already referred or tested; record the viral load history for completeness.')
        return finish('insufficient_data', 'Record the viral load results with their test dates.')

    # --- latest result
    if not nonsuppressed(latest):
        criteria.append(criterion('latest_vl', 'Most recent viral load non-suppressed', 'not_met',
                                  f"{latest['qualifier']}{latest['copies']:,.0f} copies/mL on {latest['date']:%d %b %Y} "
                                  f"is below {NONSUPPRESSED_AT}.", 'MOH-2024'))
        if UNDETECTABLE_BELOW <= latest['copies'] < NONSUPPRESSED_AT and latest['qualifier'] != '<':
            info.append('Most recent result is 50–999 copies/mL (low-level viraemia): WHO advises enhanced adherence counselling '
                        'and a repeat viral load after 3 months.')
        if in_process:
            return finish('in_process', 'Already referred or tested; latest recorded VL is below 1000 copies/mL.')
        return finish('suppressed', 'Continue routine VL monitoring per the national schedule.')

    criteria.append(criterion('latest_vl', 'Most recent viral load non-suppressed', 'met',
                              f"{latest['copies']:,.0f} copies/mL on {latest['date']:%d %b %Y}.", 'MOH-2024'))

    # --- time on ART at the first non-suppressed result of this episode
    episode_obs = [latest]
    for obs in reversed(pre[:-1]):
        if not nonsuppressed(obs):
            break
        episode_obs.insert(0, obs)
    first_ns = episode_obs[0]
    art_start = parse_date(raw.get('Treatment Initiation Date'))
    regimen_start = parse_date(raw.get('ART@VL@DR start date'))
    if art_start:
        months = months_between(art_start, first_ns['date'])
        criteria.append(criterion('art_duration', 'On ART at least 6 months', 'met' if months >= 6 else 'not_met',
                                  f'{months:.1f} months on ART at the first non-suppressed result.', 'JOBAID-160'))
    elif regimen_start and months_between(regimen_start, first_ns['date']) >= 6:
        criteria.append(criterion('art_duration', 'On ART at least 6 months', 'met',
                                  f'ART initiation date missing; current regimen started {regimen_start:%d %b %Y}, '
                                  f'{months_between(regimen_start, first_ns["date"]):.1f} months before the first non-suppressed result.', 'JOBAID-160'))
    elif line in (2, 3):
        criteria.append(criterion('art_duration', 'On ART at least 6 months', 'met',
                                  'ART initiation date missing; inferred from being on a later-line regimen '
                                  '(a previous regimen has already failed). Record the initiation date to confirm.', 'JOBAID-160'))
    else:
        criteria.append(criterion('art_duration', 'On ART at least 6 months', 'unknown',
                                  'ART initiation date not recorded.', 'JOBAID-160'))
    if regimen_start and (first_ns['date'] - regimen_start).days < MIN_ART_DAYS:
        warnings.append('Current regimen started less than 6 months before the first non-suppressed result; '
                        'confirm the failure is on the current regimen.')

    # --- children under 15 on an NNRTI first-line regimen: single VL suffices [JOBAID-161]
    child_nnrti = (age is not None and age < CHILD_AGE_LIMIT and line == 1
                   and drugs & set(NNRTI) and not drugs & set(PI + INSTI))
    if child_nnrti:
        result['pathway'] = 'Child <15 years on NNRTI-based first line'
        criteria.append(criterion('pathway', 'Child <15 on NNRTI first line (single non-suppressed VL)', 'met',
                                  f'Age {age:.1f} ({age_basis}); regimen {regimen}.', 'JOBAID-161'))
        art = next(c for c in criteria if c['key'] == 'art_duration')
        if art['status'] == 'not_met':
            return finish('in_process' if in_process else 'not_yet',
                          'On ART less than 6 months: treatment failure cannot yet be determined.')
        if in_process:
            return finish('in_process', 'Referred/tested. Switch to second line without waiting for IAC; do IAC alongside.')
        if art['status'] == 'unknown':
            return finish('needs_documentation', 'Record the ART initiation date, then refer. Do not delay the switch; do IAC alongside.')
        return finish('eligible', 'Refer for DR testing and switch to second line immediately; do IAC alongside.')

    result['pathway'] = 'Virological failure after intensive adherence counselling'

    # --- second consecutive non-suppressed VL
    if len(episode_obs) < 2:
        prior = pre[-2] if len(pre) >= 2 else None
        detail = ('This is the first non-suppressed result after a suppressed one '
                  f"({prior['qualifier']}{prior['copies']:,.0f} on {prior['date']:%d %b %Y})." if prior else
                  'No earlier dated viral load is recorded, so this is treated as the first non-suppressed result.')
        criteria.append(criterion('repeat_vl', 'Two consecutive non-suppressed VLs', 'not_met', detail, 'MOH-2024'))
        if drugs & set(NNRTI):
            info.append('On an NNRTI regimen: WHO advises considering a switch after a single VL ≥1000 because NNRTI '
                        'resistance develops quickly. MoH requires IAC and a repeat VL for adults; discuss with the clinician.')
        good = [s for s in iac_window(sessions, latest['date'], today) if (s.get('adherence_pct') or 0) >= GOOD_ADHERENCE]
        result['iac'] = summarise_iac(iac_window(sessions, latest['date'], today))
        if in_process:
            return finish('in_process', 'Referred/tested on one documented non-suppressed VL; earlier results may be missing from the record.')
        if not prior:
            criteria[-1]['status'] = 'unknown'
            return finish('needs_documentation', 'Record earlier viral load results. If this is the first non-suppressed VL, '
                                                 'start IAC within 7–30 days and repeat the VL after 3 consecutive good sessions.')
        if len(trailing_good(iac_window(sessions, latest['date'], today))) >= REQUIRED_GOOD_IAC:
            result['sample_due'] = True
            return finish('not_yet', 'Three consecutive good IAC sessions recorded: draw the repeat viral load now, '
                                     'with 2 plasma samples (one for VL, one for HIVDR).')
        due = latest['date'] + timedelta(days=MIN_REPEAT_INTERVAL_DAYS)
        return finish('not_yet', f'Start/continue IAC (first session within 7–30 days of the result); {len(good)} good session(s) so far. '
                                 f'Repeat VL after 3 consecutive good sessions, around {due:%d %b %Y}.')

    previous = episode_obs[-2]
    gap = (latest['date'] - previous['date']).days
    criteria.append(criterion('repeat_vl', 'Two consecutive non-suppressed VLs', 'met',
                              f"{previous['copies']:,.0f} on {previous['date']:%d %b %Y} then "
                              f"{latest['copies']:,.0f} on {latest['date']:%d %b %Y}.", 'MOH-2024'))
    if gap >= MIN_REPEAT_INTERVAL_DAYS:
        criteria.append(criterion('interval', 'Repeat VL at least 3 months after the first', 'met', f'{gap} days apart.', 'JOBAID-160'))
    elif gap >= SHORT_INTERVAL_DAYS:
        criteria.append(criterion('interval', 'Repeat VL at least 3 months after the first', 'unknown',
                                  f'{gap} days apart — shorter than 3 months. Confirm all three IAC sessions were completed before the repeat VL.', 'JOBAID-160'))
    else:
        criteria.append(criterion('interval', 'Repeat VL at least 3 months after the first', 'not_met',
                                  f'Only {gap} days apart; too soon to judge the response to IAC.', 'JOBAID-160'))

    # --- log drop (supporting information only) [MANUAL-2.4]
    if previous['copies'] > 0 and latest['copies'] > 0:
        drop = math.log10(previous['copies']) - math.log10(latest['copies'])
        result['log_drop'] = {'value': round(drop, 2), 'significant': drop >= 1,
                              'text': f'{drop:.2f} log10 change between the two results '
                                      + ('(≥1 log drop: significant reduction).' if drop >= 1 else '(less than a 1 log drop).')}

    # --- IAC between the two results [MOH-2024], [JOBAID-66]
    window = iac_window(sessions, previous['date'], latest['date'])
    result['iac'] = summarise_iac(window)
    streak = trailing_good(window)
    if not window:
        criteria.append(criterion('iac', '3 consecutive good IAC sessions (adherence ≥95%) before the repeat VL', 'unknown',
                                  'No IAC sessions are recorded between the two results.', 'MOH-2024'))
    elif len(streak) >= REQUIRED_GOOD_IAC:
        criteria.append(criterion('iac', '3 consecutive good IAC sessions (adherence ≥95%) before the repeat VL', 'met',
                                  f'{len(streak)} consecutive good sessions; last on {streak[-1]["_day"]:%d %b %Y}.', 'MOH-2024'))
    else:
        criteria.append(criterion('iac', '3 consecutive good IAC sessions (adherence ≥95%) before the repeat VL', 'not_met',
                                  f'{len(window)} session(s) recorded; only {len(streak)} consecutive good session(s) at the end.', 'JOBAID-66'))
    for s in window:
        if (s.get('adherence_pct') or 0) > ADHERENCE_INVESTIGATE_ABOVE:
            warnings.append(f'IAC session on {s["_day"]:%d %b %Y} records {s["adherence_pct"]:.0f}% adherence (>105%): investigate pill sharing or counting errors.')

    statuses = {c['key']: c['status'] for c in criteria}
    if in_process:
        return finish('in_process', 'Already referred or tested.')
    if 'not_met' in (statuses.get('art_duration'), statuses.get('interval')):
        reason = ('On ART less than 6 months: failure cannot yet be determined.' if statuses.get('art_duration') == 'not_met'
                  else 'Repeat VL was drawn too soon. Complete 3 good IAC sessions, then repeat the VL.')
        return finish('not_yet', reason)
    if statuses.get('iac') == 'not_met':
        return finish('not_yet', 'Adherence was not consistently good: continue IAC until 3 consecutive sessions ≥95%, then repeat the VL.')
    if 'unknown' in statuses.values():
        missing = [c['label'] for c in criteria if c['status'] == 'unknown']
        return finish('needs_documentation', 'Viral load criteria are met. Document: ' + '; '.join(missing) + '.')
    return finish('eligible', 'Refer for DR testing: send 2 plasma samples with the request form (plasma is the recommended sample).')


def trailing_good(window):
    streak = []
    for s in reversed(window):
        if s.get('adherence_pct') is not None and GOOD_ADHERENCE <= s['adherence_pct'] <= ADHERENCE_INVESTIGATE_ABOVE:
            streak.insert(0, s)
        else:
            break
    return streak


def summarise_iac(window):
    return [{'id': s.get('id'), 'session_date': s['_day'].isoformat(), 'adherence_pct': s.get('adherence_pct'),
             'tier': adherence_tier(s.get('adherence_pct'))} for s in window]


# ---------------------------------------------------------------- persistence

def load_sessions(con, pid):
    return [dict(r) for r in con.execute('SELECT * FROM iac_sessions WHERE patient_id=? ORDER BY session_date,id', (pid,))]


def refresh(con, pid):
    p = con.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    e = con.execute('SELECT * FROM episodes WHERE patient_id=?', (pid,)).fetchone()
    if p is None or e is None:
        return None
    p = dict(p)
    raw = {**json.loads(p.get('original_json') or '{}'), **json.loads(p.get('source_overrides_json') or '{}')}
    sessions = load_sessions(con, pid)
    result = assess(p, raw, dict(e), sessions)
    from .risk_service import score
    risk = score(p, raw, sessions, result)
    ttf = result.get('time_to_failure')
    ml = risk.get('ml') or {}
    con.execute('UPDATE episodes SET eligibility_status=?,eligibility_json=?,risk_category=?,risk_flagged=?,risk_json=?,risk_ml=?,ttf=? WHERE patient_id=?',
                (result['status'], json.dumps(result, default=str), risk['category'], int(risk['flagged']), json.dumps(risk),
                 round(ml['probability'], 3) if ml.get('available') else None,
                 json.dumps([ttf['months'], ttf['regimen_start'], ttf['failure_date']]) if ttf else None, pid))
    return result


def refresh_all(con):
    ids = [r[0] for r in con.execute('SELECT id FROM patients')]
    for pid in ids:
        refresh(con, pid)
    return len(ids)
