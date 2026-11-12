import os, sys
import sqlite3,json,sys
from datetime import timedelta
sys.path.insert(0,'.')
from app.services.eligibility_service import assess,parse_date
from app.services.risk_service import score
from sklearn.metrics import roc_auc_score
PANEL=['BIC','CAB','DTG','RAL','3TC','ABC','AZT','TDF','DOR','EFV','ETR','NVP']
VALID={'Susceptible','Potential Low-Level Resistance','Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
POS={'Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
c=sqlite3.connect(os.environ.get('HIVDR_DB','data/surveillance.sqlite3'));c.row_factory=sqlite3.Row
y=[];s=[];cat={}
for r in c.execute("select * from patients where source='original'"):
    raw=json.loads(r['original_json'])
    if raw.get('amplified')!='1' or not all(raw.get('Resistance to '+d) in VALID for d in PANEL): continue
    sd=parse_date(raw.get('Sample collection Date'))
    if not sd: continue
    # restrict VL history to the time of testing
    keep={k:v for k,v in raw.items() if not k.startswith('VL 6') and not k.startswith('VL 12')}
    p=dict(r);p['regimen']=raw.get('ART at sample collection(ART@VL@DR)')
    e=assess(p,keep,{},[],today=sd+timedelta(days=60))
    sc=score(p,keep,[],e)
    if sc['category']=='Not applicable': continue
    lab=int(any(raw['Resistance to '+d] in POS for d in PANEL))
    y.append(lab);s.append(sc['total']);cat.setdefault(sc['category'],[]).append(lab)
print(len(y),'AUROC',round(roc_auc_score(y,s),3))
for k,v in cat.items():print(k,len(v),round(sum(v)/len(v)*100))
