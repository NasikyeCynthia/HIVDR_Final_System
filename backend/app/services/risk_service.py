def score(patient):
    vl, adherence, line = patient.get('viral_load'), patient.get('adherence'), patient.get('treatment_line')
    points = [None if vl is None else 60 if vl >= 1000 else 30 if vl >= 200 else 0,
              None if adherence is None else 60 if adherence < 85 else 30 if adherence < 100 else 0,
              {1: 0, 2: 30, 3: 60}.get(line)]
    complete = all(value is not None for value in points)
    total = sum(points) if complete else None
    known_total=sum(value or 0 for value in points)
    category = 'High' if known_total >= 60 else ('Intermediate' if total >= 30 else 'Low') if complete else 'Incomplete'
    return {'total': total, 'known_total': known_total, 'complete': complete, 'category': category, 'eligible': category == 'High',
            'version': 'prototype-2.1', 'matches': [category],
            'notice': 'Prototype prioritisation: 0 low; 30 intermediate; 60–180 high. A known score >=60 flags high risk even if another input is missing. Clinical validation pending.',
            'factors': [{'name': name, 'value': value, 'points': point} for name,value,point in zip(['Viral load','Adherence','Treatment line'],[vl,adherence,line],points)]}
