import sqlite3
import json

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
print('tables:', [r[0] for r in cur.fetchall()])
cur.execute("PRAGMA table_info('store_pendingmetadata')")
cols = cur.fetchall()
print('schema:', cols)
conn.close()
