import sqlite3
conn = sqlite3.connect('f:/012A_Github/choppingblock/backend_engine/database/ledger.db')
conn.row_factory = sqlite3.Row
r = conn.execute("SELECT agent_id, toolconfigs FROM Agent_Status WHERE agent_id='god'").fetchone()
print('RAW toolconfigs:', dict(r)['toolconfigs'])
conn.close()
