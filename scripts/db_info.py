import sqlite3
con = sqlite3.connect('clinic.db')
cur = con.cursor()
cur.execute("PRAGMA table_info('appointments')")
print(cur.fetchall())
cur.close()
con.close()