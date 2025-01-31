import os
import json
import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    """Creates a test client for the Flask app"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_env_variables():
    """Ensure environment variables are loaded correctly"""
    assert os.getenv("SHEET_ID") is not None
    assert os.getenv("GOOGLE_CREDENTIALS_JSON") is not None

@patch("app.setup_google_sheets")
def test_write_sheet(mock_setup_google_sheets, client):
    """Test the /write endpoint with a mock Google Sheets API"""

    # Mock Google Sheets worksheet behavior
    mock_sheet = MagicMock()
    mock_sheet.get_all_values.return_value = [
        ["SO_HD", "KHACH_HANG", "DV_DUONG_SINH", "THE_DV", "DV_SPA", "DV_NAIL", "TIEN_MAT", "CHUYEN_KHOAN", "THE_DV_T", "NHAN_VIEN", "GHI_CHU"],
        ["123", "John Doe", "", "", "", "", "100", "200", "", "", ""],
        ["Tổng"]  # Ensuring it detects 'Tổng' and inserts data correctly
    ]
    mock_sheet.insert_row.return_value = None
    mock_sheet.update_cell.return_value = None
    mock_sheet.update.return_value = None

    # Mock the function returning the worksheet
    mock_setup_google_sheets.return_value.worksheet.return_value = mock_sheet

    # Sample payload
    payload = {
        "so_hd": "456",
        "khach_hang": "Jane Doe",
        "dv_duong_sinh": "",
        "the_dv": "",
        "dv_spa": "",
        "dv_nail": "",
        "tien_mat": 300,
        "chuyen_khoan": 400,
        "the_dv_t": "",
        "nhan_vien": "Alice",
        "ghi_chu": "Test entry"
    }

    response = client.post("/write", data=json.dumps(payload), content_type="application/json")

    assert response.status_code == 200
    assert "Thêm hàng" in response.json["message"]

