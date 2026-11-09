import json
from ..core.database import now

def audit(con, user, action, entity, before=None, after=None):
    con.execute('INSERT INTO audit(actor,role,action,entity,before_json,after_json,created_at) VALUES(?,?,?,?,?,?,?)', (user['name'], user['role'], action, str(entity), json.dumps(before), json.dumps(after), now()))
