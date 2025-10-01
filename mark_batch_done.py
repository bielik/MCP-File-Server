import sqlite3
conn = sqlite3.connect('data/database.db')
cur = conn.cursor()
cur.execute("""UPDATE reindex_batches SET status='completed' WHERE id='5f2cc8d7-fca6-4e2a-b0de-d3d1c5d326a0'""")
conn.commit()
conn.close()
