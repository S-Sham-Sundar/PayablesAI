import sqlite3

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

cursor.execute("""
DELETE FROM invoices
WHERE id = 8
""")

conn.commit()

conn.close()

cursor.execute("""
CREATE TABLE IF NOT EXISTS correction_logs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    invoice_id INTEGER,

    field_name TEXT,

    old_value TEXT,

    new_value TEXT,

    reason TEXT,

    edited_at TEXT

)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS audit_logs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    invoice_id INTEGER,

    action TEXT,

    details TEXT,

    created_at TEXT

)
""")