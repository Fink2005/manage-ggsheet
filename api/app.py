from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import json
from dotenv import load_dotenv
import os
from google.oauth2.service_account import Credentials
load_dotenv()
app = Flask(__name__)
CORS(app) 
# Google Sheets Setup
def setup_google_sheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    creds = Credentials.from_service_account_info(json.loads(credentials_json), scopes=scope)
    client = gspread.authorize(creds)
    sheet_id = os.getenv("SHEET_ID")
    return client.open_by_key(sheet_id)
@app.route('/write', methods=['POST'])
def write_sheet():
    sheet = setup_google_sheets().worksheet("sheet2")  # Ensure you're working with the correct sheet
    data = request.json

    # Star checking from ro 
    start_row = 6
    all_values = sheet.get_all_values()
    row_index = start_row

    # Check for 'Tổng' in the rows
    for i in range(start_row - 1, len(all_values)):  # -1 because list index starts at 0
        if len(sheet.row_values(i + 1)) == 0:
             row_index = i + 1
             break
        if 'Tổng' in all_values[i]:  # Check if 'Tổng' is in the row
            row_index = i + 1  # Insert a new row above the row containing 'Tổng'

            # Insert a blank row
            sheet.insert_row([], row_index)
            # Generate a new SUM formula for the 'Tổng' row
            sum_formula = f"=SUM(G{start_row}:G{row_index})"
            sum_formula2 = f"=SUM(H{start_row}:H{row_index})"
            sheet.update_cell(row_index + 1, 7, sum_formula)  # Reapply the formula in the updated position
            sheet.update_cell(row_index + 1, 8, sum_formula2)  
            break


    
    # Update the specific row with the provided data
    tienMat = int(data.get("tien_mat")) if data.get("tien_mat") is not None else 0
    tienNganHang = int(data.get("chuyen_khoan")) if data.get("chuyen_khoan") is not None else 0
    
    
    
    values = [
        data.get("so_hd"),
        data.get("khach_hang"),
        data.get("dv_duong_sinh"),
        data.get("the_dv"),
        data.get("dv_spa"),
        data.get("dv_nail"),
        tienMat,
        tienNganHang,
        data.get("the_dv_t"),
        data.get("nhan_vien"),
        data.get("ghi_chu"),
    ]
    sheet.update(f"A{row_index}:{chr(65 + len(values) - 1)}{row_index}", [values])

    return jsonify({"message": f"Thêm hàng thành công."})

@app.route('/', methods=['GET'])
def hehe():
    a = os.getenv("SHEET_ID")
    b = os.getenv("GOOGLE_CREDENTIALS_JSON")
    return jsonify({"message": f"{a}{b}"})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 9090))
    app.run(host="0.0.0.0", port=port)
