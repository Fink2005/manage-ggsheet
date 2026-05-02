# Hướng dẫn Setup — Option A: 1 Spreadsheet/năm

## Bạn chỉ cần làm những bước này 1 lần duy nhất

---

## Bước 1: Tạo "Master Spreadsheet" (1 lần duy nhất, mãi mãi)

1. Tạo **1 Google Spreadsheet** đặt tên `Vi Tien Cat - Master`
2. Tạo tab tên chính xác là **`Config`** với header:

   | Year | SpreadsheetID |
   |------|---------------|
   | (để trống, code tự điền) | |

3. Tạo tab tên chính xác là **`QuanLyViTienCat`** với format báo cáo chuẩn:
   - Hàng 1: Tiêu đề "Báo cáo ngày DD.MM"
   - Hàng 2-5: Header (Khách hàng, Dịch vụ, Thanh toán, ...)
   - Hàng "Tổng" phía dưới + màu sắc theo format chuẩn

4. Copy **Spreadsheet ID** từ URL:
   ```
   https://docs.google.com/spreadsheets/d/[MASTER_SHEET_ID_Ở_ĐÂY]/edit
   ```

---

## Bước 2: Update Vercel Environment Variables (1 lần duy nhất)

Vào Vercel Dashboard → Settings → Environment Variables:

- **Đổi tên** `SHEET_ID` → **`MASTER_SHEET_ID`** = `<ID vừa copy>`
- Xóa `SHEET_ID` cũ

**Sau bước này bạn KHÔNG BAO GIỜ cần đổi env var nữa, dù sang năm mới.**

---

## Bước 3: Deploy code mới

```bash
git add .
git commit -m "feat: option A - 1 spreadsheet per year with auto-creation"
git push
```

---

## Cách hoạt động tự động

```
Nhân viên nhập data ngày 03.05.2026 → POST /write
    ↓
Đọc tab "Config" trong Master Spreadsheet
    ↓ Chưa có năm 2026
Tự tạo spreadsheet "Vi Tien Cat - Doanh Thu 2026"
Clone tab "QuanLyViTienCat" từ Master sang
Ghi ID vào Config → ["2026", "abc123..."]
    ↓
Kiểm tra tab "03.05" trong spreadsheet 2026
    ↓ Chưa có
Clone "QuanLyViTienCat" → đặt tên "03.05"
    ↓
Ghi dữ liệu bình thường
```

**Kết quả:**
```
Master Spreadsheet (không bao giờ xóa)
├── Config
│     Year | SpreadsheetID
│     2025 | abc123...   ← tự điền
│     2026 | def456...   ← tự điền đầu năm
└── QuanLyViTienCat      ← template gốc

Spreadsheet "Vi Tien Cat - Doanh Thu 2025"
├── QuanLyViTienCat
├── 01.01, 02.01, ..., 31.12

Spreadsheet "Vi Tien Cat - Doanh Thu 2026"  ← tự tạo
├── QuanLyViTienCat
├── 01.01, 02.01, ..., 03.05 (hôm nay)
```

---

## Kiểm tra hệ thống

### Xem danh sách spreadsheet theo năm
```
GET https://managevitiencat.vercel.app/health
```
Response:
```json
{
  "status": "ok",
  "master_spreadsheet": "Vi Tien Cat - Master",
  "registered_years": [
    { "year": "2025", "spreadsheet_id": "abc...", "url": "https://..." },
    { "year": "2026", "spreadsheet_id": "def...", "url": "https://..." }
  ]
}
```

### Khởi tạo trước spreadsheet năm mới (tùy chọn)
```
POST https://managevitiencat.vercel.app/setup-year
```
Body (tùy chọn):
```json
{ "year": 2027 }
```

---

## So sánh trước/sau

| | Trước | Sau |
|---|---|---|
| Mỗi tháng | Tạo spreadsheet mới, update env | Tự động hoàn toàn |
| Đầu năm | Tạo spreadsheet mới, update env | Tự động hoàn toàn |
| Env var thay đổi | Mỗi tháng | **Không bao giờ** |
| Redeploy | Mỗi tháng | **Không bao giờ** |
| Nhìn dữ liệu | 1 file hàng trăm tab | Mỗi năm 1 file riêng, tối đa 366 tab |

---

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách fix |
|-----|-------------|----------|
| `MASTER_SHEET_ID not set` | Chưa update Vercel env | Đổi `SHEET_ID` → `MASTER_SHEET_ID` trong Vercel |
| `Tab 'Config' không tồn tại` | Chưa tạo tab Config | Tạo tab tên chính xác `Config` với header |
| `Tab 'QuanLyViTienCat' không tồn tại` | Chưa tạo tab template | Tạo tab `QuanLyViTienCat` trong Master |
| `GOOGLE_CREDENTIALS_JSON...` | Service account hết hạn | Tạo lại credentials JSON |
