import os
import json
import sqlite3

# ==========================================
# DATABASE CONNECTION
# ==========================================

conn = sqlite3.connect("invoices.db")

cursor = conn.cursor()

# ==========================================
# JSON FOLDER
# ==========================================

OUTPUT_FOLDER = "outputs"

# ==========================================
# READ ALL JSON FILES
# ==========================================

for filename in os.listdir(OUTPUT_FOLDER):

    if not filename.endswith(".json"):
        continue

    json_path = os.path.join(
        OUTPUT_FOLDER,
        filename
    )

    with open(json_path, "r", encoding="utf-8") as f:
        invoice = json.load(f)

    print(f"Loading {filename}")

    # ======================================
    # INSERT INTO DATABASE
    # ======================================

    cursor.execute("""
    INSERT INTO invoices (
        vendor_name,
        invoice_number,
        invoice_date,
        due_date,
        currency,
        subtotal,
        tax_amount,
        total_amount
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice.get("vendor_name"),
        invoice.get("invoice_number"),
        invoice.get("invoice_date"),
        invoice.get("due_date"),
        invoice.get("currency"),
        invoice.get("subtotal"),
        invoice.get("tax_amount"),
        invoice.get("total_amount")
    ))

# ==========================================
# SAVE CHANGES
# ==========================================

conn.commit()

# ==========================================
# CLOSE DATABASE
# ==========================================

conn.close()

print("\nAll invoices inserted successfully!")