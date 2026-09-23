# Đăng nhập & phân quyền

| Chức năng | admin | user |
|---|---|---|
| 📅 Thời khoá biểu | Nhập liệu, xếp lịch, xuất file | Xem & xuất PDF/Excel bản đã công bố |
| 🪑 Phòng thi | Nhập liệu, xếp phòng, xuất file | Xem & xuất PDF/Excel bản đã công bố |
| 🔄 Dạy thay | Phân công, lưu, xoá | Xem & xuất PDF |
| ☁️ Lưu trữ SharePoint | Lưu / tải / đồng bộ List | — |
| 👥 Tài khoản & Công bố | Công bố, xem cấu hình đăng nhập | — |

Có 2 cách đăng nhập, dùng 1 hoặc cả 2:
- **A. Tài khoản Microsoft của trường** (email Outlook) — khuyên dùng cho giáo viên.
- **B. Tài khoản nội bộ** (tên đăng nhập + mật khẩu trong Secrets) — dùng làm
  tài khoản admin dự phòng.

Chưa cấu hình cách nào thì app không yêu cầu đăng nhập (ai mở cũng là admin).

---

## A. Đăng nhập bằng email Outlook của trường (Microsoft 365)

Dùng tính năng `st.login()` của Streamlit với Microsoft Entra ID. Giáo viên bấm
**🟦 Đăng nhập bằng tài khoản Microsoft của trường**, đăng nhập như vào Outlook,
rồi quay lại app. Vai trò gán theo email:
- email trong `admin_emails` → **admin**;
- email thuộc tên miền trong `domains` (hoặc nằm trong `user_emails`) → **user**;
- email khác → bị từ chối.

### A1. Tạo App Registration (1 lần)
1. Vào https://entra.microsoft.com (hoặc https://portal.azure.com) bằng tài khoản
   trường → **Applications → App registrations → + New registration**.
2. Điền:
   - *Name*: `TKB Tan Phu`
   - *Supported account types*: **Accounts in this organizational directory only
     (Single tenant)**
   - *Redirect URI*: chọn **Web**, nhập `https://<tên-app>.streamlit.app/oauth2callback`
     (địa chỉ app Streamlit của bạn + `/oauth2callback`)
   → **Register**.
3. Trang *Overview*: ghi lại **Application (client) ID** và **Directory (tenant) ID**.
4. **Certificates & secrets → Client secrets → + New client secret** → chọn hạn
   (VD 24 tháng) → **Add** → copy ngay cột **Value** (chỉ hiện 1 lần).
5. **API permissions**: giữ mặc định `Microsoft Graph → User.Read` (chỉ đọc hồ sơ
   người đăng nhập). Không cần thêm quyền nào khác.

> **Nếu không có quyền tạo App Registration** (trang báo không có quyền, hoặc lần
> đầu đăng nhập hiện "Cần quản trị viên phê duyệt / Need admin approval"): tổ chức
> đã khoá tính năng này với tài khoản thường → nhờ IT tạo giúp đúng các bước trên.
> Ứng dụng chỉ xin quyền đăng nhập và đọc tên/email, không đọc thư hay tài liệu.

### A2. Dán vào Secrets
Streamlit Cloud → **Manage app → Settings → Secrets**:
```toml
[auth]
redirect_uri        = "https://<tên-app>.streamlit.app/oauth2callback"
cookie_secret       = "<chuỗi ngẫu nhiên — tạo bằng nút 🎲 trong module 👥>"
client_id           = "<Application (client) ID>"
client_secret       = "<Value của client secret>"
server_metadata_url = "https://login.microsoftonline.com/<Directory (tenant) ID>/v2.0/.well-known/openid-configuration"

[phan_quyen]
admin_emails = ["it.stp@igcschool.edu.vn"]   # các email được làm admin
domains      = ["igcschool.edu.vn"]          # mọi email @igcschool.edu.vn là user
# user_emails = ["gv.ngoai@gmail.com"]       # (tuỳ chọn) thêm từng email khác
```
**Save** → mở app sẽ thấy nút đăng nhập Microsoft. Module **👥** hiển thị lại các
quy tắc đang áp dụng.

- Đổi admin / thêm tên miền: sửa `[phan_quyen]` → Save. Người đang đăng nhập áp
  dụng quyền mới sau khi đăng xuất & đăng nhập lại.
- Client secret hết hạn → đăng nhập báo lỗi: tạo secret mới (bước A1.4), cập nhật
  `client_secret`.

---

## B. Tài khoản nội bộ (tuỳ chọn, VD admin dự phòng)
1. Module **👥 Tài khoản & Công bố** → **🔑 Tạo mã băm mật khẩu** → copy dòng
   `password_hash = "..."`.
2. Thêm vào Secrets:
   ```toml
   [phan_quyen.users.admin]
   name          = "Quản trị viên"
   role          = "admin"        # hoặc "user"
   password_hash = "pbkdf2_sha256$..."
   ```
   Khi đã bật cách A, tài khoản nội bộ nằm trong mục "Đăng nhập bằng tài khoản nội
   bộ" ở màn hình đăng nhập. Sai mật khẩu 5 lần liên tiếp → khoá 60 giây.
   (Khai báo cũ `[auth.users.<tên>]` vẫn dùng được.)

---

## Công bố cho người dùng
Mỗi người mở app có 1 phiên làm việc riêng, nên user chỉ thấy dữ liệu admin đã
**công bố**: admin xếp xong → module **👥** → **📢 Công bố dữ liệu hiện tại**.
User đang mở app thấy bản mới ở lần bấm/chuyển trang kế tiếp.

Bản công bố được lưu:
- trên máy chủ ứng dụng (mọi người dùng thấy ngay) và file `du_lieu/cong_bo.json`
  — **mất khi Streamlit khởi động lại app** (VD app ngủ do lâu không dùng);
- trên **SharePoint** nếu đã cấu hình (xem `HUONG_DAN_SHAREPOINT.md`) — để khi app
  khởi động lại tự nạp lại:
  - Microsoft Graph / flow lưu file (Cách 1, 2): file `CongBo_TKB.json`;
  - chỉ có flow `sp_url` (Cách 3): List **`TKB_CongBo`** — tạo List này với 1 cột
    **`NoiDung`** kiểu **Nhiều dòng văn bản**, *tắt* "văn bản đa dạng thức" (rich text).

Admin khi mở app sẽ tự nạp bản công bố làm điểm bắt đầu; nút **📥 Nạp bản công bố
vào phiên của tôi** để quay lại bản đó sau khi đã sửa.
