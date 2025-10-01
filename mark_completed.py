import sqlite3
conn = sqlite3.connect('data/database.db')
cur = conn.cursor()
cur.execute("""UPDATE index_jobs SET status='completed', completed_at=strftime('%s','now') WHERE id IN (161,171,176)""")
conn.commit()
conn.close()
