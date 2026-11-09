def score(patient):
    vl, adherence, line = (patient.get('viral_load'), patient.get('adherence'), patient.get('treatment_line'))
    factors = [{'name': 'Viral load', 'value': vl, 'points': None if vl is None else 60 if vl >= 1000 else 30 if vl >= 200 else 0}, {'name': 'Adherence', 'value': adherence, 'points': None if adherence is None else 60 if adherence < 85 else 30 if adherence < 100 else 0}, {'name': 'Treatment line', 'value': line, 'points': {1: 0, 2: 30, 3: 60}.get(line)}]
    complete = all((f['points'] is not None for f in factors))
    total = sum((f['points'] or 0 for f in factors)) if complete else None
    matches = []
    if total is not None:
        if total > 60:
            matches.append('High')
        if 31 <= total <= 59:
            matches.append('Moderate')
        if total >= 30:
            matches.append('Low')
    category = 'Rule unresolved' if complete else 'Incomplete'
    return {'total': total, 'factors': factors, 'category': category, 'matches': matches, 'eligible': category == 'High', 'version': 'user-rules-1', 'notice': 'Overall ranges need clarification: high >60; moderate 31–59; low ≥30. Overlaps are not resolved automatically.'}
