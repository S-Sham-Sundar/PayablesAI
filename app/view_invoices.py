import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
SELECT *
FROM invoices
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()