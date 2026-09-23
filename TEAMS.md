# Đăng thời khoá biểu lên Microsoft Teams

Khi admin bấm **📢 Công bố** (module 👥 Tài khoản & Công bố, tick **"Đồng thời đăng
lên Microsoft Teams"**), ứng dụng:
1. tạo các tệp: **TKB_Lop_<ngày giờ>.pdf / .xlsx** (mỗi lớp 1 trang / 1 sheet),
   **TKB_GiaoVien_<ngày giờ>.pdf / .xlsx** (mỗi giáo viên 1 trang / 1 sheet),
   **Lich_coi_thi_<ngày giờ>.xlsx** (nếu đã phân công coi thi);
2. gửi cho 1 flow Power Automate → flow **lưu tệp vào thư mục chỉ định trong kênh
   Teams** và **đăng tin nhắn thông báo** vào kênh.

Tên tệp có ngày giờ nên mỗi lần đăng là 1 bộ tệp mới, bản cũ vẫn giữ lại. Không cần
quyền admin: flow chạy bằng tài khoản của bạn (cần là thành viên của nhóm Teams, và
giấy phép Power Automate Premium cho trigger HTTP — giống các flow đang dùng).
Đăng lại khi lỗi: nút **📤 Chỉ đăng lên Teams (không công bố lại)**.

## Bước 0 — Chuẩn bị trong Teams
1. Mở nhóm + kênh muốn đăng → tab **Tệp (Files)** → **+ Mới → Thư mục**, VD
   `Thời khoá biểu`.
2. Bấm **⋯ → Mở trong SharePoint (Open in SharePoint)**. Địa chỉ có dạng:
   ```
   https://eduttc.sharepoint.com/sites/TenNhom/Shared Documents/General/Thời khoá biểu
   ```
   - **Địa chỉ site** = phần đến hết `/sites/TenNhom`
   - **Đường dẫn thư mục kênh** = `/Shared Documents/<Tên kênh>` — kênh *Chung*
     thường là `General`; thư viện tiếng Việt có thể hiện là `Tài liệu dùng chung`
     (chọn bằng nút thư mục trong flow cho chắc).

## Bước 1 — Tạo flow `TKB_DangTeams`
https://make.powerautomate.com → **+ Tạo → Luồng đám mây tức thì** → trigger
**When a HTTP request is received** → **Tạo**.

1. **Trigger**: *Who can trigger the flow* = **Anyone**; *Request Body JSON Schema*:
   ```json
   {"type": "object", "properties": {
     "thu_muc": {"type": "string"},
     "thong_diep": {"type": "string"},
     "files": {"type": "array", "items": {"type": "object", "properties": {
       "ten": {"type": "string"}, "noi_dung_base64": {"type": "string"}}}}}}
   ```
2. **Apply to each** — *Select an output*: ô **files** (Dynamic content). Bên trong:
   **SharePoint → Create file**
   - *Site Address*: địa chỉ site ở Bước 0 (chọn trong danh sách, hoặc *Enter custom value*)
   - *Folder Path*: gõ `/Shared Documents/General/` rồi chèn ô **thu_muc** (Dynamic
     content của trigger) — thay `General` bằng tên thư mục kênh của bạn
   - *File Name*: ô **ten** (thuộc *files*, trong Dynamic content)
   - *File Content* (bấm **fx**): `base64ToBinary(item()?['noi_dung_base64'])`
3. **Microsoft Teams → Post message in a chat or channel** (đặt SAU vòng lặp):
   - *Post as*: `Flow bot` (hoặc `User`) · *Post in*: `Channel`
   - *Team*, *Channel*: chọn nhóm và kênh ở Bước 0
   - *Message*: ô **thong_diep** (Dynamic content)
4. **Response**: *Status Code* `200`, *Body* `{"ok": true}`.
5. **Save** → mở lại trigger → copy **HTTP URL**.

## Bước 2 — Secrets
Streamlit Cloud → **Manage app → Settings → Secrets**, thêm:
```toml
[teams]
flow_url = "<HTTP URL của flow TKB_DangTeams>"
thu_muc  = "Thời khoá biểu"                     # đúng tên thư mục đã tạo ở Bước 0
app_url  = "https://tkbtanphu.streamlit.app/"   # (tuỳ chọn) link trong tin nhắn
```
**Save** → module 👥 hiện ô **📤 Đồng thời đăng lên Microsoft Teams**.

> 🔒 Không gửi URL của flow qua chat/email — chỉ dán vào Secrets.

## Lỗi thường gặp
| Ứng dụng báo | Cách sửa |
|---|---|
| 401 / "Who can trigger" | Trigger phải để **Anyone**, copy lại HTTP URL sau khi Save |
| 502 / 504 | Mở **Run history** của flow → bước đỏ: thường sai *Site Address*, thư mục chưa tạo, hoặc thiếu bước **Response** |
| Tệp lưu nhưng không có tin nhắn | Kiểm tra bước *Post message*: đúng nhóm/kênh, tài khoản là thành viên nhóm |
