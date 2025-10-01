import sqlite3
conn=sqlite3.connect('file:/data/database.db?mode=rw', uri=True)
row=conn.execute("SELECT created_at, started_at, completed_at FROM reindex_batches WHERE id=\'41b0ca48-34d7-4ad9-9ff9-ca0332a04f0a\'").fetchone()
print(row)
conn.close()
