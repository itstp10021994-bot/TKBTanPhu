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

> **Không có quyền admin?** Dùng **Cách 3** bên dưới: 1 flow Power Automate
> chạy bằng chính tài khoản của bạn, ghi/đọc thẳng các List — kể cả List trong
> **"Danh sách của tôi"**.

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

## Cách 3: 1 flow Power Automate đồng bộ SharePoint List (không cần admin)

Flow chạy bằng **quyền của chính tài khoản tạo flow**, nên đọc/ghi được mọi List
bạn có quyền — kể cả List trong **"Danh sách của tôi"** — mà không cần quản
trị viên cấp quyền. Chỉ cần **1 flow** cho cả 9 List.

> ⚠️ Trigger *When a HTTP request is received* là connector **Premium**: tài khoản
> cần giấy phép Power Automate Premium (hoặc bản dùng thử 90 ngày — Power
> Automate tự đề nghị khi bạn thêm trigger này). Nếu không lưu được flow vì
> giấy phép, dùng tạm mục **3. Sao lưu trên máy** trong ứng dụng.

### Bước 0 — Lấy địa chỉ site chứa List
Mở 1 List của bạn trên trình duyệt, địa chỉ có dạng:
```
https://tenmien-my.sharepoint.com/personal/ten_taikhoan_tenmien_edu_vn/Lists/LopHoc/AllItems.aspx
```
**Địa chỉ site** là phần trước `/Lists/...`:
`https://tenmien-my.sharepoint.com/personal/ten_taikhoan_tenmien_edu_vn`
(List trong 1 site nhóm thì có dạng `https://tenmien.sharepoint.com/sites/TenSite`).

### Bước 1 — Tạo flow
https://make.powerautomate.com → **+ Tạo (Create) → Luồng đám mây tức thì
(Instant cloud flow)** → đặt tên `TKB_SharePointList` → chọn trigger
**When a HTTP request is received** → **Tạo**.

### Bước 2 — Trigger
- *Who can trigger the flow*: **Anyone**
- *Request Body JSON Schema*:
  ```json
  {"type": "object", "properties": {
    "thao_tac": {"type": "string"},
    "list": {"type": "string"},
    "duong_dan": {"type": "string"},
    "xoa_ids": {"type": "array", "items": {"type": "integer"}},
    "items": {"type": "array", "items": {"type": "object"}}}}
  ```

### Bước 3 — Điều kiện (Condition)
Thêm **Condition**: ô trái nhập biểu thức (fx) `triggerBody()?['thao_tac']`,
toán tử **is equal to**, ô phải gõ `doc`.

### Bước 4 — Nhánh **True** (đọc cột / đọc dữ liệu)
1. Thêm **SharePoint → Send an HTTP request to SharePoint**, đổi tên bước thành
   **`Doc_SharePoint`** (bấm ⋯ → Rename; đúng tên này để biểu thức bên dưới chạy):
   - *Site Address*: chọn **Enter custom value**, dán địa chỉ site ở Bước 0
   - *Method*: `GET`
   - *Uri* (fx):
     ```
     concat('_api/web/lists/getbytitle(''', triggerBody()?['list'], ''')/', triggerBody()?['duong_dan'])
     ```
   - *Headers*: `Accept` = `application/json;odata=nometadata`
2. Thêm **Response** (Request → Response):
   - *Status Code* (fx): `outputs('Doc_SharePoint')?['statusCode']`
   - *Body* (fx): `body('Doc_SharePoint')`
   - ⋯ → **Settings / Configure run after** → tick cả **is successful** và
     **has failed** (để ứng dụng biết List không tồn tại thay vì bị treo).

### Bước 5 — Nhánh **False** (ghi dữ liệu)
1. **Apply to each** — đổi tên `Xoa_tung_muc`:
   - *Select an output*: (fx) `triggerBody()?['xoa_ids']`
   - ⋯ → **Settings** → bật **Concurrency control**, *Degree of parallelism* = `20`
   - Bên trong thêm **Send an HTTP request to SharePoint**:
     - *Site Address*: như Bước 4
     - *Method*: `DELETE`
     - *Uri* (fx):
       ```
       concat('_api/web/lists/getbytitle(''', triggerBody()?['list'], ''')/items(', string(item()), ')')
       ```
     - *Headers*: `IF-MATCH` = `*`
2. **Apply to each** thứ 2 (đặt SAU vòng xoá) — đổi tên `Tao_tung_muc`:
   - *Select an output*: (fx) `triggerBody()?['items']`
   - Để **tắt** Concurrency (chạy lần lượt → giữ đúng thứ tự dòng)
   - Bên trong thêm **Send an HTTP request to SharePoint**:
     - *Site Address*: như Bước 4
     - *Method*: `POST`
     - *Uri* (fx):
       ```
       concat('_api/web/lists/getbytitle(''', triggerBody()?['list'], ''')/items')
       ```
     - *Headers*: `Accept` = `application/json;odata=nometadata` và
       `Content-Type` = `application/json;odata=nometadata`
     - *Body* (fx): `item()`
3. Sau 2 vòng lặp, thêm **Response**: *Status Code* `200`, *Body* `{"ok": true}`.

### Bước 6 — Lưu & dán URL vào Secrets
Bấm **Save** → mở lại trigger, copy **HTTP URL**, rồi thêm vào Secrets của
ứng dụng (Streamlit Cloud: *Manage app → Settings → Secrets*):
```toml
[power_automate]
sp_url = "https://....logic.azure.com:443/workflows/.../triggers/manual/paths/invoke?...&sig=..."
```
Có thể giữ cả `save_url`/`list_url`/`load_url` (Cách 2) trong cùng mục nếu muốn
lưu thêm file sao lưu.

> 🔒 URL này cho phép đọc/ghi các List trong site ở Bước 0 bằng quyền của bạn —
> chỉ dán vào Secrets, không gửi qua chat/email. Nếu lộ, xoá trigger rồi tạo lại
> để có URL mới.

### Bước 7 — Chạy thử
Trong ứng dụng: module **☁️ Lưu trữ SharePoint** → mục **2b** → **🔍 Kiểm tra
List & cột**. Nếu báo lỗi 502/504, mở flow → **Run history** → bấm vào lần chạy
lỗi để xem bước nào đỏ.

Mỗi lần ghi, ứng dụng gửi tối đa 40 dòng/lần gọi flow (xoá tối đa 200 mục/lần),
nên danh sách vài trăm học sinh mất khoảng 1–3 phút. Mỗi List đọc được tối đa
5.000 mục.

---

## Đồng bộ trực tiếp với SharePoint Lists (mục 2b trong module ☁️)

Ngoài lưu file, ứng dụng ghi/đọc thẳng từng bảng vào **SharePoint List** —
mỗi dòng của bảng = 1 mục của List. Cần **Cách 3** (flow `sp_url`, không cần
admin) hoặc **Cách 1** (Microsoft Graph, App Registration có quyền **write**).

> Với Cách 1 nên tạo List trong 1 **site** (VD Team Site của trường); Cách 3
> dùng được cả "Danh sách của tôi". Với Cách 1, `site_url` trong Secrets là địa chỉ site,
> VD `https://tenmien.sharepoint.com/sites/TKB` (dán cả link của 1 List cũng được,
> ứng dụng tự lấy phần địa chỉ site).

### Tên List & tên cột
| Tên List | Các cột (tên hiển thị) | Cột kiểu **Số** |
|---|---|---|
| `ToChuyenMon` | Tên tổ | |
| `GiaoVien` | Tên giáo viên · Tổ chuyên môn | |
| `LopHoc` | Tên lớp · Khối · Nhóm thứ tự | Khối, Nhóm thứ tự |
| `PhongDacBiet` | Tên phòng · Loại phòng · Số phòng cùng loại | Số phòng cùng loại |
| `MonHocPhanCong` | Tên hoạt động · Môn · Số tiết/tuần · Lớp · GV chính · GV phụ · Loại phòng cần · Mã đồng bộ · Cố định trước | Số tiết/tuần |
| `GioHocTheoKhoi` | Khối · Thứ · Tiết · Giờ bắt đầu · Giờ kết thúc | Khối, Tiết |
| `DanhSachHocSinhThi` | SBD · Họ và tên · Lớp · Môn thi | |
| `DanhSachPhongThi` | Tên phòng · Sức chứa · Số cột bàn | Sức chứa, Số cột bàn |
| `MonThi` | Môn thi · Lớp áp dụng · Ngày thi · Ca thi · Chế độ xếp | |

- Tên cột được khớp **không phân biệt dấu, hoa/thường, bỏ qua phần trong
  ngoặc**: `Số tiết/tuần`, `So tiet tuan`, `Số tiết (tuần)`... đều khớp.
- Các cột không phải số tạo kiểu **Một dòng văn bản** (Single line of text).
  Cột "Môn thi" của học sinh có thể dài → chọn **Nhiều dòng văn bản**.
- Cột **Tiêu đề** (Title) mặc định của List: có thể đổi tên thành cột đầu tiên
  (VD "Tên lớp") hoặc để nguyên — ứng dụng tự điền giá trị cột đầu tiên vào đó.
- List `SoTietTheoKhoiNgay` **không còn dùng** — đã gộp vào `GioHocTheoKhoi`.
- Muốn dùng tên List khác, khai báo trong Secrets:
  ```toml
  [sharepoint.lists]          # hoặc [power_automate.lists] nếu dùng Cách 3
  classes = "DanhSachLop"      # departments, teachers, classes, rooms, activities,
                               # grade_times, exam_students, exam_rooms, exam_subjects
  ```

**Cách nhanh nhất**: trong module ☁️ bấm **📄 Tải file Excel mẫu để tạo List**
(mỗi List 1 sheet, đã kèm dữ liệu hiện tại), rồi vào Microsoft Lists →
**+ Danh sách mới → Từ Excel** → chọn file → chọn đúng bảng (table) → **Lưu vào**
site của trường, đặt tên List đúng như bảng trên.

### Sử dụng
1. **🔍 Kiểm tra List & cột** — xem List nào chưa có, thiếu cột nào.
2. **⬆️ Ghi các bảng lên List** — tick ô xác nhận trước; toàn bộ mục cũ trong
   List được thay bằng dữ liệu hiện tại của ứng dụng (giữ đúng thứ tự dòng).
3. **⬇️ Đọc từ List vào ứng dụng** — nạp dữ liệu từ List vào các bảng (VD sau
   khi nhiều người cùng nhập liệu trực tiếp trên SharePoint).

Kết quả xếp thời khoá biểu / phòng thi không nằm trong List — dùng nút
**💾 Lưu lên SharePoint** (mục 2) để lưu cả kết quả dưới dạng file.

## Không có SharePoint?

Mục **3. Sao lưu trên máy** trong cùng module luôn dùng được: tải file `.json`
về máy và khôi phục lại khi cần, hoặc tải bản Excel để tự upload lên
SharePoint/OneDrive.
