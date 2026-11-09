import sqlite3
from datetime import datetime, timezone
from .config import DB

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class ClosingConnection(sqlite3.Connection):

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect():
    con = sqlite3.connect(DB, factory=ClosingConnection)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con
