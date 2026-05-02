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

TEMPLATE_SHEET_NAME = "QuanLyViTienCat"


def send_email(subject, body, image_path=None):
    try:
        yag = yagmail.SMTP(user=os.getenv("SENDER_EMAIL"), password=os.getenv("EMAIL_PASSWORD"))
        contents = [body]
        if image_path:
            contents.append(image_path)
        yag.send(to=os.getenv("RECEIVER_EMAIL"), subject=subject, contents=contents)
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")


def setup_google_sheets():
    """Khởi tạo kết nối Google Sheets và trả về đối tượng Spreadsheet."""
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


def get_or_create_worksheet(spreadsheet, sheet_name):
    """
    Lấy worksheet theo tên. Nếu chưa tồn tại, tự động clone từ tab 'Template'.
    Giúp loại bỏ hoàn toàn việc tạo spreadsheet mới mỗi tháng.
    """
    try:
        # Thử lấy worksheet đã tồn tại
        ws = spreadsheet.worksheet(sheet_name)
        print(f"[INFO] Đã tìm thấy worksheet '{sheet_name}'")
        return ws
    except gspread.exceptions.WorksheetNotFound:
        print(f"[INFO] Worksheet '{sheet_name}' chưa tồn tại, tiến hành tạo mới từ template...")

    # Lấy tab Template
    try:
        template_ws = spreadsheet.worksheet(TEMPLATE_SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        raise Exception(
            f"Tab '{TEMPLATE_SHEET_NAME}' không tồn tại trong spreadsheet! "
            f"Vui lòng tạo tab 'QuanLyViTienCat' với format chuẩn trước khi sử dụng."
        )

    # Duplicate tab Template sang sheet mới (trong cùng spreadsheet)
    try:
        body = {"destinationSpreadsheetId": spreadsheet.id}
        result = spreadsheet.client.copy(
            template_ws.id,
            spreadsheet_id=spreadsheet.id,
            dest_spreadsheet_id=spreadsheet.id,
        )
        new_sheet_id = result["sheetId"]
    except Exception as e:
        raise Exception(f"Lỗi khi duplicate template: {str(e)}")

    # Đổi tên tab mới thành sheet_name
    try:
        new_ws = spreadsheet.get_worksheet_by_id(new_sheet_id)
        new_ws.update_title(sheet_name)
        print(f"[INFO] Đã tạo worksheet mới: '{sheet_name}' từ template")
        return new_ws
    except Exception as e:
        raise Exception(f"Lỗi khi đổi tên worksheet: {str(e)}")


@app.route('/write', methods=['POST'])
def write_sheet():
    vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    current_time = datetime.now(vn_timezone)
    formatted_date = current_time.strftime("%d.%m")

    try:
        spreadsheet = setup_google_sheets()
        sheet = get_or_create_worksheet(spreadsheet, formatted_date)
        print(f"[INFO] Đang ghi vào worksheet '{formatted_date}'")
    except Exception as e:
        error_message = f"Error during Google Sheets setup: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

    try:
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

        for i in range(start_row - 1, len(all_values)):
            if i + 1 < len(all_values) and 'Tổng' in all_values[i + 1]:
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

        last_column_letter = chr(65 + len(values) - 1)
        cell_range = f"A{row_index}:{last_column_letter}{row_index}"
        sheet.update(cell_range, [values])

    except Exception as e:
        error_message = f"Error updating sheet: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

    try:
        subject = f"Nhân viên {data.get('nhan_vien')}"
        body = (
            f"Khách hàng {data.get('khach_hang')} đã thanh toán "
            f"{'chuyển khoản: ' + str(tienNganHang) if tienNganHang != 0 else ''} "
            f"{'tiền mặt: ' + str(tienMat) if tienMat != 0 else ''}"
        )
        image_path = "assets/vitiencat.jpg"
        send_email(subject, body, image_path)
    except Exception as e:
        error_message = f"Error sending email notification: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

    return jsonify({"message": f"Thêm hàng {row_index} thành công vào ngày {formatted_date}"})


@app.route('/setup-month', methods=['POST'])
def setup_month():
    """
    Endpoint để admin chủ động tạo trước tab cho ngày hôm nay (hoặc ngày chỉ định).
    Body (tùy chọn): { "date": "DD.MM" }
    """
    try:
        data = request.get_json(force=True) or {}
        target_date = data.get("date")

        if not target_date:
            vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
            target_date = datetime.now(vn_timezone).strftime("%d.%m")

        spreadsheet = setup_google_sheets()
        ws = get_or_create_worksheet(spreadsheet, target_date)

        return jsonify({
            "message": f"Worksheet '{target_date}' đã sẵn sàng",
            "sheet_title": ws.title,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Kiểm tra kết nối Google Sheets và liệt kê các tab hiện có."""
    try:
        spreadsheet = setup_google_sheets()
        worksheets = [ws.title for ws in spreadsheet.worksheets()]
        return jsonify({
            "status": "ok",
            "spreadsheet_title": spreadsheet.title,
            "worksheets": worksheets,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    formatted_date = datetime.now(vn_timezone).strftime("%d.%m")
    return jsonify({"message": "Hello from Flask!", "current_sheet_tab": formatted_date})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 9090))
    app.run(host="0.0.0.0", port=port)
