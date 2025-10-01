import sqlite3, datetime
conn=sqlite3.connect('file:/data/database.db?mode=rw', uri=True)
iso=datetime.datetime.utcnow().isoformat()
conn.execute("UPDATE reindex_batches SET completed_at=? WHERE id=\'41b0ca48-34d7-4ad9-9ff9-ca0332a04f0a\'", (iso,))
conn.commit()
conn.close()
print('iso', iso)
