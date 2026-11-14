"""Audit a frozen artifact on its original facility-held-out test set; never refit.

Run from backend: python ml/validate_model.py ORIGINAL.csv --output ml/artifacts/validation.json
Only aggregate metrics are exported. A dataset hash or split mismatch aborts the audit.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ml_features import extract
from app.services.ml_service import predict_artifact

PANEL = ['BIC','CAB','DTG','RAL','3TC','ABC','AZT','TDF','DOR','EFV','ETR','NVP']
VALID = {'Susceptible','Potential Low-Level Resistance','Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
POSITIVE = {'Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}

def divide(a,b):
    return float(a/b) if b else None

def measures(y,p,threshold):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float);pred=p>=threshold
    tp=int(np.sum(pred & (y==1)));tn=int(np.sum(~pred & (y==0)))
    fp=int(np.sum(pred & (y==0)));fn=int(np.sum(~pred & (y==1)))
    sensitivity=divide(tp,tp+fn);specificity=divide(tn,tn+fp)
    return {'roc_auc':float(roc_auc_score(y,p)) if len(set(y))==2 else None,
            'average_precision':float(average_precision_score(y,p)) if np.any(y) else None,
            'accuracy':divide(tp+tn,len(y)),
            'balanced_accuracy':(sensitivity+specificity)/2 if sensitivity is not None and specificity is not None else None,
            'sensitivity':sensitivity,'specificity':specificity,'precision':divide(tp,tp+fp),
            'negative_predictive_value':divide(tn,tn+fn),'brier_score':float(np.mean((p-y)**2)),
            'confusion_matrix':{'tn':tn,'fp':fp,'fn':fn,'tp':tp}}

def calibration_bins(y,p):
    bins=[]
    for i in range(10):
        lower=i/10;upper=(i+1)/10
        mask=(p>=lower)&((p<=upper) if i==9 else (p<upper))
        if not np.any(mask):continue
        bins.append({'lower':lower,'upper':upper,'n':int(mask.sum()),
                     'mean_probability':float(p[mask].mean()),'observed_rate':float(y[mask].mean())})
    return bins

def cluster_bootstrap(y,p,groups,threshold,replicates,seed=2026):
    rng=np.random.default_rng(seed)
    unique=np.unique(groups)
    indices=[np.flatnonzero(groups==g) for g in unique]
    samples={k:[] for k in ('roc_auc','sensitivity','specificity','brier_score')}
    for _ in range(replicates):
        take=np.concatenate([indices[i] for i in rng.integers(0,len(indices),len(indices))])
        m=measures(y[take],p[take],threshold)
        for key in samples:
            if m[key] is not None:samples[key].append(m[key])
    return {'method':'Facility-cluster percentile bootstrap','replicates':replicates,'seed':seed,
            'intervals':{k:[float(v) for v in np.percentile(values,[2.5,97.5])] for k,values in samples.items() if values},
            'valid_replicates':{k:len(v) for k,v in samples.items()}}

def subgroup_results(features,y,p,threshold):
    definitions={
        'Age under 15':lambda f:f['age'] is not None and f['age']<15,
        'Age 15–19':lambda f:f['age'] is not None and 15<=f['age']<20,
        'Age 20+':lambda f:f['age'] is not None and f['age']>=20,
        'Age missing':lambda f:f['age'] is None,
        **{f'Treatment line {n}':lambda f,n=n:f['treatment_line']==n for n in (1,2,3)},
        **{f'Sex {sex}':lambda f,sex=sex:f['sex']==sex for sex in ('F','M')},
        'TDF-3TC-DTG':lambda f:f['regimen']=='TDF-3TC-DTG',
        'Other / missing regimen':lambda f:f['regimen']!='TDF-3TC-DTG'}
    result=[]
    for name,test in definitions.items():
        mask=np.array([test(f) for f in features],dtype=bool);n=int(mask.sum())
        positives=int(y[mask].sum());suppressed=n<30 or positives<10 or n-positives<10
        result.append({'group':name,'n':n,'suppressed':suppressed,
                       'metrics':None if suppressed else measures(y[mask],p[mask],threshold)})
    return result

def audit(csv_path,artifact_path,replicates=500):
    data_hash=hashlib.sha256(csv_path.read_bytes()).hexdigest()
    model_hash=hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    artifact=json.loads(artifact_path.read_text());meta=artifact['metadata']
    if data_hash!=meta['data_sha256']:raise ValueError('Dataset hash differs from the original model training input.')
    rows=list(csv.DictReader(csv_path.open(encoding='utf-8-sig',newline='')))
    cohort=[r for r in rows if r.get('amplified')=='1' and all(r.get('Resistance to '+d) in VALID for d in PANEL)]
    seen=set();features=[];labels=[];groups=[]
    for r in cohort:
        f=extract(r);label=int(any(r['Resistance to '+d] in POSITIVE for d in PANEL))
        key=(r['Facility'],r.get('Date of Birth'),r.get('Treatment Initiation Date'),json.dumps(f,sort_keys=True),label)
        if key in seen:continue
        seen.add(key);features.append(f);labels.append(label);groups.append(r['Facility'])
    y=np.array(labels);groups=np.array(groups)
    fit,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(features,y,groups))
    train,valid=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(fit,y[fit],groups[fit]));train=fit[train];valid=fit[valid]
    if set(groups[train])&set(groups[test]) or set(groups[valid])&set(groups[test]) or set(groups[train])&set(groups[valid]):raise ValueError('Facility overlap.')
    for name,index in [('train',train),('validation',valid),('test',test)]:
        expected=meta['split'][name]
        if len(index)!=expected['rows'] or len(set(groups[index]))!=expected['facilities'] or abs(y[index].mean()-expected['positive_rate'])>1e-12:raise ValueError('Original split could not be reproduced.')
    if len(rows)!=meta['original_rows'] or len(cohort)!=meta['complete_panel_rows'] or len(features)!=meta['training_eligible_rows']:raise ValueError('Cohort count mismatch.')
    test_features=[features[i] for i in test]
    p=np.array([predict_artifact(artifact,f) for f in test_features]);yt=y[test];threshold=meta['threshold']
    metrics=measures(yt,p,threshold)
    for k,v in meta['held_out_test'].items():
        if k=='confusion_matrix':
            if metrics[k]!=v:raise ValueError('Saved confusion matrix mismatch.')
        elif abs(metrics[k]-v)>1e-8:raise ValueError('Saved test metric mismatch: '+k)
    prevalence=float(y[train].mean());majority=int(prevalence>=.5)
    return {'schema_version':1,'evaluated_at':datetime.now(timezone.utc).isoformat(),
            'model_sha256':model_hash,'data_sha256':data_hash,'model_version':meta['version'],
            'protocol':'Frozen model; original facility-held-out split; no fitting or threshold selection on test data.',
            'test_rows':len(test),'test_facilities':len(set(groups[test])),'threshold':threshold,'metrics':metrics,
            'bootstrap':cluster_bootstrap(yt,p,groups[test],threshold,replicates),
            'calibration':calibration_bins(yt,p),
            'subgroups':subgroup_results(test_features,yt,p,threshold),
            'baselines':{'training_prevalence':prevalence,'training_prevalence_brier':float(np.mean((prevalence-yt)**2)),
                         'majority_accuracy':float(np.mean(yt==majority))},
            'limitations':['Retrospective internal validation; not prospective or independent external validation.',
                           'Intervals condition on the fitted model and this selected test cohort, not the entire training procedure.',
                           'Subgroups are descriptive, overlap, and do not establish fairness; groups with <30 records or <10 of either outcome are suppressed.',
                           'Validation data were reused for candidate selection, calibration and cutoff selection. No refitting or model promotion was performed.',
                           'Stable patient identifiers were unavailable; transfers across facilities cannot be excluded.']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv',type=Path);parser.add_argument('--model',type=Path,default=Path(__file__).parent/'artifacts/model.json')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--bootstrap',type=int,default=500)
    args=parser.parse_args()
    if args.bootstrap<100:parser.error('Use at least 100 bootstrap replicates.')
    if args.output.resolve() in (args.csv.resolve(),args.model.resolve()):parser.error('Output must not overwrite inputs.')
    report=audit(args.csv,args.model,args.bootstrap)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'test_rows':report['test_rows'],'metrics':report['metrics'],'bootstrap':report['bootstrap']},indent=2))

if __name__=='__main__':main()
