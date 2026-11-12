import os
import sqlite3,json,sys,math,collections,numpy as np
from datetime import timedelta
sys.path.insert(0,'.')
from app.services.eligibility_service import vl_timeline,parse_date,regimen_drugs
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score,brier_score_loss
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
c=sqlite3.connect(os.environ.get('HIVDR_DB','data/surveillance.sqlite3'))
rows=[json.loads(j) for (j,) in c.execute("select original_json from patients where source='original'")]
END=parse_date('26/06/2026');WIN=36;cut=END-timedelta(days=int(WIN*30.44))
def yn(v): v=str(v or '').strip().lower(); return 1. if v in('yes','1','true') else 0.
def num(v):
    try: x=float(str(v).replace(',','')); return x if math.isfinite(x) else np.nan
    except: return np.nan
REGIONS=sorted({r.get('Region') for r in rows if r.get('Region')})
def feats(r,rs):
    dob=parse_date(r.get('Date of Birth')); sd=parse_date(r.get('Sample collection Date'))
    age=(rs-dob).days/365.25 if dob else (num(r.get('Age(yrs)'))-((sd-rs).days/365.25) if sd and num(r.get('Age(yrs)'))==num(r.get('Age(yrs)')) else np.nan)
    if age==age and (age<0 or age>90): age=np.nan
    ai=parse_date(r.get('Treatment Initiation Date')); prior=(rs-ai).days/365.25 if ai and ai<=rs else np.nan
    d=regimen_drugs(r.get('ART at sample collection(ART@VL@DR)'))
    t=str(r.get('Treatment Line at Sample collection','')).lower(); line=1 if 'first' in t else 2 if 'second' in t else 3 if 'third' in t else np.nan
    return dict(age=age,female=1. if str(r.get('sex','')).upper().startswith('F') else 0.,line=line,
        nnrti=1. if d&{'EFV','NVP'} else 0.,pi=1. if d&{'LPV','ATV','DRV'} else 0.,dtg=1. if 'DTG' in d else 0.,
        tdf=1. if 'TDF' in d else 0.,azt=1. if 'AZT' in d else 0.,abc=1. if 'ABC' in d else 0.,
        prior_art_years=prior,regimen_changes=num(r.get('Regimen changes prior to sample collection')),
        exp_azt=yn(r.get('exposure_to_AZT')),exp_abc=yn(r.get('exposure_to_ABC')),exp_lpv=yn(r.get('exposure_to_LPV')),exp_dtg=yn(r.get('exposure_to_DTG')),
**{'region='+g:(1. if r.get('Region')==g else 0.) for g in REGIONS})
X=[];y=[];g=[];months=[]
for r in rows:
    rs=parse_date(r.get('ART@VL@DR start date'))
    if not rs or rs>cut or rs.year<2019: continue
    obs=[o for o in vl_timeline(r) if o['kind']=='pre' and o['date']>=rs]
    f=next((o for o in obs if o['copies']>=1000 and o['qualifier']!='<'),None)
    if not f: continue
    m=(f['date']-rs).days/30.44
    if m<1 or m>WIN: continue
    X.append(feats(r,rs)); y.append(int(m<=12)); g.append(r.get('Facility')); months.append(m)
names=list(X[0]); A=np.array([[x[k] for k in names] for x in X],float); y=np.array(y); g=np.array(g)
print('n',len(y),'early share',y.mean().round(3),'facilities',len(set(g)))
med=np.nanmedian(A,axis=0); miss=np.isnan(A); Af=np.where(miss,med,A)
def cv(make,X):
    s=[];b=[]
    for tr,te in GroupKFold(5).split(X,y,g):
        m=make(); m.fit(X[tr],y[tr]); p=m.predict_proba(X[te])[:,1]; s.append(roc_auc_score(y[te],p)); b.append(brier_score_loss(y[te],p))
    return np.round([np.mean(s),np.min(s),np.max(s),np.mean(b)],3)
LR=lambda: make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,C=0.5))
RF=lambda: RandomForestClassifier(300,max_depth=8,min_samples_leaf=20,n_jobs=4,random_state=0)
HGB=lambda: HistGradientBoostingClassifier(max_iter=250,learning_rate=0.05,max_leaf_nodes=15,l2_regularization=1.0,random_state=0)
print('baseline brier (predict share)',round(y.mean()*(1-y.mean()),3))
print('logistic  [auroc mean,min,max,brier]',cv(LR,Af))
print('forest    ',cv(RF,Af))
print('boosting  ',cv(HGB,A))
lr=LR().fit(Af,y); coef=lr[-1].coef_[0]
for n,cf in sorted(zip(names,coef),key=lambda t:-abs(t[1]))[:12]: print(f'{n:22s}{cf:+.2f}')

