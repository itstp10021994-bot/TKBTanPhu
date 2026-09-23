# Đăng nhập & phân quyền

| Chức năng | admin | user |
|---|---|---|
| 📅 Thời khoá biểu | Nhập liệu, xếp lịch, xuất file | Xem & xuất PDF/Excel bản đã công bố |
| 🪑 Phòng thi | Nhập liệu, xếp phòng, xuất file | Xem & xuất PDF/Excel bản đã công bố |
| 🔄 Dạy thay | Phân công, lưu, xoá | Xem & xuất PDF |
| ☁️ Lưu trữ SharePoint | Lưu / tải / đồng bộ List | — |
| 👥 Tài khoản & Công bố | Công bố, xem tài khoản, tạo mã băm | — |

## 1. Bật đăng nhập
1. Mở app (lúc chưa bật đăng nhập ai cũng là admin) → module **👥 Tài khoản &
   Công bố** → **🔑 Tạo mã băm mật khẩu** → nhập mật khẩu (≥ 8 ký tự) → copy dòng
   `password_hash = "..."`. Làm cho từng tài khoản.
2. Streamlit Cloud → **Manage app → Settings → Secrets**, thêm:
   ```toml
   [auth.users.admin]
   name          = "Quản trị viên"
   role          = "admin"
   password_hash = "pbkdf2_sha256$..."

   [auth.users.giaovien]
   name          = "Giáo viên"
   role          = "user"
   password_hash = "pbkdf2_sha256$..."
   ```
   Tên đăng nhập là phần sau `auth.users.` (không phân biệt hoa/thường). Thêm bao
   nhiêu tài khoản cũng được; có thể dùng chung 1 tài khoản `user` cho giáo viên.
3. **Save** → app yêu cầu đăng nhập. Đổi mật khẩu / xoá tài khoản: sửa Secrets.

Sai mật khẩu 5 lần liên tiếp → tài khoản bị khoá đăng nhập 60 giây.

## 2. Công bố cho người dùng
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
    Có thể đổi tên List qua `[power_automate.lists] cong_bo = "..."`.

Admin khi mở app sẽ tự nạp bản công bố làm điểm bắt đầu; nút **📥 Nạp bản công bố
vào phiên của tôi** để quay lại bản đó sau khi đã sửa.
