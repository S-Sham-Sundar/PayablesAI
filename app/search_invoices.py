import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
SELECT
    vendor_name,
    total_amount
FROM invoices
ORDER BY CAST(total_amount AS REAL) DESC
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()