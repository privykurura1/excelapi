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


def extract_text_as_columns(pdf):
    data = {}
    all_text = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            all_text.append(text)
            lines = text.split("\n")
            for line in lines:
                if re.match(r'^[A-Z].+:', line):  # Detect headings
                    key, value = line.split(":", 1)
                    data.setdefault(key.strip(), []).append(value.strip())

    df_text = pd.DataFrame({"Text Content": all_text})
    df_headings = pd.DataFrame.from_dict(data, orient='index').transpose()

    return df_text, df_headings


def extract_table(pdf):
    tables = []
    for page in pdf.pages:
        table = page.extract_table()
        if table:
            df = pd.DataFrame(table[1:], columns=table[0])
            tables.append(df)
    return pd.concat(tables, ignore_index=True) if tables else None


def extract_form(pdf):
    data = {}
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            lines = text.split("\n")
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key, value = parts
                    data[key.strip()] = value.strip()
    return pd.DataFrame(list(data.items()), columns=["Field", "Value"])


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
            table_df = extract_table(pdf)
            text_df, headings_df = extract_text_as_columns(pdf)
            form_df = extract_form(pdf)

            # Save all extracted data to Excel
            excel_path = os.path.join(UPLOAD_FOLDER, "converted.xlsx")
            with pd.ExcelWriter(excel_path) as writer:
                if table_df is not None and not table_df.empty:
                    table_df.to_excel(writer, sheet_name="Tables", index=False)
                if not text_df.empty:
                    text_df.to_excel(writer, sheet_name="Text", index=False)
                if not headings_df.empty:
                    headings_df.to_excel(writer, sheet_name="Headings", index=False)
                if not form_df.empty:
                    form_df.to_excel(writer, sheet_name="Forms", index=False)

            return send_file(excel_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
