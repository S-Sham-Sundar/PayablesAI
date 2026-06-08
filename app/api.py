from fastapi import FastAPI
import sqlite3
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
import shutil
import os
import fitz
import json
import google.generativeai as genai
import pandas as pd
from fastapi.responses import FileResponse
from datetime import datetime
from fastapi import Body
from dotenv import load_dotenv
load_dotenv()
genai.configure(
    api_key=os.getenv(

        "GEMINI_API_KEY"

    )
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)
app = FastAPI()
UPLOAD_FOLDER = "uploaded_invoices"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)
def create_audit_log(
    invoice_id,
    action,
    details
):

    conn = sqlite3.connect(
        "invoices.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO audit_logs (
        invoice_id,
        action,
        details,
        created_at
    )
    VALUES (?, ?, ?, ?)
    """, (

        invoice_id,

        action,

        details,

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    ))

    conn.commit()

    conn.close()
@app.get("/invoices")
def get_invoices():

    conn = sqlite3.connect("invoices.db")

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        vendor_name,
        invoice_number,
        total_amount,
        currency,
        status,
        due_date,
        reject_reason,
        confidence_score,
        validation_notes
    FROM invoices
    """)

    rows = cursor.fetchall()

    conn.close()

    invoices = []

    for row in rows:
        due_date_text = row[6]

        due_status = "Unknown"

        formats = [

            "%B %d, %Y",

            "%d %B %Y",

            "%d-%b-%Y",

            "%d/%m/%Y"

        ]

        for fmt in formats:

            try:

                due_date = datetime.strptime(

                    due_date_text,

                    fmt

                )

                today = datetime.today()

                days_left = (

                    due_date - today

                ).days

                if days_left < 0:

                    due_status = "Overdue"

                elif days_left <= 7:

                    due_status = "Due Soon"

                else:

                    due_status = "Active"

                break

            except:

                pass
        invoices.append({
            "id": row[0],
            "vendor_name": row[1],
            "invoice_number": row[2],
            "total_amount": row[3],
            "currency": row[4],
            "status": row[5],
            "due_status": due_status,
            "reject_reason": row[7],
            "confidence_score": row[8],
            "validation_notes": row[9]
        })

    return invoices

@app.get("/top-invoices")
def top_invoices():

    conn = sqlite3.connect("invoices.db")

    cursor = conn.cursor()

    cursor.execute("""
    SELECT vendor_name,
           total_amount
    FROM invoices
    ORDER BY CAST(total_amount AS REAL) DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def evaluate_invoice(invoice):

    prompt = f"""
You are an invoice validation expert.

Review this invoice JSON.

Invoice:

{json.dumps(invoice, indent=2)}

Check:

1. Invoice number format
2. Vendor name quality
3. Date validity
4. Currency validity
5. Amount consistency
and also
You are a senior AP auditor.

Review the extracted invoice.

Consider taxes, discounts, freight charges,

handling fees, insurance fees and any other

charges mentioned in the invoice.

Determine whether the final amount appears

mathematically consistent.
Return ONLY valid JSON.

{{
    "confidence_score": 95,
    "validation_notes": "Invoice appears valid"
}}
"""

    response = model.generate_content(prompt)

    clean_json = (
        response.text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    return json.loads(clean_json)

@app.post("/upload")
async def upload_invoice(
    file: UploadFile = File(...)
):

    # =====================================
    # SAVE PDF
    # =====================================

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(file_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    print("PDF uploaded")

    # =====================================
    # EXTRACT TEXT
    # =====================================

    pdf = fitz.open(file_path)

    all_text = ""

    for page in pdf:
        all_text += page.get_text()

    pdf.close()

    print("Text extracted")

    # =====================================
    # GEMINI PROMPT
    # =====================================

    prompt = f"""
You are an invoice extraction assistant.

Extract the following fields.

Return ONLY valid JSON.

{{
    "vendor_name": "",
    "invoice_number": "",
    "invoice_date": "",
    "due_date": "",
    "currency": "",
    "subtotal": "",
    "tax_amount": "",
    "total_amount": ""
}}

Invoice Text:

{all_text}
"""

    # =====================================
    # GEMINI
    # =====================================

    response = model.generate_content(
        prompt
    )

    clean_json = (
        response.text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    invoice = json.loads(
        clean_json
    )
    evaluation = evaluate_invoice(
        invoice
    )

    confidence_score = evaluation[
        "confidence_score"
    ]

    validation_notes = evaluation[
        "validation_notes"
    ]

    print("Gemini extraction completed")

    # =====================================
    # INSERT INTO DATABASE
    # =====================================

    conn = sqlite3.connect(
        "invoices.db"
    )
    cursor = conn.cursor()
    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE invoice_number = ?
    """, (
        invoice.get("invoice_number"),
    ))

    count = cursor.fetchone()[0]

    if count > 0:

        conn.close()

        return {
            "message":
            "Duplicate invoice detected"
        }

    cursor.execute("""
    INSERT INTO invoices (
        vendor_name,
        invoice_number,
        invoice_date,
        due_date,
        currency,
        subtotal,
        tax_amount,
        total_amount,
        pdf_path,
        confidence_score,
        validation_notes
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        invoice.get("vendor_name"),
        invoice.get("invoice_number"),
        invoice.get("invoice_date"),
        invoice.get("due_date"),
        invoice.get("currency"),
        invoice.get("subtotal"),
        invoice.get("tax_amount"),
        invoice.get("total_amount"),
        file_path,
        confidence_score,
        validation_notes

    ))

    invoice_id = cursor.lastrowid

    conn.commit()

    conn.close()

    create_audit_log(
        invoice_id,
        "UPLOAD",
        "Invoice uploaded successfully"
    )

    create_audit_log(
        invoice_id,
        "VALIDATION",
        f"Confidence Score = {confidence_score}"
    )
    print("Inserted into database")

    return {
        "message":
        f"{file.filename} processed successfully"
    }

@app.delete("/invoice/{invoice_id}")
def delete_invoice(invoice_id: int):

    conn = sqlite3.connect("invoices.db")

    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM invoices
    WHERE id = ?
    """, (invoice_id,))

    conn.commit()

    conn.close()

    return {
        "message":
        f"Invoice {invoice_id} deleted"
    }

@app.get("/invoice/{invoice_id}")
def get_invoice(invoice_id: int):

    conn = sqlite3.connect("invoices.db")

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM invoices
    WHERE id = ?
    """, (invoice_id,))

    row = cursor.fetchone()

    conn.close()

    if not row:
        return {
            "message": "Invoice not found"
        }

    return {
        "id": row[0],
        "vendor_name": row[1],
        "invoice_number": row[2],
        "invoice_date": row[3],
        "due_date": row[4],
        "currency": row[5],
        "subtotal": row[6],
        "tax_amount": row[7],
        "total_amount": row[8],
        "status": row[9],
        "due_status": row[10],
        "reject_reason": row[11],
        "pdf_path": row[12],
        "confidence_score": row[13],
        "validation_notes": row[14]
    }

@app.get("/stats")
def get_stats():

    conn = sqlite3.connect("invoices.db")

    cursor = conn.cursor()

    # =========================
    # TOTAL INVOICES
    # =========================

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    """)

    total_invoices = cursor.fetchone()[0]

    # =========================
    # CURRENCY COUNTS
    # =========================

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE currency = 'USD'
    """)

    usd_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE currency = 'INR'
    """)

    inr_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE currency = 'EUR'
    """)

    eur_count = cursor.fetchone()[0]

    # =========================
    # CURRENCY TOTALS
    # =========================

    cursor.execute("""
    SELECT SUM(CAST(total_amount AS REAL))
    FROM invoices
    WHERE currency = 'USD'
    """)

    usd_total = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT SUM(CAST(total_amount AS REAL))
    FROM invoices
    WHERE currency = 'INR'
    """)

    inr_total = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT SUM(CAST(total_amount AS REAL))
    FROM invoices
    WHERE currency = 'EUR'
    """)

    eur_total = cursor.fetchone()[0] or 0

    # =========================
    # STATUS COUNTS
    # =========================

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE status = 'Pending'
    """)

    pending_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE status = 'Approved'
    """)

    approved_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM invoices
    WHERE status = 'Rejected'
    """)

    rejected_count = cursor.fetchone()[0]

    # =========================
    # DUE STATUS COUNTS
    # =========================

    overdue_count = 0
    due_soon_count = 0
    active_count = 0

    cursor.execute("""
    SELECT due_date
    FROM invoices
    """)

    rows = cursor.fetchall()

    formats = [
        "%B %d, %Y",
        "%d %B %Y",
        "%d-%b-%Y",
        "%d/%m/%Y"
    ]

    for row in rows:

        due_date_text = row[0]

        for fmt in formats:

            try:

                due_date = datetime.strptime(
                    due_date_text,
                    fmt
                )

                days_left = (
                    due_date -
                    datetime.today()
                ).days

                if days_left < 0:
                    overdue_count += 1

                elif days_left <= 7:
                    due_soon_count += 1

                else:
                    active_count += 1

                break

            except:
                pass

    conn.close()

    return {

        "total_invoices": total_invoices,

        "usd_count": usd_count,
        "inr_count": inr_count,
        "eur_count": eur_count,

        "usd_total": round(usd_total, 2),
        "inr_total": round(inr_total, 2),
        "eur_total": round(eur_total, 2),

        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,

        "overdue_count": overdue_count,
        "due_soon_count": due_soon_count,
        "active_count": active_count
    }

@app.put("/approve/{invoice_id}")
def approve_invoice(invoice_id: int):

    conn = sqlite3.connect(
        "invoices.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE invoices
    SET status = 'Approved'
    WHERE id = ?
    """, (invoice_id,))

    conn.commit()

    conn.close()

    create_audit_log(
        invoice_id,
        "APPROVED",
        "Invoice approved"
    )

    return {
        "message":
        "Invoice Approved"
    }

@app.get("/export")
def export_excel():

    conn = sqlite3.connect(
        "invoices.db"
    )

    query = """
    SELECT *
    FROM invoices
    """

    df = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    file_name = "invoice_export.xlsx"

    df.to_excel(
        file_name,
        index=False
    )

    return FileResponse(
        path=file_name,
        filename=file_name,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.put("/reject/{invoice_id}")
def reject_invoice(
    invoice_id: int,
    reason: str = Body(...)
):

    conn = sqlite3.connect(
        "invoices.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE invoices
    SET
        status = 'Rejected',
        reject_reason = ?
    WHERE id = ?
    """, (
        reason,
        invoice_id
    ))

    conn.commit()

    conn.close()

    create_audit_log(
        invoice_id,
        "REJECTED",
        reason
    )

    return {
        "message":
        "Invoice rejected"
    }
@app.put("/invoice/{invoice_id}")
def update_invoice(
    invoice_id: int,
    data: dict = Body(...)
):

    conn = sqlite3.connect(
        "invoices.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE invoices
    SET
        vendor_name = ?,
        total_amount = ?,
        due_date = ?
    WHERE id = ?
    """, (

        data["vendor_name"],

        data["total_amount"],

        data["due_date"],

        invoice_id

    ))

    conn.commit()

    conn.close()

    return {
        "message":
        "Invoice updated"
    }
@app.get("/audit/{invoice_id}")
def get_audit_logs(
    invoice_id: int
):

    conn = sqlite3.connect(
        "invoices.db"
    )

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        action,
        details,
        created_at
    FROM audit_logs
    WHERE invoice_id = ?
    ORDER BY id DESC
    """, (invoice_id,))

    rows = cursor.fetchall()

    conn.close()

    logs = []

    for row in rows:

        logs.append({
            "action": row[0],
            "details": row[1],
            "created_at": row[2]
        })

    return logs

@app.get("/pdf/{invoice_id}")
def get_pdf(invoice_id: int):

    conn = sqlite3.connect("invoices.db")

    cursor = conn.cursor()

    cursor.execute("""
    SELECT pdf_path
    FROM invoices
    WHERE id = ?
    """, (invoice_id,))

    row = cursor.fetchone()

    conn.close()

    if not row:
        return {
            "message": "PDF not found"
        }

    return FileResponse(
        row[0],
        media_type="application/pdf"
    )