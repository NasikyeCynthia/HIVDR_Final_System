"""Map only documented historical values; no adherence or ownership is invented."""
import json
from .mutation_inputs import has_genotype,suggested_mutations
from datetime import datetime
from .import_service import present

def date(value):
    if not present(value): return None
    for fmt in ('%d/%m/%Y %H:%M','%d/%m/%Y','%Y-%m-%d','%Y-%m-%d %H:%M:%S'):
        try: return datetime.strptime(value,fmt).isoformat()+'+00:00'
        except ValueError: pass
    return None

def map_history(con,pid,raw):
    e=con.execute('SELECT * FROM episodes WHERE patient_id=?',(pid,)).fetchone()
    if e['sample_at'] or e['reviewed_at'] or e['report_at'] or e['status']!='Not collected': return False
    kind={'P':'Plasma','PLASMA':'Plasma','D':'DBS','DBS':'DBS'}.get(str(raw.get('Sample Type','')).upper())
    amp={'0':0,'1':1}.get(str(raw.get('amplified','')))
    sample=date(raw.get('Sample collection Date'))
    report=date(raw.get('DR_results_releaseDate'))
    resistance=any(value in {'Susceptible','Potential Low-Level Resistance','Low-Level Resistance','Intermediate Resistance','High-Level Resistance'} for key,value in raw.items() if key.startswith('Resistance to ')) or has_genotype(raw)
    status='Usable result' if amp==1 and resistance else 'Unamplified' if amp==0 else 'Pending' if sample or report else 'Not collected'
    decision=raw.get('decision Category')
    if decision not in ('Maintained','Switched','Substituted'): decision=None
    decision_date=date(raw.get('Decision Date')) if decision else None
    regimen=raw.get('Assigned ART by switch committee') or raw.get('ART started by patient') or ''
    implemented=date(raw.get('ART start date')) if present(raw.get('ART started by patient')) and decision else None
    con.execute('UPDATE episodes SET sample_at=?,sample_type=?,referred_at=?,report_at=?,amplified=?,status=?,failure_reason=?,mutations=?,decision=?,decision_at=?,reviewed_at=?,decision_notes=?,recommended_regimen=?,implemented_at=?,implementation_notes=? WHERE patient_id=?',
       (sample,kind,date(raw.get('Date referred to DR Lab')),report,amp,status,
        'Reason not recorded in source; laboratory follow-up required' if amp==0 else '',
        raw.get('All Mutations Combined') or suggested_mutations(raw),decision,decision_date,decision_date,
        'Imported documented committee decision: '+raw.get('Decision','') if decision else '',regimen,implemented,
        'Imported ART start date and patient-started regimen' if implemented else '',pid))
    flags=[key.removeprefix('PSS:') for key,val in raw.items() if key.startswith('PSS:') and str(val).lower()=='yes']
    assessed=any(str(val).lower() in ('yes','no') for key,val in raw.items() if key.startswith('PSS:'))
    con.execute('UPDATE patients SET psychosocial_json=? WHERE id=?',(json.dumps({'assessed':assessed,'factors':flags,'notes':'Imported source assessment' if assessed else ''}),pid))
    return True
