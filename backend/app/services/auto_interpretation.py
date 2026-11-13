"""Durable Stanford jobs; drug interpretations and local drafts never approve treatment."""
import json
from concurrent.futures import ThreadPoolExecutor
from ..core.database import connect,now
from ..core.errors import DomainError
from .mutation_inputs import analysis_input
from .record_service import effective_record
from .audit_service import audit
from . import stanford_service

_workers=ThreadPoolExecutor(max_workers=2,thread_name_prefix='stanford')


def enqueue(con,user,patient_id):
    p=dict(con.execute('SELECT * FROM patients WHERE id=?',(patient_id,)).fetchone())
    e=dict(con.execute('SELECT * FROM episodes WHERE patient_id=?',(patient_id,)).fetchone())
    if e['status']!='Usable result' or e.get('decision') or p.get('archived_at'):
        return None
    current=con.execute("SELECT id FROM interpretation_jobs WHERE patient_id=? AND episode_version=? AND status IN ('pending','running') ORDER BY id DESC LIMIT 1",(patient_id,e['version'])).fetchone()
    if current:return current['id']
    con.execute("UPDATE interpretation_jobs SET status='superseded',message='Laboratory evidence changed.',finished_at=? WHERE patient_id=? AND status IN ('pending','running')",(now(),patient_id))
    sequence=str(e.get('sequence') or '').strip()
    mutations=analysis_input(effective_record(p),e.get('mutations'))
    kind,text=('sequence',sequence) if sequence else ('mutations',mutations)
    status='pending' if text else 'needs_input'
    con.execute('UPDATE episodes SET interpretation_json=NULL,interpreted_at=NULL,suggestion_json=NULL WHERE patient_id=?',(patient_id,))
    message='Waiting for Stanford analysis.' if text else 'A gene-specific mutation list or nucleotide sequence is needed. For a no-mutations report, supply the sequence.'
    row=con.execute('INSERT INTO interpretation_jobs(patient_id,episode_version,input_kind,input_text,status,message,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
                    (patient_id,e['version'],kind,text,status,message,user['id'],now()))
    audit(con,user,'automatic Stanford analysis queued',patient_id,after={'job_id':row.lastrowid,'status':status,'episode_version':e['version']})
    return row.lastrowid


def state(con,e):
    if e.get('decision'):
        return {'status':'approved','message':'Clinician decision approved; implementation recorded.' if e.get('implemented_at') else 'Clinician decision approved; awaiting nurse or counsellor implementation.'}
    job=con.execute('SELECT id,status,message,created_at,started_at,finished_at,episode_version FROM interpretation_jobs WHERE patient_id=? ORDER BY id DESC LIMIT 1',(e['patient_id'],)).fetchone()
    if e.get('interpretation_json'):
        return {'status':'ready','message':'Stanford interpretation saved. Awaiting clinician approval.','job_id':job['id'] if job else None}
    if e['status']!='Usable result':return {'status':'not_required','message':'Awaiting a usable laboratory result.'}
    if not job:return {'status':'not_requested','message':'Existing laboratory result: run its saved genotype to prepare a Stanford-based draft.'}
    if job['episode_version']!=e['version']:return {'status':'not_requested','message':'The laboratory evidence changed; request a new analysis.'}
    return dict(job)


def schedule(patient_id):
    _workers.submit(process_pending,patient_id)


def resume_pending():
    # Single-process prototype: recover durable jobs left by a previous interrupted process.
    with connect() as con:
        con.execute("UPDATE interpretation_jobs SET status='pending',message='Resuming interrupted analysis.' WHERE status='running'")
        ids=[r[0] for r in con.execute("SELECT DISTINCT patient_id FROM interpretation_jobs WHERE status='pending'")]
    for patient_id in ids:schedule(patient_id)


def process_pending(patient_id):
    with connect() as con:
        row=con.execute("SELECT * FROM interpretation_jobs WHERE patient_id=? AND status='pending' ORDER BY id DESC LIMIT 1",(patient_id,)).fetchone()
        if not row:return
        job=dict(row)
        if con.execute("UPDATE interpretation_jobs SET status='running',message='Contacting Stanford HIVdb.',started_at=? WHERE id=? AND status='pending'",(now(),job['id'])).rowcount!=1:return
        e=dict(con.execute('SELECT * FROM episodes WHERE patient_id=?',(patient_id,)).fetchone())
        p=dict(con.execute('SELECT * FROM patients WHERE id=?',(patient_id,)).fetchone())
        if e['version']!=job['episode_version'] or e['status']!='Usable result' or e.get('decision') or p.get('archived_at'):
            con.execute("UPDATE interpretation_jobs SET status='superseded',message='Laboratory result changed or record locked.',finished_at=? WHERE id=?",(now(),job['id']))
            return
    try:
        result=stanford_service.analyze(job['input_kind'],job['input_text'])
        with connect() as con:
            e=dict(con.execute('SELECT * FROM episodes WHERE patient_id=?',(patient_id,)).fetchone())
            p=dict(con.execute('SELECT * FROM patients WHERE id=?',(patient_id,)).fetchone())
            job_status=con.execute('SELECT status FROM interpretation_jobs WHERE id=?',(job['id'],)).fetchone()[0]
            if job_status!='running' or e['version']!=job['episode_version'] or e['status']!='Usable result' or e.get('decision') or p.get('archived_at'):
                con.execute("UPDATE interpretation_jobs SET status='superseded',message='Old response discarded: the laboratory result changed or record locked.',finished_at=? WHERE id=?",(now(),job['id']))
                return
            from .suggestion_service import suggest
            draft=suggest(p,{**e,'interpretation_json':json.dumps(result)},effective_record(p))
            con.execute('UPDATE episodes SET interpretation_json=?,interpreted_at=?,suggestion_json=?,version=version+1 WHERE patient_id=?',
                        (json.dumps(result),now(),json.dumps(draft),patient_id))
            con.execute("UPDATE interpretation_jobs SET status='completed',message='Stanford interpretation saved; clinician review required.',finished_at=? WHERE id=?",(now(),job['id']))
            audit(con,{'name':'Automatic Stanford interpretation','role':'system'},'automatic Stanford analysis completed',patient_id,
                  after={'job_id':job['id'],'stanford_version':result.get('version'),'draft_action':(draft or {}).get('action'),'draft_rule_version':(draft or {}).get('version')})
    except Exception as error:
        message=str(error) if isinstance(error,DomainError) else 'Automatic analysis failed. Retry the saved laboratory result from Discussion.'
        with connect() as con:
            con.execute("UPDATE interpretation_jobs SET status='failed',message=?,finished_at=? WHERE id=? AND status='running'",(message[:1000],now(),job['id']))
