import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE invoices
ADD COLUMN status TEXT DEFAULT 'Pending'
""")

conn.commit()

conn.close()

print("Status column added!")