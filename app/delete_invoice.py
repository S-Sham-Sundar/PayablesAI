import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
DELETE FROM invoices
WHERE id = 8
""")

conn.commit()

conn.close()

print("Invoice deleted successfully")