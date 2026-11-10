"""Train on the original CSV only. Run from backend; exports portable JSON, not patient rows."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import sys
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,accuracy_score,balanced_accuracy_score,confusion_matrix,brier_score_loss
from sklearn.model_selection import GroupShuffleSplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.ml_features import NUMERIC,CATEGORICAL,extract,transform

PANEL=['BIC','CAB','DTG','RAL','3TC','ABC','AZT','TDF','DOR','EFV','ETR','NVP']
VALID={'Susceptible','Potential Low-Level Resistance','Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
POSITIVE={'Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}

def metrics(y,p,threshold):
    predicted=p>=threshold;tn,fp,fn,tp=confusion_matrix(y,predicted,labels=[0,1]).ravel()
    return {'roc_auc':float(roc_auc_score(y,p)),'average_precision':float(average_precision_score(y,p)),
      'accuracy':float(accuracy_score(y,predicted)),'balanced_accuracy':float(balanced_accuracy_score(y,predicted)),
      'sensitivity':float(tp/(tp+fn)),'specificity':float(tn/(tn+fp)),'brier_score':float(brier_score_loss(y,p)),
      'confusion_matrix':{'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('csv');parser.add_argument('--output',default='ml/artifacts');args=parser.parse_args()
    path=Path(args.csv);rows=list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
    cohort=[r for r in rows if r.get('amplified')=='1' and all(r.get('Resistance to '+d) in VALID for d in PANEL)]
    # Remove repeated snapshots with the same facility, dated demographics, input features and target.
    seen=set();features=[];labels=[];groups=[]
    for r in cohort:
        f=extract(r);label=int(any(r['Resistance to '+d] in POSITIVE for d in PANEL))
        key=(r['Facility'],r.get('Date of Birth'),r.get('Treatment Initiation Date'),json.dumps(f,sort_keys=True),label)
        if key in seen:continue
        seen.add(key);features.append(f);labels.append(label);groups.append(r['Facility'])
    labels=np.array(labels);groups=np.array(groups)
    fit,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(features,labels,groups))
    train,valid=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(fit,labels[fit],groups[fit]));train=fit[train];valid=fit[valid]
    assert not (set(groups[train])&set(groups[valid]) or set(groups[train])&set(groups[test]) or set(groups[valid])&set(groups[test]))
    spec={'numeric':{},'categorical':{}}
    for name in NUMERIC:
        observed=[features[i][name] for i in train if features[i][name] is not None]
        median=float(np.median(observed)) if observed else 0.
        filled=np.array([features[i][name] if features[i][name] is not None else median for i in train])
        spec['numeric'][name]={'median':median,'mean':float(filled.mean()),'scale':float(filled.std()) or 1.}
    for name in CATEGORICAL:
        counts=Counter(features[i][name] or '__MISSING__' for i in train)
        spec['categorical'][name]=sorted({v for v,n in counts.items() if n>=20}|{'__OTHER__','__MISSING__'})
    x=np.array([transform(f,spec) for f in features])
    models={'Logistic regression':LogisticRegression(max_iter=1500,class_weight='balanced',random_state=42),
            'Random forest':RandomForestClassifier(n_estimators=160,max_depth=10,min_samples_leaf=15,class_weight='balanced',n_jobs=2,random_state=42)}
    results={}
    for name,model in models.items():
        model.fit(x[train],labels[train]);prediction=model.predict_proba(x[valid])[:,1]
        results[name]={'validation_roc_auc':float(roc_auc_score(labels[valid],prediction))}
    selected=max(results,key=lambda n:results[n]['validation_roc_auc']);model=models[selected]
    def logits(p):return np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    calibration=LogisticRegression().fit(logits(model.predict_proba(x[valid])[:,1]).reshape(-1,1),labels[valid])
    val_p=calibration.predict_proba(logits(model.predict_proba(x[valid])[:,1]).reshape(-1,1))[:,1]
    threshold=float(max(np.arange(.1,.91,.01),key=lambda t:balanced_accuracy_score(labels[valid],val_p>=t)))
    probabilities=calibration.predict_proba(logits(model.predict_proba(x[test])[:,1]).reshape(-1,1))[:,1]
    feature_names=[]
    for name in NUMERIC:feature_names.extend([name,name+'_missing'])
    for name in CATEGORICAL:feature_names.extend(name+'='+v for v in spec['categorical'][name])
    if selected=='Random forest':
        artifact={'kind':'forest','trees':[{'left':t.tree_.children_left.tolist(),'right':t.tree_.children_right.tolist(),
            'feature':t.tree_.feature.tolist(),'threshold':t.tree_.threshold.tolist(),
            'positive_probability':[(float(v[0][1])/float(sum(v[0]))) for v in t.tree_.value]} for t in model.estimators_]}
        importance=model.feature_importances_
    else:
        artifact={'kind':'logistic','coefficients':model.coef_[0].tolist(),'intercept':float(model.intercept_[0])};importance=np.abs(model.coef_[0])
    report={'version':'hivdr-panel-v1','trained_at':datetime.now(timezone.utc).isoformat(),'selected_model':selected,
      'target':'Any low-level-or-greater resistance across the fully observed 12-drug RT/IN panel',
      'panel':PANEL,'original_rows':len(rows),'complete_panel_rows':len(cohort),'training_eligible_rows':len(features),
      'split':{name:{'rows':len(index),'facilities':len(set(groups[index])),'positive_rate':float(labels[index].mean())} for name,index in [('train',train),('validation',valid),('test',test)]},
      'threshold':threshold,'model_comparison':results,'held_out_test':metrics(labels[test],probabilities,threshold),
      'top_global_features':sorted([{'feature':n,'importance':float(v)} for n,v in zip(feature_names,importance)],key=lambda x:-x['importance'])[:12],
      'limitations':['Retrospective referred-and-tested cohort; cannot establish performance in untested low-risk patients.',
       'Facility-disjoint evaluation reduces repeated-record leakage; stable person identifiers were unavailable, so transfers across facilities cannot be excluded.',
       'Adherence is absent from original data and is not an ML input. Psychosocial, mutations, resistance fields, decisions and post-DRT outcomes are excluded as inputs.',
       'Prior viral loads require a dated observation on or before the index sample. ART duration is derived at that sample date.',
       'Outcome requires all 12 panel results and excludes PI-only resistance. Potential low-level resistance is below the binary target threshold.',
       'Not prospectively validated. Estimates support a research demonstration; they do not confirm resistance or determine treatment/referral.'],
      'data_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    artifact.update({'preprocessing':spec,'feature_names':feature_names,'calibration':{'coefficient':float(calibration.coef_[0][0]),'intercept':float(calibration.intercept_[0])},'metadata':report})
    (output/'model.json').write_text(json.dumps(artifact,separators=(',',':')))
    (output/'metrics.json').write_text(json.dumps(report,indent=2))
    # Independent portable inference must agree with the trained estimator before export is accepted.
    from app.services.ml_service import predict_artifact
    portable=np.array([predict_artifact(artifact,features[i]) for i in test])
    assert np.max(np.abs(portable-probabilities))<1e-8
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
