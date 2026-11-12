import os, sys
import sqlite3,json,collections,sys
sys.path.insert(0,'.')
from app.services.suggestion_service import suggest
c=sqlite3.connect(os.environ.get('HIVDR_DB','data/surveillance.sqlite3'))
t=collections.Counter();conf=collections.Counter()
for (j,) in c.execute("select original_json from patients where source='original'"):
    r=json.loads(j);d=r.get('decision Category')
    if d not in('Maintained','Switched','Substituted') or r.get('amplified')!='1':continue
    s=suggest({'regimen':r.get('ART at sample collection(ART@VL@DR)')},{'status':'Usable result'},r)
    if not s or not s['action']: t['no suggestion']+=1;continue
    t['n']+=1; t['agree']+= s['action']==d; t['agree_or_alt']+= d in (s['action'],s.get('alternative'))
    conf[(s['action'],d)]+=1
print(t, round(t['agree']/t['n']*100,1), round(t['agree_or_alt']/t['n']*100,1))
for k,v in sorted(conf.items()):print(k,v)
