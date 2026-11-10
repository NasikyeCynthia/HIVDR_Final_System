import json
import re
from pathlib import Path
from ..core.errors import DomainError
from ..core.database import now
from .audit_service import audit
from .import_service import number,line_number,present

COLUMNS=json.loads((Path(__file__).resolve().parents[1]/'models/source_columns.json').read_text())
CORE={'Age(yrs)':'age','sex':'sex','ART at sample collection(ART@VL@DR)':'regimen','Treatment Line at Sample collection':'treatment_line','VL Leading to DR':'viral_load','Adherence (%)':'adherence'}
DECISION={'Decision Date','Decision','decision Category','Assigned ART by switch committee','ART started by patient','ART start date','Treatment Line on new ART'}
IDENTITY={'Patient No.','Facility','Patient Add Time','Is Backlog?','isBacklog'}

def is_extra_vl_field(key):
    return bool(re.fullmatch(r'viral_load_test_\d+(?:_date)?', key))

def section(key):
    if key in IDENTITY:return 'Identity and provenance'
    if key in DECISION:return 'Discussion and committee decision'
    if key.startswith('VL 6 Months') or key.startswith('VL 12 Months'):return 'Follow-up'
    if key.startswith('PSS:') or key=='ASP':return 'Psychosocial'
    if key=='VL Leading to DR' or key=='VL Test Date' or key.lower().startswith('vl_') or is_extra_vl_field(key):return 'Viral load history'
    if key.startswith('Resistance to ') or 'Mutation' in key or key in {'PI','INSTI','NRTI','NNRTI','Sample Type','Sample collection Date','No. of DR tests','dateTestedForDR','Date referred to DR Lab','DR_results_releaseDate','amplified','Lab failure reason','DBS justification'} or key.startswith('has relevant '):return 'Laboratory'
    if 'ART' in key or 'Treatment' in key or key.startswith('exposure_') or key in {'drIndication','Regimen changes prior to sample collection'}:return 'Treatment history'
    return 'Patient background'

def hidden_from_nurse(key):
    return section(key) in {'Laboratory', 'Discussion and committee decision'}

def effective_record(p):
    return {**json.loads(p.get('original_json') or '{}'),**json.loads(p.get('source_overrides_json') or '{}')}

def may_edit(user,p,key):
    if user['facility']!=p['facility'] or p.get('archived_at'):return False
    group=section(key)
    if group in {'Identity and provenance','Discussion and committee decision'}:return False
    if group=='Laboratory' and (p.get('reviewed_at') or p.get('decision')):return False
    return user['role']=='lab' if group=='Laboratory' else user['role'] in ('nurse','counsellor')

def sections(p,user):
    raw=effective_record(p);result={}
    raw.setdefault('Adherence (%)','' if p.get('adherence') is None else str(p['adherence']))
    raw.setdefault('Lab failure reason',p.get('failure_reason') or '')
    raw.setdefault('DBS justification',p.get('dbs_reason') or '')
    for key in dict.fromkeys(COLUMNS+['Adherence (%)','Lab failure reason','DBS justification']+list(raw)):
        if user['role']=='nurse' and hidden_from_nurse(key):continue
        result.setdefault(section(key),[]).append({'key':key,'value':raw.get(key,''),'editable':may_edit(user,p,key)})
    return result

def sync_core(con,pid,raw):
    updates={}
    for key,field in CORE.items():
        if key not in raw:continue
        value=raw[key]
        if field=='treatment_line':value=line_number(value)
        elif field in ('age','viral_load','adherence'):value=number(value)
        else:value=value or None
        if field=='adherence' and value is not None and value>100:raise ValueError('Adherence must be 0–100')
        if field=='age' and value is not None and value>120:raise ValueError('Age must be 0–120')
        updates[field]=value
    if updates:con.execute('UPDATE patients SET '+','.join(k+'=?' for k in updates)+' WHERE id=?',list(updates.values())+[pid])

def update_fields(con,user,p,e,data):
    changes=data['fields']
    if data['expected_version']!=p['data_version']:raise DomainError('The record changed. Reload before saving.',409)
    allowed=set(COLUMNS)|{'Adherence (%)','Lab failure reason','DBS justification'}
    for key,value in changes.items():
        if key not in allowed and not is_extra_vl_field(key):raise DomainError('Your role cannot edit '+key,403)
        if not may_edit(user,p,key):raise DomainError('Your role cannot edit '+key,403)
        if len(value)>20000:raise ValueError('Field value is too long')
        if section(key)=='Laboratory' and (e['reviewed_at'] or e['decision']):raise DomainError('Reviewed laboratory evidence is locked. Use the amendment workflow.',409)
        if key in {'Age(yrs)','VL Leading to DR','Adherence (%)'} and value and number(value) is None:raise ValueError('Enter a valid number for '+key)
        if key in CORE and CORE[key] in ('age','viral_load','adherence') and value.strip().startswith('-'):raise ValueError('Negative values are not allowed')
    previous=effective_record(p);overrides=json.loads(p.get('source_overrides_json') or '{}');overrides.update(changes)
    changed=con.execute("UPDATE patients SET source_overrides_json=?,data_version=data_version+1,assigned_to=CASE WHEN assigned_to IS NULL AND ? IN ('nurse','counsellor') THEN ? ELSE assigned_to END WHERE id=? AND data_version=?",(json.dumps(overrides),user['role'],user['id'],p['id'],data['expected_version']))
    if changed.rowcount!=1:raise DomainError('The record changed. Reload before saving.',409)
    sync_core(con,p['id'],changes)
    raw={**previous,**changes}
    if any(section(key)=='Laboratory' for key in changes):
        from .history_service import date
        valid={'Susceptible','Potential Low-Level Resistance','Low-Level Resistance','Intermediate Resistance','High-Level Resistance'}
        for key,value in changes.items():
            if key.startswith('Resistance to ') and value and value not in valid:raise ValueError('Choose a supported resistance interpretation for '+key)
        amp_text=str(raw.get('amplified',''))
        if amp_text not in ('','0','1'):raise ValueError('Amplified must be 0, 1 or blank')
        amp={'0':0,'1':1}.get(amp_text)
        kind={'P':'Plasma','PLASMA':'Plasma','D':'DBS','DBS':'DBS'}.get(str(raw.get('Sample Type','')).upper())
        failure=raw.get('Lab failure reason',e.get('failure_reason') or '')
        dbs_reason=raw.get('DBS justification',e.get('dbs_reason') or '')
        if kind=='DBS' and not str(dbs_reason).strip():raise ValueError('A reason for using DBS is required')
        if amp==0 and not str(failure).strip():raise ValueError('An unsuccessful-test reason is required')
        from .mutation_inputs import has_genotype
        has_scores=any(v in valid for k,v in raw.items() if k.startswith('Resistance to ')) or has_genotype(raw)
        status='Usable result' if amp==1 and has_scores else 'Unamplified' if amp==0 else 'Pending'
        con.execute('INSERT INTO lab_attempts(patient_id,actor_id,created_at,snapshot_json) VALUES(?,?,?,?)',(p['id'],user['id'],now(),json.dumps(e)))
        con.execute('UPDATE episodes SET lab_owner=?,sample_type=?,failure_reason=?,dbs_reason=?,sample_at=?,report_at=?,amplified=?,status=?,mutations=?,interpretation_json=NULL,interpreted_at=NULL,version=version+1 WHERE patient_id=?',
          (user['id'],kind,failure,dbs_reason,date(raw.get('Sample collection Date')),date(raw.get('DR_results_releaseDate')),amp,status,raw.get('All Mutations Combined') or e['mutations'],p['id']))
    if any(key.startswith('PSS:') for key in changes):
        psy={'assessed':any(str(v).lower() in ('yes','no') for k,v in raw.items() if k.startswith('PSS:')),'factors':[k[4:] for k,v in raw.items() if k.startswith('PSS:') and str(v).lower()=='yes'],'notes':'Recorded psychosocial fields'}
        con.execute('UPDATE patients SET psychosocial_json=? WHERE id=?',(json.dumps(psy),p['id']))
    audit(con,user,'record fields corrected',p['id'],{k:previous.get(k) for k in changes},changes)

def repair_existing(con):
    """Fill genuinely unmapped fields without replacing staff edits or explicit clears."""
    count=0
    for row in con.execute("SELECT * FROM patients WHERE source='original' AND (age IS NULL OR sex IS NULL OR regimen IS NULL OR treatment_line IS NULL OR viral_load IS NULL OR (adherence IS NULL AND original_json LIKE '%Adherence (%)%'))").fetchall():
        p=dict(row);raw=effective_record(p)
        edited=con.execute("SELECT 1 FROM audit WHERE entity=? AND action='profile update' LIMIT 1",(str(p['id']),)).fetchone()
        if not edited:
            fill={key:raw[key] for key,field in CORE.items() if p.get(field) is None and present(raw.get(key))}
            if fill:sync_core(con,p['id'],fill);count+=1
    from .history_service import map_history
    untouched=con.execute("SELECT p.id,p.original_json FROM patients p JOIN episodes e ON e.patient_id=p.id WHERE p.source='original' AND e.status='Not collected' AND e.sample_at IS NULL AND e.report_at IS NULL AND e.reviewed_at IS NULL AND e.decision IS NULL").fetchall()
    for row in untouched:
        raw=json.loads(row['original_json'])
        if any(present(raw.get(k)) for k in ('Sample collection Date','Date referred to DR Lab','DR_results_releaseDate','Decision Date')):
            map_history(con,row['id'],raw)
    from .mutation_inputs import has_genotype,suggested_mutations
    for row in con.execute("SELECT p.id,p.original_json,p.source_overrides_json FROM patients p JOIN episodes e ON e.patient_id=p.id WHERE e.status='Pending' AND e.amplified=1 AND e.version=0 AND e.reviewed_at IS NULL AND e.decision IS NULL").fetchall():
        raw=effective_record(dict(row))
        if has_genotype(raw):con.execute("UPDATE episodes SET status='Usable result',mutations=CASE WHEN mutations='' THEN ? ELSE mutations END WHERE patient_id=?",(raw.get('All Mutations Combined') or suggested_mutations(raw),row['id']))
    return count

def overlay_changes(con,pid,changes):
    row=con.execute('SELECT source_overrides_json FROM patients WHERE id=?',(pid,)).fetchone()
    values=json.loads(row['source_overrides_json'] or '{}');values.update(changes)
    con.execute('UPDATE patients SET source_overrides_json=?,data_version=data_version+1 WHERE id=?',(json.dumps(values),pid))
