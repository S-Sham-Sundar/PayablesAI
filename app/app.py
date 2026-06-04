import os
import fitz
import google.generativeai as genai

# GEMINI CONFIGURATION

from dotenv import load_dotenv

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")

# FOLDERS

INVOICE_FOLDER = "invoices"
OUTPUT_FOLDER = "outputs"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# PROCESS ALL PDFS

for filename in os.listdir(INVOICE_FOLDER):

    if not filename.endswith(".pdf"):
        continue

    pdf_path = os.path.join(INVOICE_FOLDER, filename)

    print(f"\nProcessing: {filename}")

    # Extract PDF Text

    pdf = fitz.open(pdf_path)

    all_text = ""

    for page in pdf:
        all_text += page.get_text()

    pdf.close()

    print("Text extracted successfully")

    
    # Prompt

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

    # Gemini Call
    

    response = model.generate_content(prompt)

    clean_json = (
        response.text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    # Save JSON

    output_filename = filename.replace(".pdf", ".json")

    output_path = os.path.join(
        OUTPUT_FOLDER,
        output_filename
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(clean_json)

    print(f"Saved: {output_filename}")

print("\nAll invoices processed successfully!")