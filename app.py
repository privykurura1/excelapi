from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pdfplumber
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_dynamic_table(pdf):
    extracted_data = []
    
    for page in pdf.pages:
        table = page.extract_table()
        if table:
            headers = table[0]  # First row as headers
            for row in table[1:]:  # Skip header row
                if len(row) == len(headers):  # Ensure row consistency
                    extracted_data.append(dict(zip(headers, row)))
    
    return pd.DataFrame(extracted_data) if extracted_data else pd.DataFrame()

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
            extracted_df = extract_dynamic_table(pdf)
            
            if extracted_df.empty:
                return jsonify({"error": "No tabular data found in the PDF"}), 400
            
            # Save extracted data to Excel
            excel_path = os.path.join(UPLOAD_FOLDER, "converted.xlsx")
            extracted_df.to_excel(excel_path, sheet_name="Extracted Data", index=False)
            
            return send_file(excel_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
