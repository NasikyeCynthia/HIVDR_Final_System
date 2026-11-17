"""Versioned pre-sample treatment and dated VL history features.

No mutation, resistance, referral outcome, decision or post-sample observation is used.
Used by the active history-v2 research estimate and its training pipeline.
"""
import math
import re
from .ml_features import NUMERIC as BASE_NUMERIC, CATEGORICAL, extract as base_extract, date, number

DRUGS=['DTG','BIC','CAB','RAL','LPV','ATV','DRV','EFV','NVP','DOR','ETR','TDF','TAF','AZT','ABC','3TC','FTC']
NUMERIC=BASE_NUMERIC+['current_regimen_years','prior_gap_years','prior_log_max','prior_log_mean',
                     'prior_nonsuppressed_fraction','log_vl_change','consecutive_prior_nonsuppressed',
                     'ongoing_nonsuppression_years']+['on_'+d for d in DRUGS]

def extract(raw,patient=None):
    sample=date(raw.get('Sample collection Date'))
    context=dict(patient or {})
    if sample:
        # Retrospective cases must use the indexed sample context, not a later
        # follow-up VL or a regimen started after the committee decision.
        columns={'viral_load':'VL Leading to DR','age':'Age(yrs)','sex':'sex',
                 'treatment_line':'Treatment Line at Sample collection',
                 'regimen':'ART at sample collection(ART@VL@DR)'}
        for field,column in columns.items():
            if column in raw:context[field]=raw[column]
    f=base_extract(raw,context)
    start=date(raw.get('ART@VL@DR start date'))
    years=(sample-start).days/365.25 if sample and start and start<=sample else None
    f['current_regimen_years']=years if years is None or years<=70 else None
    prior=[]
    for i in range(1,11):
        d=date(raw.get(f'VL_{i}_Prior_To_DR_TestDate') or raw.get(f'vl_{i}_Prior_To_DR_TestDate'))
        value=number(raw.get(f'vl_{i}_Prior_To_DR'))
        if sample and d and d<=sample and value is not None:prior.append((d,value))
    # Same-day duplicate observations do not inflate the consecutive-observation count.
    prior=sorted(set(prior),reverse=True)
    logs=[math.log1p(v) for _,v in prior]
    f['prior_gap_years']=(sample-prior[0][0]).days/365.25 if prior else None
    f['prior_log_max']=max(logs) if logs else None
    f['prior_log_mean']=sum(logs)/len(logs) if logs else None
    f['prior_nonsuppressed_fraction']=sum(v>=1000 for _,v in prior)/len(prior) if prior else None
    f['log_vl_change']=f['log_viral_load']-logs[0] if logs and f['log_viral_load'] is not None else None
    streak=[]
    for d,v in prior:
        if v<1000:break
        streak.append(d)
    f['consecutive_prior_nonsuppressed']=len(streak) if prior else None
    f['ongoing_nonsuppression_years']=(sample-streak[-1]).days/365.25 if streak and f['log_viral_load'] is not None and f['log_viral_load']>=math.log1p(1000) else None
    regimen=f['regimen'].replace('/R','')
    tokens={('AZT' if d=='ZDV' else d) for d in re.split(r'[-+/,\s]+',regimen) if d}
    for drug in DRUGS:f['on_'+drug]=int(drug in tokens) if tokens else None
    return f

def transform(features,spec):
    values=[]
    for name,s in spec['numeric'].items():
        value=features.get(name)
        values.extend([((s['median'] if value is None else value)-s['mean'])/s['scale'],int(value is None)])
    for name,categories in spec['categorical'].items():
        value=features.get(name) or '__MISSING__'
        if value not in categories:value='__OTHER__'
        values.extend(int(value==c) for c in categories)
    return values
