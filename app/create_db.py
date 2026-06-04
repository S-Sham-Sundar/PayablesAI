import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_name TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    due_date TEXT,
    currency TEXT,
    subtotal TEXT,
    tax_amount TEXT,
    total_amount TEXT
)
""")

conn.commit()

conn.close()

print("Database created successfully!")