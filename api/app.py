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

load_dotenv()
app = Flask(__name__)
CORS(app)

TEMPLATE_SHEET_NAME = "QuanLyViTienCat"
CONFIG_SHEET_NAME = "Config"


# ─────────────────────────────────────────────
# Google Sheets helpers
# ─────────────────────────────────────────────

def setup_google_client():
    """Khởi tạo Google Sheets client với scope Drive + Sheets."""
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",  # cần để tạo spreadsheet mới
    ]
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("GOOGLE_CREDENTIALS_JSON environment variable not set.")

    try:
        creds_info = json.loads(credentials_json)
    except Exception as e:
        raise Exception("Error parsing GOOGLE_CREDENTIALS_JSON: " + str(e))

    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)


def get_year_spreadsheet(client, year):
    """
    Lấy spreadsheet của năm từ registry (tab Config).
    Nếu chưa có → tự tạo spreadsheet mới + clone template + đăng ký vào Config.
    """
    master_id = os.getenv("MASTER_SHEET_ID")
    if not master_id:
        raise Exception("MASTER_SHEET_ID environment variable not set.")

    master = client.open_by_key(master_id)

    # Đọc registry Config
    config_ws = master.worksheet(CONFIG_SHEET_NAME)
    records = config_ws.get_all_values()  # [[Year, SpreadsheetID], ...]

    for row in records[1:]:  # bỏ qua header row
        if len(row) >= 2 and row[0] == str(year):
            print(f"[INFO] Tìm thấy spreadsheet năm {year}: {row[1]}")
            return client.open_by_key(row[1])

    # Chưa có → tạo mới
    print(f"[INFO] Chưa có spreadsheet năm {year}, tiến hành tạo mới...")

    # 1. Tạo spreadsheet mới
    new_spreadsheet = client.create(f"Vi Tien Cat - Doanh Thu {year}")
    print(f"[INFO] Đã tạo spreadsheet: {new_spreadsheet.id}")

    # 2. Clone tab QuanLyViTienCat từ master sang spreadsheet mới
    template_ws = master.worksheet(TEMPLATE_SHEET_NAME)
    result = template_ws.copy_to(new_spreadsheet.id)
    copied_ws = new_spreadsheet.get_worksheet_by_id(result["sheetId"])
    copied_ws.update_title(TEMPLATE_SHEET_NAME)
    print(f"[INFO] Đã clone tab '{TEMPLATE_SHEET_NAME}' sang spreadsheet mới")

    # 3. Xóa tab mặc định "Sheet1" nếu còn
    try:
        default_ws = new_spreadsheet.worksheet("Sheet1")
        new_spreadsheet.del_worksheet(default_ws)
    except gspread.exceptions.WorksheetNotFound:
        pass

    # 4. Đăng ký vào Config của master
    config_ws.append_row([str(year), new_spreadsheet.id])
    print(f"[INFO] Đã đăng ký năm {year} vào Config: {new_spreadsheet.id}")

    return new_spreadsheet


def get_or_create_worksheet(spreadsheet, sheet_name):
    """
    Lấy worksheet theo tên trong spreadsheet năm.
    Nếu chưa tồn tại → tự clone từ tab QuanLyViTienCat.
    """
    try:
        ws = spreadsheet.worksheet(sheet_name)
        print(f"[INFO] Đã tìm thấy worksheet '{sheet_name}'")
        return ws
    except gspread.exceptions.WorksheetNotFound:
        print(f"[INFO] Worksheet '{sheet_name}' chưa có, tạo mới từ template...")

    try:
        template_ws = spreadsheet.worksheet(TEMPLATE_SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        raise Exception(
            f"Tab '{TEMPLATE_SHEET_NAME}' không tồn tại trong spreadsheet! "
            f"Vui lòng tạo tab '{TEMPLATE_SHEET_NAME}' với format chuẩn."
        )

    result = template_ws.copy_to(spreadsheet.id)
    new_ws = spreadsheet.get_worksheet_by_id(result["sheetId"])
    new_ws.update_title(sheet_name)
    print(f"[INFO] Đã tạo worksheet mới: '{sheet_name}'")
    return new_ws


# ─────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/write', methods=['POST'])
def write_sheet():
    vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    current_time = datetime.now(vn_timezone)
    formatted_date = current_time.strftime("%d.%m")   # tab: "03.05"
    current_year = current_time.year                  # spreadsheet: "Vi Tien Cat 2026"

    try:
        client = setup_google_client()
        spreadsheet = get_year_spreadsheet(client, current_year)
        sheet = get_or_create_worksheet(spreadsheet, formatted_date)
        print(f"[INFO] Ghi vào [{current_year}] → tab '{formatted_date}'")
    except Exception as e:
        error_message = f"Error during Google Sheets setup: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
    except Exception as e:
        return jsonify({"error": f"Error reading JSON data: {e}"}), 400

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
        return jsonify({"error": f"Error processing rows: {e}"}), 500

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
        return jsonify({"error": f"Error updating sheet: {e}"}), 500

    try:
        subject = f"Nhân viên {data.get('nhan_vien')}"
        body = (
            f"Khách hàng {data.get('khach_hang')} đã thanh toán "
            f"{'chuyển khoản: ' + str(tienNganHang) if tienNganHang != 0 else ''} "
            f"{'tiền mặt: ' + str(tienMat) if tienMat != 0 else ''}"
        )
        send_email(subject, body, "assets/vitiencat.jpg")
    except Exception as e:
        print(f"Error sending email: {e}")

    return jsonify({
        "message": f"Thêm hàng {row_index} thành công vào ngày {formatted_date} năm {current_year}"
    })


@app.route('/setup-year', methods=['POST'])
def setup_year():
    """
    Endpoint để admin chủ động khởi tạo spreadsheet cho năm chỉ định.
    Body (tùy chọn): { "year": 2027 }
    """
    try:
        data = request.get_json(force=True) or {}
        vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
        target_year = data.get("year") or datetime.now(vn_timezone).year

        client = setup_google_client()
        spreadsheet = get_year_spreadsheet(client, int(target_year))

        return jsonify({
            "message": f"Spreadsheet năm {target_year} đã sẵn sàng",
            "spreadsheet_title": spreadsheet.title,
            "spreadsheet_id": spreadsheet.id,
            "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Kiểm tra kết nối và xem danh sách spreadsheet theo năm."""
    try:
        client = setup_google_client()
        master_id = os.getenv("MASTER_SHEET_ID")
        master = client.open_by_key(master_id)
        config_ws = master.worksheet(CONFIG_SHEET_NAME)
        records = config_ws.get_all_values()

        years = []
        for row in records[1:]:
            if len(row) >= 2:
                years.append({
                    "year": row[0],
                    "spreadsheet_id": row[1],
                    "url": f"https://docs.google.com/spreadsheets/d/{row[1]}/edit",
                })

        return jsonify({
            "status": "ok",
            "master_spreadsheet": master.title,
            "registered_years": years,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    now = datetime.now(vn_timezone)
    return jsonify({
        "message": "Hello from Flask!",
        "current_tab": now.strftime("%d.%m"),
        "current_year": now.year,
    })


if __name__ == '__main__':
    port = int(os.getenv("PORT", 9090))
    app.run(host="0.0.0.0", port=port)
