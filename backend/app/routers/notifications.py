from fastapi import APIRouter, Depends,Query
from pydantic import BaseModel,Field
import hashlib
import re
from ..core.database import connect,now
from ..core.errors import DomainError
from ..core.dependencies import current_user
from ..services.patient_service import records
from ..services.notification_service import notifications
router = APIRouter(prefix='/api/notifications', tags=['Notifications'])
@router.get('')
def list_notifications(user=Depends(current_user)):
    with connect() as con:
        due = {r[0]: r[1] for r in con.execute('SELECT patient_id,min(due_date) FROM follow_ups WHERE assessed_on IS NULL GROUP BY patient_id')}
        result = notifications(records(con, user), due)
        # Each role sees the work that is theirs.
        mine = {
            'nurse': ('Missing profile: ', 'Approved decision', '6-monthly', 'High risk', 'Repeat sample requested', 'Viral load result awaited'),
            'counsellor': ('Missing profile: ', 'Approved decision', '6-monthly', 'High risk', 'Repeat sample requested', 'Viral load result awaited'),
            'lab': ('Eligible for a DR test', 'Unsuccessful laboratory test', 'DR result overdue','Stanford analysis','Laboratory input needed for Stanford'),
            'clinician': ('Usable result awaits clinician review','Stanford analysis','Laboratory input needed for Stanford'),
        }.get(user['role'])
        if mine:
            result = [{**item, 'reasons': [r for r in item['reasons'] if r.startswith(mine)]} for item in result]
            result = [item for item in result if item['reasons']]
        return result


def describe(reason):
    if reason.startswith('Stanford analysis required'):return ('Saved result needs interpretation','discussion','analysis')
    if reason.startswith('Stanford analysis'):return ('Stanford analysis needs attention','discussion','analysis')
    if reason.startswith('Laboratory input'):return ('Laboratory input required','laboratory','laboratory')
    if reason.startswith('Usable result'):return ('Result ready for clinician review','discussion','review')
    if reason.startswith('Approved decision'):return ('Approved decision awaiting implementation','decision','implementation')
    if reason.startswith('Missing profile'):return ('Patient profile incomplete','profile','profile')
    if reason.startswith('6-monthly'):return ('Follow-up assessment due','decision','follow-up')
    if reason.startswith('Viral load'):return ('Viral load result awaited','viral-load','laboratory')
    if reason.startswith('Repeat sample'):return ('Repeat sample requested','laboratory','laboratory')
    if reason.startswith('DR result overdue'):return ('Laboratory result overdue','laboratory','laboratory')
    if reason.startswith('Unsuccessful'):return ('Unsuccessful laboratory test','laboratory','laboratory')
    if reason.startswith('Eligible'):return ('DR test request due','laboratory','laboratory')
    return ('Patient follow-up required','risk','follow-up')


@router.get('/inbox')
def inbox(source:str=Query(default='original',pattern='^(original|synthetic)$'),facility:str='all',
          status:str=Query(default='all',pattern='^(all|read|unread)$'),category:str='all',
          offset:int=Query(default=0,ge=0),limit:int=Query(default=20,ge=1,le=300),user=Depends(current_user)):
    records_for_role=list_notifications(user)
    with connect() as con:
        read={r[0] for r in con.execute('SELECT notification_key FROM notification_reads WHERE user_id=?',(user['id'],))}
    items=[]
    for record in records_for_role:
        if record.get('source')!=source or (facility!='all' and record.get('facility')!=facility):continue
        for reason in record['reasons']:
            title,tab,item_category=describe(reason)
            key=hashlib.sha256(f"{record['patient_id']}|{reason}|{record.get('occurred_at') or ''}".encode()).hexdigest()
            items.append({'id':key,'patient_id':record['patient_id'],'patient_no':record.get('patient_no'),
                          'title':title,'body':reason,'category':item_category,'tab':tab,'read':key in read,'occurred_at':record.get('occurred_at')})
    items.sort(key=lambda item:(item['occurred_at'] or '',item['id']),reverse=True)
    unread=sum(not item['read'] for item in items)
    filtered=[item for item in items if (status=='all' or item['read']==(status=='read')) and (category=='all' or item['category']==category)]
    return {'items':filtered[offset:offset+limit],'unread_count':unread,'total':len(filtered)}


class ReadNotifications(BaseModel):
    ids:list[str]=Field(min_length=1,max_length=300)
    read:bool=True


@router.patch('/read')
def read_notifications(data:ReadNotifications,user=Depends(current_user)):
    if any(not re.fullmatch('[a-f0-9]{64}',key) for key in data.ids):raise DomainError('Invalid notification identifier.')
    with connect() as con:
        if data.read:
            con.executemany('INSERT INTO notification_reads(user_id,notification_key,read_at) VALUES(?,?,?) ON CONFLICT(user_id,notification_key) DO UPDATE SET read_at=excluded.read_at',[(user['id'],key,now()) for key in data.ids])
        else:
            con.executemany('DELETE FROM notification_reads WHERE user_id=? AND notification_key=?',[(user['id'],key) for key in data.ids])
    return {'ok':True}
