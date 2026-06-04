import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""

PRAGMA table_info(invoices)

""")

for row in cursor.fetchall():

    print(row)

conn.close()