from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pdfplumber
import pandas as pd
import os
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_transaction_data(pdf):
    transactions = []
    pattern = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(.*?)\s+([A-Za-z0-9_ ]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.-]+)$')
    
    for page in pdf.pages:
        lines = page.extract_text().split("\n") if page.extract_text() else []
        
        for line in lines:
            match = pattern.match(line)
            if match:
                transactions.append({
                    "Date": match.group(1),
                    "Reference": match.group(2),
                    "Description": match.group(3),
                    "Debit": match.group(4),
                    "Credit": match.group(5),
                    "Balance": match.group(6)
                })
    
    return pd.DataFrame(transactions) if transactions else pd.DataFrame()

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    try:
        with pdfplumber.open(file_path) as pdf:
            transactions_df = extract_transaction_data(pdf)
            
            if transactions_df.empty:
                return jsonify({"error": "No structured data found in the PDF"}), 400
            
            excel_path = os.path.join(UPLOAD_FOLDER, "converted.xlsx")
            transactions_df.to_excel(excel_path, sheet_name="Transactions", index=False)
            
            return send_file(excel_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
