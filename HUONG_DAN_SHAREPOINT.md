# Hướng dẫn kết nối SharePoint & Power Automate để lưu dữ liệu

Module **☁️ Lưu trữ SharePoint** (thanh bên trái của ứng dụng) lưu TOÀN BỘ dữ
liệu lên thư viện tài liệu SharePoint của trường: các bảng nhập liệu, cấu hình,
thời gian biểu, kết quả thời khoá biểu, phòng thi, phân công dạy thay.

Mỗi lần bấm **💾 Lưu lên SharePoint**, ứng dụng tạo 2 file cùng tên trong thư
mục đã cấu hình:

| File | Dùng để |
|---|---|
| `<tên>.json` | Bản sao lưu đầy đủ — bấm **📂 Tải vào ứng dụng** để nạp lại. |
| `<tên>.xlsx` | Bản Excel dễ đọc (mỗi bảng 1 sheet + sheet kết quả) — mở trực tiếp trên SharePoint. |

Lưu trùng tên thì file cũ bị ghi đè, nhưng SharePoint vẫn giữ **lịch sử phiên
bản** (chuột phải file → *Version history*) nên không mất dữ liệu cũ.

Có **2 cách** kết nối — chọn 1 (hoặc cấu hình cả 2, ứng dụng sẽ cho chọn):

| | Cách 1: Microsoft Graph | Cách 2: Power Automate |
|---|---|---|
| Cần gì | Quyền quản trị Microsoft 365 / Entra ID để tạo App Registration | Giấy phép **Power Automate Premium** (trigger *When a HTTP request is received* là connector Premium) |
| Lưu | ✅ | ✅ |
| Tải lại từ SharePoint | ✅ | ✅ (cần thêm 2 flow đọc) |
| Ưu điểm | Nhanh, ít bước, không tốn lượt chạy flow | Không cần tạo App Registration; dễ thêm bước xử lý (gửi mail, duyệt, ghi List...) |

Cấu hình đặt trong **Secrets** của ứng dụng — KHÔNG đưa lên GitHub:
- **Streamlit Cloud**: *Manage app → Settings → Secrets*, dán nội dung vào.
- **Chạy trên máy**: tạo file `.streamlit/secrets.toml` (copy từ
  `.streamlit/secrets.toml.example`). File này đã nằm trong `.gitignore`.

Sau khi lưu Secrets, mở lại module ☁️ — dòng "✅ Đã cấu hình" nghĩa là đã nhận.

---

## Bước chung: chuẩn bị chỗ lưu trên SharePoint

1. Chọn (hoặc tạo) 1 site SharePoint, VD `https://tenmien.sharepoint.com/sites/TKB`.
2. Trong thư viện **Documents** (Tài liệu) của site, tạo thư mục, VD `TKB_TanPhu`.
   (Với cách 1, nếu chưa tạo thì ứng dụng tự tạo khi lưu lần đầu.)

---

## Cách 1: Microsoft Graph (gọi thẳng SharePoint)

### 1.1 Tạo App Registration
1. Vào https://entra.microsoft.com → **Applications → App registrations → New registration**.
2. Tên: `TKB Tan Phu`, *Supported account types*: **Single tenant** → **Register**.
3. Ở trang Overview, ghi lại **Application (client) ID** và **Directory (tenant) ID**.
4. **Certificates & secrets → New client secret** → ghi lại **Value** (chỉ hiện 1 lần).

### 1.2 Cấp quyền
Chọn 1 trong 2:

- **Đơn giản** — quyền trên toàn bộ SharePoint của trường:
  **API permissions → Add a permission → Microsoft Graph → Application permissions →
  `Sites.ReadWrite.All`** → **Grant admin consent**.
- **An toàn hơn** — chỉ 1 site: thêm quyền Application **`Sites.Selected`** →
  **Grant admin consent**, rồi quản trị viên cấp quyền ghi cho đúng site đó bằng
  Graph Explorer (https://developer.microsoft.com/graph/graph-explorer):
  1. `GET https://graph.microsoft.com/v1.0/sites/tenmien.sharepoint.com:/sites/TKB` → lấy `id`.
  2. `POST https://graph.microsoft.com/v1.0/sites/{id}/permissions` với body:
     ```json
     {"roles": ["write"],
      "grantedToIdentities": [{"application": {"id": "<client_id>", "displayName": "TKB Tan Phu"}}]}
     ```

### 1.3 Secrets
```toml
[sharepoint]
tenant_id     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
client_id     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
client_secret = "giá-trị-secret"
site_url      = "https://tenmien.sharepoint.com/sites/TKB"
folder        = "TKB_TanPhu"   # thư mục trong thư viện tài liệu
# library     = "Documents"    # (tuỳ chọn) tên thư viện, bỏ trống = thư viện mặc định
```

> Client secret có hạn dùng (mặc định 6–24 tháng). Khi hết hạn, ứng dụng báo
> "Đăng nhập Microsoft thất bại" — tạo secret mới và cập nhật Secrets.

---

## Cách 2: Power Automate

Tạo **3 flow** kiểu *Instant cloud flow* với trigger **When a HTTP request is
received** (flow 2 & 3 chỉ cần nếu muốn tải dữ liệu ngược về ứng dụng). Trong
mỗi trigger, mục *Who can trigger the flow* chọn **Anyone**. Sau khi **Save**,
trigger hiện ra **HTTP URL** — copy vào Secrets.

> URL của trigger chứa chữ ký bảo mật (`sig=...`): ai có URL là gọi được flow.
> Chỉ dán URL vào Secrets, không gửi qua chat/email.

Ở các bước dưới: *Site Address* = site của bạn, thư mục = `/Shared Documents/TKB_TanPhu`
(với site tiếng Việt, thư viện có thể hiện là `/Tai lieu dung chung` — chọn bằng nút thư mục).

### Flow 1 — Lưu (`save_url`)
1. Trigger **When a HTTP request is received**, *Request Body JSON Schema*:
   ```json
   {"type": "object", "properties": {
     "ten": {"type": "string"}, "thoi_gian": {"type": "string"},
     "json_text": {"type": "string"}, "excel_base64": {"type": "string"}}}
   ```
2. **SharePoint → Create file**
   - Folder Path: `/Shared Documents/TKB_TanPhu`
   - File Name: `@{triggerBody()?['ten']}.json`
   - File Content: `@{triggerBody()?['json_text']}`
3. **SharePoint → Create file** (lần 2)
   - File Name: `@{triggerBody()?['ten']}.xlsx`
   - File Content (bấm *fx*, nhập biểu thức): `base64ToBinary(triggerBody()?['excel_base64'])`
4. **Response**: Status Code `200`, Body `{"ok": true}`.

> Nếu lưu trùng tên mà bước *Create file* báo file đã tồn tại, thêm 1 nhánh
> song song dùng **Update file** (cấu hình *Configure run after → has failed*),
> hoặc đặt tên bản lưu khác nhau (VD thêm ngày).

### Flow 2 — Danh sách bản lưu (`list_url`)
1. Trigger **When a HTTP request is received** (không cần schema).
2. **SharePoint → List folder**, File Identifier: `/Shared Documents/TKB_TanPhu`.
3. **Response**: Status Code `200`, Body = `body('List_folder')` (hoặc chọn
   *Body* của bước *List folder* trong Dynamic content).

Ứng dụng tự lọc các file `.json` và đọc các trường `Name`, `LastModified`.

### Flow 3 — Tải 1 bản lưu (`load_url`)
1. Trigger **When a HTTP request is received**, schema:
   ```json
   {"type": "object", "properties": {"ten": {"type": "string"}}}
   ```
2. **SharePoint → Get file content using path**,
   File Path: `/Shared Documents/TKB_TanPhu/@{triggerBody()?['ten']}.json`
3. **Response**: Status Code `200`, Body = *File Content* của bước 2.

### Secrets
```toml
[power_automate]
save_url = "https://prod-00.southeastasia.logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?...&sig=..."
list_url = "https://..."   # flow 2 (không bắt buộc)
load_url = "https://..."   # flow 3 (không bắt buộc)
```

Có thể mở rộng Flow 1 tuỳ ý, VD thêm bước *Send an email* báo cho Ban giám
hiệu mỗi khi có bản thời khoá biểu mới, hoặc *Start and wait for an approval*.

---

## Không có SharePoint?

Mục **3. Sao lưu trên máy** trong cùng module luôn dùng được: tải file `.json`
về máy và khôi phục lại khi cần, hoặc tải bản Excel để tự upload lên
SharePoint/OneDrive.
