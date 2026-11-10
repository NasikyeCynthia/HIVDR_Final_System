"""Shared pre-DRT feature extraction. No mutation, resistance or decision inputs."""
import math
import re
from datetime import datetime

NUMERIC=['log_viral_load','age','treatment_line','art_years_at_sample','log_prior_vl','prior_vl_count']
CATEGORICAL=['sex','regimen']
def number(value):
    if value is None:return None
    text=str(value).strip().replace(',','')
    if text.lower() in ('','unknown','none','not applicable','left blank'):return None
    match=re.search(r'[-+]?\d+(?:\.\d+)?',text)
    if not match:return None
    value=float(match.group())
    return value if math.isfinite(value) and value>=0 else None
def date(value):
    text=str(value or '').split(' ')[0]
    for fmt in ('%d/%m/%Y','%Y-%m-%d'):
        try:return datetime.strptime(text,fmt)
        except ValueError:pass
    return None
def line(value):
    text=str(value or '').lower()
    for n,word in ((1,'first'),(2,'second'),(3,'third')):
        if word in text or text==str(n):return n
    return None
def extract(raw,patient=None):
    patient=patient or {}
    vl=number(patient.get('viral_load',raw.get('VL Leading to DR')))
    age=number(patient.get('age',raw.get('Age(yrs)')))
    treatment=line(patient.get('treatment_line',raw.get('Treatment Line at Sample collection')))
    sample=date(raw.get('Sample collection Date'))
    start=date(raw.get('Treatment Initiation Date'))
    duration=(sample-start).days/365.25 if sample and start and sample>=start else None
    prior=[]
    for i in range(1,11):
        d=date(raw.get(f'VL_{i}_Prior_To_DR_TestDate') or raw.get(f'vl_{i}_Prior_To_DR_TestDate'))
        value=number(raw.get(f'vl_{i}_Prior_To_DR'))
        if sample and d and d<=sample and value is not None:prior.append((d,value))
    prior.sort(reverse=True)
    regimen=str(patient.get('regimen',raw.get('ART at sample collection(ART@VL@DR)','')) or '').upper().replace(' ','').replace('+','-')
    return {'log_viral_load':math.log1p(vl) if vl is not None else None,'age':age if age is None or age<=120 else None,
            'treatment_line':treatment,'art_years_at_sample':duration if duration is None or duration<=70 else None,
            'log_prior_vl':math.log1p(prior[0][1]) if prior else None,'prior_vl_count':len(prior),
            'sex':str(patient.get('sex',raw.get('sex','')) or '').upper(),'regimen':regimen}
def transform(features,spec):
    values=[]
    for name in NUMERIC:
        s=spec['numeric'][name];value=features.get(name)
        values.extend([((s['median'] if value is None else value)-s['mean'])/s['scale'],int(value is None)])
    for name in CATEGORICAL:
        categories=spec['categorical'][name];value=features.get(name) or '__MISSING__'
        if value not in categories:value='__OTHER__'
        values.extend(int(value==c) for c in categories)
    return values
