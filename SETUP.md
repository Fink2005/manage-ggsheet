# Hướng dẫn Setup Tự động hóa Google Sheets

## Bạn chỉ cần làm những bước này 1 lần duy nhất

---

## Bước 1: Chuẩn bị Google Spreadsheet

1. Tạo **1 Google Spreadsheet mới** (đây là lần cuối bạn tạo spreadsheet)
2. Tạo tab tên chính xác là `Template`
3. Setup tab `Template` với format giống báo cáo hiện tại của bạn:
   - Hàng 1: Tiêu đề "Báo cáo ngày DD.MM"
   - Hàng 2-5: Header (Khách hàng, Dịch vụ, Thanh toán, ...)
   - Hàng "Tổng" phía dưới
   - Màu sắc theo format chuẩn

4. Copy **Spreadsheet ID** từ URL:
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID_Ở_ĐÂY]/edit
   ```

---

## Bước 2: Update Vercel Environment Variable (lần cuối cùng)

Vào Vercel Dashboard → Settings → Environment Variables → Update:

```
SHEET_ID = <spreadsheet_id_mới_vừa_tạo>
```

**Sau bước này bạn KHÔNG BAO GIỜ cần đổi `SHEET_ID` nữa.**

---

## Bước 3: Deploy code mới

```bash
git add .
git commit -m "feat: auto-create worksheet tabs from Template"
git push
```

Vercel sẽ tự deploy. Sau đó hệ thống tự chạy mãi mãi.

---

## Kiểm tra hệ thống

### Kiểm tra kết nối
```
GET https://managevitiencat.vercel.app/health
```

Response mẫu:
```json
{
  "status": "ok",
  "spreadsheet_title": "Vi Tien Cat - Doanh Thu",
  "worksheets": ["Template", "25.03", "26.03"]
}
```

### Tạo tab trước (tùy chọn)
```
POST https://managevitiencat.vercel.app/setup-month
```
Body (tùy chọn):
```json
{ "date": "01.04" }
```

---

## Cách hoạt động sau khi setup

```
Nhân viên nhập data → POST /write
    ↓
Hệ thống kiểm tra tab "25.03" có chưa?
    ↓ Chưa có
Tự clone tab "Template" → đặt tên "25.03"
    ↓
Ghi dữ liệu bình thường vào tab
```

**Kết quả trong Google Spreadsheet:**
```
Spreadsheet: Vi Tien Cat - Doanh Thu
├── Template    ← không bao giờ xóa
├── 01.03
├── 02.03
├── ...
├── 25.03       ← tab hôm nay
└── 26.03       ← tự tạo ngày mai
```

---

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách fix |
|-----|-------------|----------|
| `Tab 'Template' không tồn tại` | Chưa tạo tab Template | Tạo tab tên chính xác là `Template` |
| `SHEET_ID environment variable not set` | Chưa update Vercel env | Update `SHEET_ID` trong Vercel |
| `GOOGLE_CREDENTIALS_JSON...` | Service account hết hạn | Tạo lại credentials JSON |
