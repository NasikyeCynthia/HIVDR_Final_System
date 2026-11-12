"""Risk of drug resistance — the project's original points algorithm (prototype 2.1).

  Viral load:      >=1000 copies/mL = 60, 200–999 = 30, <200 = 0
  Adherence:       <85% = 60, 85–99% = 30, 100% = 0   (latest IAC pill count)
  Treatment line:  third = 60, second = 30, first = 0
  Category:        High if the known points reach 60 (even if another input is missing);
                   otherwise Intermediate (30–59) or Low (0) once all three are known;
                   Incomplete if inputs are missing and the known points are below 60.

High risk is flagged together with the DR-test eligibility status (MoH/WHO criteria in
eligibility_service.py), which remains the gate for requesting a test. The machine-learning
estimate is attached as a second, research-only opinion.

An evidence-derived alternative is kept, unused, in evidence_risk_service.py.
"""
SCORE_VERSION = 'prototype-2.1-ug.2'
BANDS = [{'from': 0, 'to': 0, 'label': 'Low'}, {'from': 30, 'to': 59, 'label': 'Intermediate'},
         {'from': 60, 'to': 180, 'label': 'High'}]


def _points(patient):
    vl, adherence, line = patient.get('viral_load'), patient.get('adherence'), patient.get('treatment_line')
    return [
        {'name': 'Viral load (copies/mL)', 'value': vl, 'max': 60,
         'points': None if vl is None else 60 if vl >= 1000 else 30 if vl >= 200 else 0,
         'rule': '≥1000 → 60 · 200–999 → 30 · <200 → 0'},
        {'name': 'Adherence (%)', 'value': adherence, 'max': 60,
         'points': None if adherence is None else 60 if adherence < 85 else 30 if adherence < 100 else 0,
         'rule': '<85 → 60 · 85–99 → 30 · 100 → 0'},
        {'name': 'Treatment line', 'value': line, 'max': 60,
         'points': {1: 0, 2: 30, 3: 60}.get(line),
         'rule': 'Third → 60 · Second → 30 · First → 0'},
    ]


def score(patient, raw=None, sessions=(), eligibility=None):
    eligibility = eligibility or {}
    factors = _points(patient)
    points = [f['points'] for f in factors]
    complete = all(p is not None for p in points)
    known_total = sum(p or 0 for p in points)
    total = known_total if complete else None
    if known_total >= 60:
        category = 'High'
    elif complete:
        category = 'Intermediate' if known_total >= 30 else 'Low'
    else:
        category = 'Incomplete'
    missing = [f['name'] for f in factors if f['points'] is None]
    drivers = [f"{f['name'].split(' (')[0].lower()} {f['points']}" for f in factors if f['points']]
    reason = f"{category} risk ({known_total} points{': ' + ', '.join(drivers) if drivers else ''})."
    if missing:
        reason += ' Missing: ' + ', '.join(missing) + '.'
    if eligibility:
        reason += ' DR test: ' + (eligibility.get('label') or '') + '. ' + (eligibility.get('next_step') or '')
    ml = None
    if raw is not None:
        try:
            from .ml_service import predict
            ml = predict(raw, patient)
        except Exception:
            ml = {'available': False, 'reason': 'Model could not be run'}
    return {'version': SCORE_VERSION, 'total': total, 'known_total': known_total, 'complete': complete,
            'category': category, 'flagged': category == 'High', 'reason': reason.strip(), 'factors': factors,
            'missing_inputs': missing, 'bands': BANDS, 'ml': ml,
            'notice': 'Prototype prioritisation; clinical validation pending. DR-test eligibility follows the MoH/WHO '
                      'criteria and the decision rests with the clinician.'}
