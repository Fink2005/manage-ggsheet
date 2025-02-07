from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import json
from dotenv import load_dotenv
import os
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import yagmail
# Load environment variables
load_dotenv()
app = Flask(__name__)
CORS(app)


def send_email(subject, body, image_path=None):
    try:
        # Connect to Gmail SMTP
        yag = yagmail.SMTP(user=os.getenv("SENDER_EMAIL"), password=os.getenv("EMAIL_PASSWORD"))
        contents = [body]
        if image_path:
            contents.append(image_path)
        yag.send(to=os.getenv("RECEIVER_EMAIL"), subject=subject, contents=contents)
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def setup_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("GOOGLE_CREDENTIALS_JSON environment variable not set.")
    
    try:
        creds_info = json.loads(credentials_json)
    except Exception as e:
        raise Exception("Error parsing GOOGLE_CREDENTIALS_JSON: " + str(e))
    
    try:
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    except Exception as e:
        raise Exception("Error creating credentials: " + str(e))
    
    client = gspread.authorize(creds)
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id:
        raise Exception("SHEET_ID environment variable not set.")
    
    return client.open_by_key(sheet_id)

@app.route('/write', methods=['POST'])
def write_sheet():
# Format the date as "DD.MM"
    vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    current_time = datetime.now(vn_timezone)
    formatted_date = current_time.strftime("%d.%m")
    try:
        # Setup Google Sheets and get the worksheet "sheet2"
        sheet = setup_google_sheets().worksheet(formatted_date)
        print(sheet.get_all_values())
        print(sheet)
    except Exception as e:
        error_message = f"Error during Google Sheets setup: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

    try:
        # Retrieve JSON payload; force=True ensures it tries to parse the body as JSN
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
    except Exception as e:
        error_message = f"Error reading JSON data: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 400

    try:
        start_row = 6
        all_values = sheet.get_all_values()
        row_index = start_row

        # Check for an empty row or for a row containing 'Tổng
        for i in range(start_row - 1, len(all_values)):
              if 'Tổng' in all_values[i + 1]:
                row_index = i + 1
                sheet.insert_row([], row_index)
                sum_formula = f"=SUM(G{start_row + 1}:G{row_index + 1})"
                sum_formula2 = f"=SUM(H{start_row + 1}:H{row_index + 1})"
                sheet.update_cell(row_index + 2, 7, sum_formula)
                sheet.update_cell(row_index + 2, 8, sum_formula2)
                break
              if len(sheet.row_values(i + 1)) == 0:
                    row_index = i + 1
                    break
          
    except Exception as e:
        error_message = f"Error processing rows: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

    try:
        # Convert numeric fields safe
        tienMat = int(data.get("tien_mat")) if data.get("tien_mat") is not None else 0
        tienNganHang = int(data.get("chuyen_khoan")) if data.get("chuyen_khoan") is not None else 0

        # Prepare the row values
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
        
        # Determine the cell range to update (e.g., A{row_index} to K{row_index})
        last_column_letter = chr(65 + len(values) - 1)  # 65 is ASCII for 'A'
        cell_range = f"A{row_index}:{last_column_letter}{row_index}"
        
        # Update the sheet with the values
        sheet.update(cell_range, [values])
    except Exception as e:
        error_message = f"Error updating sheet: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500
    
    try:
        subject = f"Nhân viên {data.get("nhan_vien")}"
        body = f"khách hàng {data.get("khach_hang")} đã thanh toán {'chuyển khoản: ' + str(tienNganHang) if tienNganHang != 0 else ''} {'tiền mặt: ' + str(tienMat) if tienMat != 0 else ''}"
        image_path="assets/vitiencat.jpg"
        send_email(subject, body, image_path)
    except Exception as e:
        error_message = f"Error sending email notification: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500   
    # Return a successful JSON response
    return jsonify({"message": f"Thêm hàng {row_index} thành công vào ngày {formatted_date}"})

@app.route('/', methods=['GET'])
def index():
    today = datetime.now()
# Format the date as "DD.MM"
    formatted_date = today.strftime("%d.%m")
    print(formatted_date)
    return jsonify({"message": "Hello from Flask!"})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 9090))
    app.run(host="0.0.0.0", port=port)
