"""Reproducible development-only model selection; separate calibration/cutoff facilities.

The original test has already been examined. It is a legacy comparison, not a new
independent validation. This command writes a candidate directory, never deploys it.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.ml_features import NUMERIC,CATEGORICAL,extract,transform
from app.services.ml_service import predict_artifact, sigmoid
from ml.validate_model import PANEL,VALID,POSITIVE,measures,calibration_bins,subgroup_results,cluster_bootstrap

PROTOCOL = {
    'version':'hivdr-retraining-v2.1',
    'selection':'Highest mean 4-fold facility-grouped training AUROC; fixed candidate grid.',
    'calibration':'Logistic calibration fitted on independent calibration facilities only.',
    'cutoff':'Maximise balanced accuracy on separate cutoff facilities; ties prefer higher sensitivity.',
    'evaluation':'One legacy-test comparison after selection; previously examined, not independent external validation.',
    'promotion':'Candidate only. No automated replacement of the deployed artifact.',
    'seed':20261114,
}

def candidates():
    return {
        'Logistic regression':LogisticRegression(max_iter=1500,class_weight='balanced',random_state=42),
        'Random forest original configuration':RandomForestClassifier(n_estimators=160,max_depth=10,min_samples_leaf=15,class_weight='balanced',n_jobs=2,random_state=42),
        'Random forest deeper':RandomForestClassifier(n_estimators=300,max_depth=12,min_samples_leaf=8,class_weight='balanced',n_jobs=2,random_state=42),
        'Random forest regularised':RandomForestClassifier(n_estimators=300,max_depth=8,min_samples_leaf=25,n_jobs=2,random_state=42),
        'Extra trees':ExtraTreesClassifier(n_estimators=300,max_depth=12,min_samples_leaf=8,class_weight='balanced',n_jobs=2,random_state=42),
        'Gradient boosting depth 2':GradientBoostingClassifier(n_estimators=200,learning_rate=.05,max_depth=2,min_samples_leaf=20,random_state=42),
        'Gradient boosting depth 3':GradientBoostingClassifier(n_estimators=200,learning_rate=.05,max_depth=3,min_samples_leaf=20,random_state=42),
    }

def preprocessing(features,index):
    spec={'numeric':{},'categorical':{}}
    for name in NUMERIC:
        observed=[features[i][name] for i in index if features[i][name] is not None]
        median=float(np.median(observed)) if observed else 0.
        filled=np.array([features[i][name] if features[i][name] is not None else median for i in index])
        spec['numeric'][name]={'median':median,'mean':float(filled.mean()),'scale':float(filled.std()) or 1.}
    for name in CATEGORICAL:
        counts=Counter(features[i][name] or '__MISSING__' for i in index)
        spec['categorical'][name]=sorted({v for v,n in counts.items() if n>=20}|{'__OTHER__','__MISSING__'})
    return spec

def prepare_cohort(path,metadata):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=metadata['data_sha256']:raise ValueError('Original training CSV hash mismatch.')
    with path.open(encoding='utf-8-sig',newline='') as file:rows=list(csv.DictReader(file))
    cohort=[r for r in rows if r.get('amplified')=='1' and all(r.get('Resistance to '+d) in VALID for d in PANEL)]
    seen=set();features=[];labels=[];groups=[]
    for r in cohort:
        from app.services.ml_features import extract as original_extract
        original=original_extract(r)
        f=extract(r);label=int(any(r['Resistance to '+d] in POSITIVE for d in PANEL))
        key=(r['Facility'],r.get('Date of Birth'),r.get('Treatment Initiation Date'),json.dumps(original,sort_keys=True),label)
        if key in seen:continue
        seen.add(key);features.append(f);labels.append(label);groups.append(r['Facility'])
    if len(features)!=metadata['training_eligible_rows']:raise ValueError('Cohort mismatch.')
    return features,np.array(labels),np.array(groups),digest

def disjoint(groups,partitions):
    sets=[set(groups[index]) for index in partitions]
    if any(a&b for i,a in enumerate(sets) for b in sets[i+1:]):raise ValueError('Facility leakage between partitions.')

def split_cohort(features,y,groups,metadata):
    fit,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(features,y,groups))
    train,valid=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(fit,y[fit],groups[fit]));train=fit[train];valid=fit[valid]
    for name,index in [('train',train),('validation',valid),('test',test)]:
        expected=metadata['split'][name]
        if len(index)!=expected['rows'] or len(set(groups[index]))!=expected['facilities'] or abs(y[index].mean()-expected['positive_rate'])>1e-12:raise ValueError('Original split mismatch.')
    cal,cutoff=next(GroupShuffleSplit(n_splits=1,test_size=.5,random_state=PROTOCOL['seed']).split(valid,y[valid],groups[valid]));cal=valid[cal];cutoff=valid[cutoff]
    disjoint(groups,[train,cal,cutoff,test])
    for index in (train,cal,cutoff,test):
        if len(set(y[index]))!=2:raise ValueError('Each partition must contain both outcomes.')
    return train,cal,cutoff,test

def logits(p):
    p=np.clip(p,1e-6,1-1e-6)
    return np.log(p/(1-p))

def choose_cutoff(y,p):
    choices=[]
    for t in np.arange(10,91)/100:
        m=measures(y,p,float(t))
        choices.append((m['balanced_accuracy'],m['sensitivity'],float(t)))
    return max(choices)[2]

def export_model(model,spec):
    if isinstance(model,LogisticRegression):
        return {'kind':'logistic','coefficients':model.coef_[0].tolist(),'intercept':float(model.intercept_[0]),'preprocessing':spec}
    boosting=isinstance(model,GradientBoostingClassifier)
    estimators=model.estimators_.ravel() if boosting else model.estimators_
    trees=[]
    for estimator in estimators:
        t=estimator.tree_
        tree={'left':t.children_left.tolist(),'right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist()}
        if boosting:tree['value']=t.value[:,0,0].tolist()
        else:tree['positive_probability']=[float(v[0][1])/float(sum(v[0])) for v in t.value]
        trees.append(tree)
    result={'kind':'gradient_boosting' if boosting else 'forest','trees':trees,'preprocessing':spec}
    if boosting:
        prior=float(model.init_.class_prior_[1])
        result.update(base_log_odds=float(np.log(prior/(1-prior))),learning_rate=float(model.learning_rate))
    return result

def candidate_predict(artifact,features):
    from ml.history_features import transform as transform_spec
    x=transform_spec(features,artifact['preprocessing'])
    if artifact['kind']=='logistic':
        raw=artifact['intercept']+sum(a*b for a,b in zip(x,artifact['coefficients']))
        probability=sigmoid(raw)
    else:
        x=np.asarray(x,dtype=np.float32).tolist();values=[]
        boosting=artifact['kind']=='gradient_boosting'
        for tree in artifact['trees']:
            node=0
            while tree['left'][node]!=-1:
                node=tree['left'][node] if x[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
            values.append(tree['value'][node] if boosting else tree['positive_probability'][node])
        probability=sigmoid(artifact['base_log_odds']+artifact['learning_rate']*sum(values)) if boosting else sum(values)/len(values)
    p=np.clip(probability,1e-6,1-1e-6);c=artifact['calibration']
    return sigmoid(c['intercept']+c['coefficient']*float(np.log(p/(1-p))))


def paired_intervals(y,current,new,groups,replicates=500):
    rng=np.random.default_rng(PROTOCOL['seed']);unique=np.unique(groups);indices=[np.flatnonzero(groups==g) for g in unique]
    deltas=[]
    for _ in range(replicates):
        take=np.concatenate([indices[i] for i in rng.integers(0,len(indices),len(indices))])
        if len(set(y[take]))<2:continue
        deltas.append(float(roc_auc_score(y[take],new[take])-roc_auc_score(y[take],current[take])))
    return {'method':'Paired facility-cluster percentile bootstrap','replicates':replicates,
            'auroc_difference_95_interval':[float(v) for v in np.percentile(deltas,[2.5,97.5])],
            'note':'Conditions on the selected models and reused legacy cohort; not model-selection uncertainty.'}

def train(csv_path,baseline_path,output,feature_set="original"):
    global NUMERIC, CATEGORICAL, extract, transform
    if feature_set=="history":
        from ml.history_features import NUMERIC, CATEGORICAL, extract, transform
    else:
        from app.services.ml_features import NUMERIC, CATEGORICAL, extract, transform
    if (output/'model.json').resolve()==baseline_path.resolve():raise ValueError('Candidate output must not overwrite deployed model.')
    if output.exists() and any(output.iterdir()):raise ValueError('Use a new empty candidate output directory.')
    output.mkdir(parents=True,exist_ok=True)
    grid=candidates()
    (output/'protocol.json').write_text(json.dumps({**PROTOCOL,'feature_set':feature_set,'candidates':{n:m.get_params() for n,m in grid.items()}},indent=2),encoding='utf-8')
    baseline=json.loads(baseline_path.read_text());meta=baseline['metadata']
    features,y,groups,data_hash=prepare_cohort(csv_path,meta)
    fit,cal,cutoff,test=split_cohort(features,y,groups,meta)
    comparison={name:{'fold_auroc':[]} for name in grid}
    cv=StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=PROTOCOL['seed'])
    for fold,(a,b) in enumerate(cv.split(fit,y[fit],groups[fit]),1):
        a=fit[a];b=fit[b];disjoint(groups,[a,b,cal,cutoff,test]);spec=preprocessing(features,a)
        xa=np.array([transform(features[i],spec) for i in a]);xb=np.array([transform(features[i],spec) for i in b])
        for name,prototype in grid.items():
            model=clone(prototype).fit(xa,y[a]);p=model.predict_proba(xb)[:,1]
            auc=float(roc_auc_score(y[b],p));comparison[name]['fold_auroc'].append(auc)
            print(f'Fold {fold}/4 · {name}: AUROC {auc:.4f}',flush=True)
    for name,values in comparison.items():
        values.update(mean_auroc=float(np.mean(values['fold_auroc'])),sd_auroc=float(np.std(values['fold_auroc'],ddof=1)))
    selected=max(comparison,key=lambda n:comparison[n]['mean_auroc'])
    print('Selected using training CV only: '+selected,flush=True)
    spec=preprocessing(features,fit);x=np.array([transform(f,spec) for f in features])
    model=clone(grid[selected]).fit(x[fit],y[fit])
    calibration=LogisticRegression().fit(logits(model.predict_proba(x[cal])[:,1]).reshape(-1,1),y[cal])
    def probability(index):return calibration.predict_proba(logits(model.predict_proba(x[index])[:,1]).reshape(-1,1))[:,1]
    threshold=choose_cutoff(y[cutoff],probability(cutoff))
    artifact=export_model(model,spec)
    artifact['calibration']={'coefficient':float(calibration.coef_[0][0]),'intercept':float(calibration.intercept_[0])}
    # Lock selection/calibration/cutoff before any legacy-test predictions.
    (output/'development_selection.json').write_text(json.dumps({'selected':selected,'comparison':comparison,'threshold':threshold,'calibration':artifact['calibration']},indent=2),encoding='utf-8')
    test_p=probability(test);current=np.array([predict_artifact(baseline,features[i]) for i in test])
    test_metrics=measures(y[test],test_p,threshold);base_metrics=measures(y[test],current,meta['threshold'])
    if base_metrics['confusion_matrix']!=meta['held_out_test']['confusion_matrix'] or abs(base_metrics['roc_auc']-meta['held_out_test']['roc_auc'])>1e-8:raise ValueError('Baseline metrics failed reproduction.')
    portable=np.array([candidate_predict(artifact,features[i]) for i in test])
    error=float(np.max(np.abs(portable-test_p)))
    if error>=1e-8:raise ValueError(f'Portable inference differs from fitted estimator: {error}')
    report={'version':'hivdr-panel-v2-candidate','trained_at':datetime.now(timezone.utc).isoformat(),
            'feature_set':feature_set,'status':'research_candidate_not_deployed','selected_model':selected,'target':meta['target'],'panel':PANEL,
            'protocol':PROTOCOL,'environment':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__},
            'data_sha256':data_hash,'baseline_model_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
            'training_eligible_rows':len(features),'split':{name:{'rows':len(index),'facilities':len(set(groups[index])),'positive_rate':float(y[index].mean())} for name,index in [('train',fit),('calibration',cal),('cutoff',cutoff),('legacy_test',test)]},
            'development_comparison':comparison,'threshold':threshold,'cutoff_partition_metrics':measures(y[cutoff],probability(cutoff),threshold),
            'legacy_test':test_metrics,'baseline_legacy_test':base_metrics,
            'paired_comparison':paired_intervals(y[test],current,test_p,groups[test]),
            'calibration':calibration_bins(y[test],test_p),
            'subgroups':subgroup_results([features[i] for i in test],y[test],test_p,threshold),
            'baseline_subgroups':subgroup_results([features[i] for i in test],y[test],current,meta['threshold']),
            'portable_max_absolute_error':error,
            'limitations':meta['limitations']+['Legacy test previously inspected; this is not a fresh independent validation.',
                'No new clinical records were added. History features, when enabled, use only observations dated on or before sample collection.',
                'No prospective validation or clinical operating cutoff is established.']}
    artifact['metadata']={k:v for k,v in report.items() if k not in ('subgroups','baseline_subgroups','development_comparison')}
    (output/'model.json').write_text(json.dumps(artifact,separators=(',',':')),encoding='utf-8')
    (output/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('selected_model','threshold','legacy_test','baseline_legacy_test','paired_comparison','portable_max_absolute_error')},indent=2),flush=True)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('csv',type=Path)
    parser.add_argument('--baseline',type=Path,default=Path(__file__).parent/'artifacts/model.json')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--features',choices=['original','history'],default='original');args=parser.parse_args()
    train(args.csv,args.baseline,args.output,args.features)

if __name__=='__main__':main()
