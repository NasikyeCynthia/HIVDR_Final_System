"""Fair exploratory comparison of model families; never changes the active model.

Use Python 3.13 and ml/requirements-comparison.txt. Run from backend:
python ml/compare_models.py ORIGINAL.csv --output NEW_EMPTY_RESEARCH_DIRECTORY
Only aggregate results are saved; fitted models and patient-level predictions are not.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
import time
import warnings
if __name__=='__main__':print('Loading isolated research libraries...',flush=True)
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.ensemble import AdaBoostClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score
from sklearn.model_selection import GroupShuffleSplit,StratifiedGroupKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits

BACKEND=Path(__file__).resolve().parents[1]
if not (BACKEND/'app').exists():
    BACKEND=Path.cwd()
    if not (BACKEND/'app').exists():raise RuntimeError('Run from backend or place this script in backend/ml.')
sys.path.insert(0,str(BACKEND))
from app.services.ml_history_features import NUMERIC,CATEGORICAL,extract,transform
from app.services.ml_features import extract as original_extract
from app.services.ml_service import model as active_model,predict_artifact
from ml.validate_model import PANEL,VALID,POSITIVE,measures,calibration_bins,subgroup_results

SEED=20261114
PROTOCOL={
    'version':'hivdr-model-family-comparison-v1',
    'selection':'Highest mean AUROC across the same four training-only facility-grouped folds. No model selection from legacy-test results.',
    'calibration':'Each model: standardise raw margins on calibration data, then logistic calibration on 518 separate records / 94 facilities.',
    'cutoff':'Each model: maximise balanced accuracy on 1057 other records / 95 facilities; ties prefer sensitivity.',
    'legacy_test':'1739 previously examined records / 236 facilities. Exploratory reused comparison; not independent validation.',
    'feature_schema':'history-v2; identical preprocessing protocol for every family, fitted within each training fold.',
    'candidate_scope':'One fixed configuration per family; this is not exhaustive hyperparameter optimisation.',
    'internal_validation':'No row-wise early-stopping validation and no SVC probability=True internal calibration.',
    'export_policy':'Aggregate metrics only. No patient rows, individual predictions, support vectors or nearest-neighbour training data exported.',
    'deployment':'Active model is not replaced by this experiment.',
    'cv_seed':SEED,
}

def candidates():
    models={
      'Random forest (active configuration)':RandomForestClassifier(n_estimators=300,max_depth=12,min_samples_leaf=8,class_weight='balanced',n_jobs=2,random_state=42),
      'Logistic regression':LogisticRegression(max_iter=1500,class_weight='balanced',random_state=42),
      'Gradient boosting':GradientBoostingClassifier(n_estimators=200,learning_rate=.05,max_depth=3,min_samples_leaf=20,random_state=42),
      'Histogram gradient boosting':HistGradientBoostingClassifier(max_iter=250,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=5,class_weight='balanced',early_stopping=False,random_state=42),
      'AdaBoost':AdaBoostClassifier(n_estimators=200,learning_rate=.05,random_state=42),
      'SVM (RBF)':SVC(C=1,kernel='rbf',gamma='scale',class_weight='balanced',probability=False,cache_size=256,random_state=42),
      'Nearest neighbours':KNeighborsClassifier(n_neighbors=35,weights='distance',n_jobs=2),
      'Gaussian naive Bayes':GaussianNB(var_smoothing=.01),
      'Neural network (MLP)':MLPClassifier(hidden_layer_sizes=(64,32),alpha=1,learning_rate_init=.001,batch_size=128,max_iter=400,early_stopping=False,n_iter_no_change=20,random_state=42),
    }
    unavailable={};versions={}
    try:
        import xgboost
        models['XGBoost']=xgboost.XGBClassifier(n_estimators=400,max_depth=4,learning_rate=.05,min_child_weight=10,
            subsample=.85,colsample_bytree=.85,reg_lambda=5,objective='binary:logistic',eval_metric='logloss',n_jobs=2,random_state=42,verbosity=0)
        versions['xgboost']=xgboost.__version__
    except (ImportError,OSError) as e:unavailable['XGBoost']=type(e).__name__
    try:
        import lightgbm
        models['LightGBM']=lightgbm.LGBMClassifier(n_estimators=400,num_leaves=15,min_child_samples=30,learning_rate=.04,
            reg_lambda=5,class_weight='balanced',subsample=.85,subsample_freq=1,colsample_bytree=.85,
            deterministic=True,force_col_wise=True,n_jobs=2,random_state=42,verbosity=-1)
        versions['lightgbm']=lightgbm.__version__
    except (ImportError,OSError) as e:unavailable['LightGBM']=type(e).__name__
    try:
        import catboost
        models['CatBoost']=catboost.CatBoostClassifier(iterations=400,depth=5,learning_rate=.05,l2_leaf_reg=6,
            auto_class_weights='Balanced',loss_function='Logloss',random_seed=42,thread_count=2,verbose=False,allow_writing_files=False)
        versions['catboost']=catboost.__version__
    except (ImportError,OSError) as e:unavailable['CatBoost']=type(e).__name__
    return models,unavailable,versions

def cohort(path,meta):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=meta['data_sha256']:raise ValueError('Original dataset fingerprint mismatch.')
    with path.open(encoding='utf-8-sig',newline='') as file:rows=list(csv.DictReader(file))
    seen=set();features=[];labels=[];groups=[]
    for r in rows:
        if r.get('amplified')!='1' or not all(r.get('Resistance to '+d) in VALID for d in PANEL):continue
        y=int(any(r['Resistance to '+d] in POSITIVE for d in PANEL))
        key=(r['Facility'],r.get('Date of Birth'),r.get('Treatment Initiation Date'),json.dumps(original_extract(r),sort_keys=True),y)
        if key in seen:continue
        seen.add(key);features.append(extract(r));labels.append(y);groups.append(r['Facility'])
    if len(features)!=meta['training_eligible_rows']:raise ValueError('Original cohort count mismatch.')
    return features,np.array(labels),np.array(groups),digest

def disjoint(groups,*partitions):
    sets=[set(groups[index]) for index in partitions]
    if any(a&b for i,a in enumerate(sets) for b in sets[i+1:]):raise ValueError('Facility leakage.')

def split(features,y,groups,meta):
    fit,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(features,y,groups))
    train,valid=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(fit,y[fit],groups[fit]));train=fit[train];valid=fit[valid]
    for name,index in [('train',train),('validation',valid),('test',test)]:
        expected=meta['split'][name]
        if len(index)!=expected['rows'] or len(set(groups[index]))!=expected['facilities'] or abs(y[index].mean()-expected['positive_rate'])>1e-12:raise ValueError('Original split mismatch.')
    cal,cut=next(GroupShuffleSplit(n_splits=1,test_size=.5,random_state=SEED).split(valid,y[valid],groups[valid]));cal=valid[cal];cut=valid[cut]
    disjoint(groups,train,cal,cut,test)
    return train,cal,cut,test

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

def score(model,x):
    if hasattr(model,'decision_function'):
        values=np.asarray(model.decision_function(x),dtype=float).reshape(-1)
    elif isinstance(model,GaussianNB):
        log_p=model.predict_log_proba(x)
        values=log_p[:,1]-log_p[:,0]
    else:
        p=np.clip(model.predict_proba(x)[:,1],1e-6,1-1e-6)
        values=np.log(p/(1-p))
    if not np.all(np.isfinite(values)):raise ValueError('Non-finite model scores.')
    return values

def choose_cutoff(y,p):
    results=[]
    for t in np.arange(10,91)/100:
        m=measures(y,p,float(t));results.append((m['balanced_accuracy'],m['sensitivity'],float(t)))
    return max(results)[2]

def metrics(y,p,cutoff):
    result=measures(y,p,cutoff);c=result['confusion_matrix'];den=2*c['tp']+c['fp']+c['fn']
    result['f1']=2*c['tp']/den if den else None
    return result

def paired_auc(y,active,new,groups,replicates=500):
    rng=np.random.default_rng(SEED);indices=[np.flatnonzero(groups==g) for g in np.unique(groups)];values=[]
    for _ in range(replicates):
        take=np.concatenate([indices[i] for i in rng.integers(0,len(indices),len(indices))])
        if len(set(y[take]))==2:values.append(float(roc_auc_score(y[take],new[take])-roc_auc_score(y[take],active[take])))
    return {'method':'Paired facility-cluster percentile bootstrap','replicates':replicates,
            'difference':float(roc_auc_score(y,new)-roc_auc_score(y,active)),
            'difference_95_interval':[float(v) for v in np.percentile(values,[2.5,97.5])],
            'limitation':'Reused cohort; conditions on fitted models and excludes selection uncertainty.'}

def fit(model,x,y):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');start=time.perf_counter();model.fit(x,y);seconds=time.perf_counter()-start
    return seconds,dict(Counter(type(w.message).__name__ for w in caught))

def compare(csv_path,output):
    if output.exists() and any(output.iterdir()):raise ValueError('Use a new empty output directory.')
    if output.resolve().is_relative_to((BACKEND/'ml/artifacts').resolve()):raise ValueError('Do not write comparison results into active artifacts.')
    grid,unavailable,versions=candidates()
    print(f'Libraries ready: {len(grid)} model families; {len(unavailable)} unavailable.',flush=True)
    output.mkdir(parents=True,exist_ok=True)
    protocol={**PROTOCOL,'declared_candidates':list(grid),'unavailable':unavailable,'parameters':{n:m.get_params() for n,m in grid.items()},
              'environment':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__,
                             'scipy':version('scipy'),'pandas':version('pandas'),**versions}}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2,default=str),encoding='utf-8')
    baseline_path=BACKEND/'ml/artifacts/model.json';baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
    active=active_model();active_sha=active['_runtime']['sha256']
    features,y,groups,digest=cohort(csv_path,baseline['metadata'])
    train,cal,cut,test=split(features,y,groups,baseline['metadata'])
    print(f'Original cohort and splits verified: {len(train)} training records; starting four grouped folds.',flush=True)
    result={name:{'fold_auroc':[],'fold_average_precision':[],'cv_fit_seconds':0.,'warnings':{}} for name in grid}
    cv=StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=SEED)
    for fold,(a,b) in enumerate(cv.split(train,y[train],groups[train]),1):
        a=train[a];b=train[b];disjoint(groups,a,b,cal,cut,test)
        spec=preprocessing(features,a);xa=np.array([transform(features[i],spec) for i in a]);xb=np.array([transform(features[i],spec) for i in b])
        for name,prototype in grid.items():
            r=result[name]
            if r.get('excluded'):continue
            try:
                model=clone(prototype);seconds,warning_counts=fit(model,xa,y[a]);scores=score(model,xb)
                r['fold_auroc'].append(float(roc_auc_score(y[b],scores)))
                r['fold_average_precision'].append(float(average_precision_score(y[b],scores)))
                r['cv_fit_seconds']+=seconds;r['warnings']=dict(Counter(r['warnings'])+Counter(warning_counts))
                print(f'Fold {fold}/4 | {name} | AUROC {r["fold_auroc"][-1]:.4f}',flush=True)
            except Exception as e:
                r['excluded']=type(e).__name__;print(f'Fold {fold}/4 | {name} | excluded: {type(e).__name__}',flush=True)
        (output/'cv_progress.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    complete={n:r for n,r in result.items() if len(r['fold_auroc'])==4 and not r.get('excluded')}
    if not complete:raise ValueError('No model completed all four folds.')
    for r in complete.values():
        r.update(mean_cv_auroc=float(np.mean(r['fold_auroc'])),sd_cv_auroc=float(np.std(r['fold_auroc'],ddof=1)),
                 mean_cv_average_precision=float(np.mean(r['fold_average_precision'])))
    ranked=sorted(complete,key=lambda n:complete[n]['mean_cv_auroc'],reverse=True);selected=ranked[0]
    # Lock model ranking before fitting calibration/cutoffs or examining legacy predictions.
    selection={'selected_by_training_cv':selected,'cv_ranking':ranked,'development_results':result}
    (output/'selection.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    print('Locked selection using training CV: '+selected,flush=True)
    spec=preprocessing(features,train);x=np.array([transform(f,spec) for f in features])
    final={};models={};calibrators={}
    for name in ranked:
        model=clone(grid[name]);seconds,warn=fit(model,x[train],y[train])
        cal_scores=score(model,x[cal]);mean=float(cal_scores.mean());scale=float(cal_scores.std()) or 1.
        calibrator=LogisticRegression(max_iter=1000).fit(((cal_scores-mean)/scale).reshape(-1,1),y[cal])
        p=calibrator.predict_proba(((score(model,x[cut])-mean)/scale).reshape(-1,1))[:,1];cutoff=choose_cutoff(y[cut],p)
        final[name]={'threshold':cutoff,'cutoff_partition':metrics(y[cut],p,cutoff),'fit_seconds':seconds,
                     'warnings':warn,'calibration':{'coefficient':float(calibrator.coef_[0][0])/scale,
                         'intercept':float(calibrator.intercept_[0])-float(calibrator.coef_[0][0])*mean/scale}}
        models[name]=model;calibrators[name]=(calibrator,mean,scale)
    (output/'locked_operating_points.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
    active_p=np.array([predict_artifact(active,f) for f in (features[i] for i in test)])
    active_metrics=metrics(y[test],active_p,active['metadata']['threshold'])
    expected=active['metadata']['held_out_test']
    if active_metrics['confusion_matrix']!=expected['confusion_matrix'] or abs(active_metrics['roc_auc']-expected['roc_auc'])>1e-8:raise ValueError('Active model legacy baseline did not reproduce.')
    selected_probabilities=None
    for name in ranked:
        calibrator,mean,scale=calibrators[name]
        p=calibrator.predict_proba(((score(models[name],x[test])-mean)/scale).reshape(-1,1))[:,1]
        final[name]['legacy_test']=metrics(y[test],p,final[name]['threshold'])
        final[name]['calibration_bins']=calibration_bins(y[test],p)
        final[name]['subgroups']=subgroup_results([features[i] for i in test],y[test],p,final[name]['threshold'])
        if name==selected:selected_probabilities=p
        print(f'Legacy comparison | {name} | AUROC {final[name]["legacy_test"]["roc_auc"]:.4f}',flush=True)
    comparison=paired_auc(y[test],active_p,selected_probabilities,groups[test])
    after=json.loads((BACKEND/'ml/artifacts/active_model.json').read_text(encoding='utf-8'))
    if after['sha256']!=active_sha:raise ValueError('Active model changed during this experiment.')
    report={'protocol':protocol,'completed_at':datetime.now(timezone.utc).isoformat(),'data_sha256':digest,
            'active_model_version':active['metadata']['version'],'active_model_sha256':active_sha,
            'selected_by_training_cv':selected,'cv_ranking':ranked,'development_results':result,'models':final,
            'split':{n:{'rows':len(i),'facilities':len(set(groups[i])),'positive_rate':float(y[i].mean())} for n,i in [('train',train),('calibration',cal),('cutoff',cut),('legacy_test',test)]},
            'active_model_legacy_test':active_metrics,'selected_vs_active_paired_auc':comparison,
            'limitations':['One fixed configuration per family; results do not establish the globally best algorithm.',
                          'Repeated development and previously inspected legacy test; no independent validation.',
                          'Shared numerical/one-hot representation; CatBoost native categorical handling was not tested.',
                          'CV spread is not a confidence interval. Selection uncertainty is not included in the paired bootstrap.',
                          'Research-only comparison. Active application model was not changed.']}
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'selected_by_training_cv':selected,'paired_auc':comparison,'active_model_unchanged':True},indent=2),flush=True)
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('csv',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with threadpool_limits(limits=2):compare(args.csv,args.output)

if __name__=='__main__':main()
