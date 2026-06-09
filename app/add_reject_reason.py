
import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE invoices
ADD COLUMN reject_reason TEXT
""")

conn.commit()
conn.close()

print("Column added")