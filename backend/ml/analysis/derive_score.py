import os, sys
import sqlite3,json,math,collections,sys
import numpy as np
sys.path.insert(0,'.')
from app.services.eligibility_service import parse_date,parse_vl,vl_timeline,regimen_drugs
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import roc_auc_score
PANEL=['BIC','CAB','DTG','RAL','3TC','ABC','AZT','TDF','DOR','EFV','ETR','NVP']
VALID={'Susceptible','Potential Low-Level Resistance','Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
POS={'Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
c=sqlite3.connect(os.environ.get('HIVDR_DB','data/surveillance.sqlite3'))
rows=[json.loads(j) for (j,) in c.execute("select original_json from patients where source='original'")]
def factors(r):
    v=parse_vl(r.get('VL Leading to DR')); vl=v[0] if v else None
    sd=parse_date(r.get('Sample collection Date'))
    drugs=regimen_drugs(r.get('ART at sample collection(ART@VL@DR)'))
    anchor='INSTI' if drugs&{'DTG','RAL'} else 'PI' if drugs&{'LPV','ATV','DRV'} else 'NNRTI' if drugs&{'EFV','NVP'} else 'Other'
    t=str(r.get('Treatment Line at Sample collection','')).lower()
    line=1 if 'first' in t else 2 if 'second' in t else 3 if 'third' in t else None
    try: age=float(r.get('Age(yrs)'))
    except: age=None
    if age is not None and age>=100: age=None
    start=parse_date(r.get('Treatment Initiation Date'))
    yrs=(sd-start).days/365.25 if sd and start and sd>=start else None
    # consecutive NS before sample
    obs=[o for o in vl_timeline(r) if o['kind']=='pre' and sd and o['date']<sd- __import__('datetime').timedelta(days=14)]
    ns=0
    for o in reversed(obs):
        if o['qualifier']!='<' and o['copies']>=1000: ns+=1
        else: break
    exp=r.get('exposure_to_AZT_and_ABC','')
    return dict(vl=vl,anchor=anchor,line=line,age=age,yrs=yrs,prior_ns=ns,n_prior=len(obs),both_nrti=str(exp).strip().lower() in('yes','1','true'))
X=[];y=[];g=[];F=[]
for r in rows:
    if r.get('amplified')!='1' or not all(r.get('Resistance to '+d) in VALID for d in PANEL): continue
    f=factors(r)
    if f['vl'] is None: continue
    F.append(f);y.append(int(any(r['Resistance to '+d] in POS for d in PANEL)));g.append(r['Facility'])
y=np.array(y);g=np.array(g)
print('n',len(y),'prev',y.mean().round(3))
print('exposure values',collections.Counter(str(r.get('exposure_to_AZT_and_ABC')) for r in rows).most_common(4))
def enc(f):
    vl=f['vl']
    return [vl>=10000 and vl<100000, vl>=100000,
            f['anchor']=='NNRTI', f['anchor']=='PI',
            f['line']==2, f['line']==3,
            f['age'] is not None and f['age']<10, f['age'] is not None and 10<=f['age']<20,
            f['yrs'] is not None and 2<=f['yrs']<5, f['yrs'] is not None and f['yrs']>=5,
            f['prior_ns']>=1, f['prior_ns']>=2, f['both_nrti']]
names=['VL 10k-100k','VL >=100k','NNRTI anchor','PI anchor','2nd line','3rd line','age<10','age10-19','ART 2-5y','ART>=5y','>=1 prior NS','>=2 prior NS','AZT+ABC exposed']
X=np.array([enc(f) for f in F],dtype=float)
# univariate rates
for i,n in enumerate(names):
    m=X[:,i]==1; print(f'{n:15s} n={m.sum():5d} rate={y[m].mean():.2f} vs {y[~m].mean():.2f}')
fit,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(X,y,g))
lr=LogisticRegression(max_iter=2000).fit(X[fit],y[fit])
print('test AUROC full LR',round(roc_auc_score(y[test],lr.predict_proba(X[test])[:,1]),3))
for n,b in zip(names,lr.coef_[0]): print(f'{n:15s} beta={b:+.2f} OR={math.exp(b):.2f}')
print('intercept',lr.intercept_)
np.save('ml/analysis/X.npy',X);np.save('ml/analysis/y.npy',y);np.save('ml/analysis/g.npy',g)
