import sys
import os
import json
sys.path.insert(0, 'f:/012A_Github/choppingblock/backend_engine')
from database.db_manager import get_fernet

def read_db():
    import sqlite3
    conn = sqlite3.connect('f:/012A_Github/choppingblock/backend_engine/database/ledger.db')
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT agent_id, toolconfigs FROM Agent_Status WHERE agent_id='god'").fetchone()
    conn.close()
    
    val = dict(r)['toolconfigs']
    print("Raw from DB:", val)
    
    f = get_fernet()
    try:
        dec = f.decrypt(val.encode()).decode()
        print("Decrypted raw string:", dec)
        print("Parsed JSON:", json.loads(dec))
    except Exception as e:
        print("Decryption failed:", str(e))

read_db()
