import sqlite3

conn = sqlite3.connect(
    "invoices.db"
)

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE invoices
ADD COLUMN due_status TEXT
""")

conn.commit()

conn.close()

print("Due Status column added")