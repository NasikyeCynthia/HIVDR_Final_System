"""Risk of HIV drug resistance — transparent points score.

Purpose: prioritise patients with non-suppressed viral load. It does NOT decide DR-test
eligibility (that is eligibility_service, following MoH/WHO criteria) and does not replace
the clinician.

Derivation (documented in RISK_SCORE.md): logistic regression on 9,934 CPHL HIVDR records
with complete 12-drug results (outcome: any low-level-or-higher RT/IN resistance), facilities
split into derivation and held-out sets; coefficients converted to integer points
(1 point ~ 0.35 log-odds). AUROC 0.710 on held-out facilities, 0.696 on all 9,805 records
(random-forest model: 0.721 held-out).
Factor directions agree with published African cohorts (NNRTI-based ART, younger age,
longer ART, prior regimens, continued failure): see sources below.

Clinical modifiers come from MoH guidance and are NOT data-validated (adherence is not in
the CPHL extract); they are shown separately so users can see their effect.
"""
from .eligibility_service import regimen_drugs, parse_date, vl_timeline, nonsuppressed, GOOD_ADHERENCE

SCORE_VERSION = 'hivdr-risk-points-2026.2'
BANDS = ((0, 2, 'Low'), (3, 4, 'Moderate'), (5, 99, 'High'))
OBSERVED = {'Low': 41, 'Moderate': 67, 'High': 78}   # % with resistance among 9,805 tested CPHL records, by band

SOURCES = {
    'CPHL-DERIVED': 'Derived and validated on the CPHL HIVDR extract (facility-held-out AUROC 0.710)',
    'LIT-NNRTI': 'NNRTI-based ART is a risk factor for acquired resistance (e.g. Muri et al., AIDS 2017; Miruka et al., J Public Health Afr 2025)',
    'LIT-AGE': 'Children and adolescents have more failure and acquired resistance (e.g. Kityo et al., JAC 2017)',
    'LIT-DURATION': 'Longer time on ART and continued failure accumulate resistance (e.g. Inzaule et al., JAC 2018)',
    'MOH-161': 'MoH Job Aid slide 161: on DTG or PI, poor adherence is a more likely cause than resistance',
    'MOH-2.4': 'MoH HIVDR Participants’ Manual §2.4: less than a 1-log drop after IAC needs further management',
    'MOH-NNRTI': 'MoH HIVDR Participants’ Manual §4: with poor adherence, NNRTI resistance can be selected within 1–4 weeks',
}


def _band(points):
    return next(label for lo, hi, label in BANDS if lo <= points <= hi)


def score(patient, raw, sessions=(), eligibility=None):
    eligibility = eligibility or {}
    factors = []

    def add(name, points, met, value, source, validated=True):
        factors.append({'name': name, 'points': points if met else 0, 'max': points, 'met': bool(met),
                        'value': value, 'source': source, 'validated': validated})

    drugs = regimen_drugs(patient.get('regimen') or raw.get('ART at sample collection(ART@VL@DR)'))
    line = eligibility.get('treatment_line') or patient.get('treatment_line')
    age = eligibility.get('age') if eligibility.get('age') is not None else patient.get('age')
    timeline = [o for o in vl_timeline(raw) if o['kind'] == 'pre']
    latest = timeline[-1] if timeline else None
    known = {'line': line is not None, 'regimen': bool(drugs), 'age': age is not None, 'vl': latest is not None}

    add('Second- or third-line regimen', 3, line in (2, 3), f'Line {line}' if line else 'Not recorded', 'CPHL-DERIVED')
    add('NNRTI-based regimen (EFV/NVP)', 3, drugs & {'EFV', 'NVP'}, '-'.join(sorted(drugs)) or 'Not recorded', 'LIT-NNRTI')
    add('Child under 10 years', 3, age is not None and age < 10, 'Not recorded' if age is None else f'{age:.0f} years', 'LIT-AGE')
    add('Adolescent 10–19 years', 1, age is not None and 10 <= age < 20, 'Not recorded' if age is None else f'{age:.0f} years', 'LIT-AGE')
    start = parse_date(raw.get('Treatment Initiation Date'))
    years = ((latest['date'] if latest else parse_date(raw.get('Sample collection Date'))) - start).days / 365.25 if start and (latest or raw.get('Sample collection Date')) else None
    add('On ART 5 years or more', 1, years is not None and years >= 5, 'Not recorded' if years is None else f'{years:.1f} years', 'LIT-DURATION')
    streak = 0
    for o in reversed(timeline):
        if nonsuppressed(o):
            streak += 1
        else:
            break
    add('Three or more consecutive VL ≥1000', 1, streak >= 3, f'{streak} consecutive', 'LIT-DURATION')
    exposed = str(raw.get('exposure_to_AZT_and_ABC') or '').strip().lower() in ('yes', '1', 'true')
    add('Previously exposed to both AZT and ABC', 1, exposed, 'Yes' if exposed else 'Not recorded / no', 'CPHL-DERIVED')
    # The VL >=1000 gate is applied before scoring (only non-suppressed patients are scored).
    # A separate point by VL size was tested and removed: within VL >=1000 it added almost nothing (AUROC 0.714 vs 0.710).

    # guideline-based modifiers (not validated against outcomes)
    repeat_ns = latest is not None and nonsuppressed(latest) and streak >= 2
    good = [s for s in sessions if s.get('adherence_pct') is not None]
    good_streak = 0
    for s in reversed(good):
        if GOOD_ADHERENCE <= s['adherence_pct'] <= 105:
            good_streak += 1
        else:
            break
    add('Still ≥1000 after 3 good IAC sessions', 2, repeat_ns and good_streak >= 3,
        f'{good_streak} consecutive good session(s)', 'MOH-161', validated=False)
    drop = (eligibility.get('log_drop') or {}).get('value')
    add('Less than 1-log drop after IAC', 1, repeat_ns and drop is not None and drop < 1,
        'Not available' if drop is None else f'{drop:.2f} log', 'MOH-2.4', validated=False)
    poor = good[-1]['adherence_pct'] < 85 if good else False
    add('Poor adherence on an NNRTI regimen', 1, poor and bool(drugs & {'EFV', 'NVP'}),
        'Not recorded' if not good else f"{good[-1]['adherence_pct']:.0f}%", 'MOH-NNRTI', validated=False)

    data_points = sum(f['points'] for f in factors if f['validated'])
    clinical_points = sum(f['points'] for f in factors if not f['validated'])
    total = data_points + clinical_points
    category = _band(total)
    missing = [k for k, v in known.items() if not v]
    nonsupp = latest is not None and nonsuppressed(latest)
    if not nonsupp:
        flag, reason = False, 'Latest viral load is below 1000 copies/mL: risk scoring applies to non-suppressed patients.'
    else:
        flag = category == 'High'
        reason = f"{category} risk ({total} points; about {OBSERVED[category]}% of similar tested patients had resistance)."
        reason += ' DR test: ' + (eligibility.get('label') or 'not assessed') + '. ' + (eligibility.get('next_step') or '')
    ml = None
    try:
        from .ml_service import predict
        ml = predict(raw, patient)
    except Exception:  # the model is advisory; scoring must not fail because of it
        ml = {'available': False, 'reason': 'Model could not be run'}
    if nonsupp and ml and ml.get('available'):
        pct = round(ml['probability'] * 100)
        reason += f" Machine-learning estimate: {pct}%" + (' (above the research threshold).' if ml['above_research_threshold'] else '.')
    return {'version': SCORE_VERSION, 'ml': ml, 'total': total, 'data_points': data_points, 'clinical_points': clinical_points,
            'category': category if nonsupp else 'Not applicable', 'flagged': flag, 'reason': reason.strip(),
            'factors': factors, 'missing_inputs': missing, 'observed_rate': OBSERVED.get(category) if nonsupp else None,
            'bands': [{'from': lo, 'to': hi, 'label': label, 'observed_rate': OBSERVED[label]} for lo, hi, label in BANDS],
            'sources': SOURCES,
            'notice': 'Prioritisation only. DR-test eligibility follows MoH/WHO criteria; the decision rests with the clinician.'}
