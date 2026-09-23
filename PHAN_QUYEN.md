# Đăng nhập & phân quyền

| Chức năng | admin | user (giáo viên) |
|---|---|---|
| 📅 Thời khoá biểu (toàn trường) | Nhập liệu, xếp lịch, xuất file | — |
| 🪑 Phòng thi + phân công coi thi | Nhập liệu, xếp phòng, phân công giám thị | — |
| 🔄 Dạy thay | Phân công, lưu, xoá | — |
| ☁️ Lưu trữ SharePoint, 👥 Tài khoản & Công bố | Có | — |
| **👤 Lịch của tôi** | Xem trước lịch của bất kỳ GV nào | **TKB của mình, TKB lớp chủ nhiệm, lịch coi thi, lịch dạy thay liên quan** (xem & tải PDF/Excel) |

## Cấp quyền admin — 2 cách
1. **Trong Secrets** (admin gốc, luôn có hiệu lực):
   ```toml
   [phan_quyen]
   admin_emails = ["it.stp@igcschool.edu.vn", "hieutruong@igcschool.edu.vn"]
   ```
2. **Trong app** (không cần sửa Secrets): module 📅 → tab **🏢 Tổ / GV / Lớp / Phòng**
   → bảng **Giáo viên** → cột **Quyền** chọn `admin` cho giáo viên đó → module 👥
   → **📢 Công bố**. Giáo viên đăng nhập lại là có quyền admin. Đổi về `user` + công
   bố để thu hồi.

## Gắn giáo viên với tài khoản đăng nhập
Bảng **Giáo viên** có thêm 3 cột:
- **Email**: email trường của giáo viên — khi đăng nhập bằng email này, trang
  **👤 Lịch của tôi** hiện đúng lịch của giáo viên đó. Email có trong cột này cũng
  được phép đăng nhập (kể cả khi không thuộc tên miền trong `domains`).
- **Lớp chủ nhiệm**: giáo viên thấy thêm TKB của lớp này.
- **Quyền**: `user` / `admin` (xem trên).

Lịch coi thi: module 🪑 → sau khi xếp phòng → mục **4. Phân công coi thi** → chọn số
giám thị/phòng, GV không tham gia → **🎲 Phân công coi thi tự động** (chia đều, không
coi 2 phòng cùng buổi, tránh coi môn mình dạy) → sửa tay nếu cần → **📢 Công bố**.

Mọi thay đổi (TKB, email, lớp chủ nhiệm, quyền, coi thi) chỉ đến với giáo viên sau
khi admin **📢 Công bố**.

Các cách đăng nhập (dùng 1 hoặc kết hợp):
- **C. Mã gửi qua email trường** — giáo viên nhập email trường, nhận mã 6 số trong
  Outlook. **Không cần App Registration / quyền admin Microsoft** — khuyên dùng.
- **A. Tài khoản Microsoft của trường** (nút đăng nhập Microsoft) — cần App
  Registration trên Microsoft Entra (thường phải có IT hỗ trợ).
- **B. Tài khoản nội bộ** (tên đăng nhập + mật khẩu trong Secrets) — dùng làm
  tài khoản admin dự phòng.

Với cả A và C, vai trò gán theo email trong mục `[phan_quyen]`: email trong
`admin_emails` → admin; email thuộc `domains` (hoặc trong `user_emails`) → user;
email khác bị từ chối.

Chưa cấu hình cách nào thì app không yêu cầu đăng nhập (ai mở cũng là admin).

---

## C. Mã đăng nhập gửi qua email trường (không cần App Registration, không cần admin) — khuyên dùng

Giáo viên nhập **email trường** → 1 flow Power Automate gửi **mã 6 số** vào hộp thư
Outlook của giáo viên đó → nhập mã là đăng nhập. Ai đọc được hộp thư trường mới
đăng nhập được, nên đây vẫn là "đăng nhập bằng mail trường". Flow gửi thư từ hộp
thư của người tạo flow (VD `it.stp@...`), dùng connector Outlook thường.

Bảo mật: mã hết hạn sau 10 phút, dùng 1 lần, sai 5 lần phải gửi mã mới; mỗi email
chỉ gửi được 1 mã/phút và 5 mã/giờ; chỉ gửi cho email hợp lệ theo `[phan_quyen]`.
Đăng nhập giữ đến khi đóng/tải lại tab trình duyệt (tải lại trang thì nhập mã mới).

### C1. Tạo flow gửi mã (1 lần)
1. https://make.powerautomate.com → **+ Tạo → Luồng đám mây tức thì** → tên
   `TKB_GuiMaDangNhap` → trigger **When a HTTP request is received** → **Tạo**.
2. Trigger: *Who can trigger the flow* = **Anyone**; *Request Body JSON Schema*:
   ```json
   {"type": "object", "properties": {
     "email": {"type": "string"}, "ma": {"type": "string"},
     "het_han_phut": {"type": "integer"}, "ten_truong": {"type": "string"}}}
   ```
3. **+ Thêm bước → Office 365 Outlook → Send an email (V2)**:
   - *To*: chọn ô **email** (Dynamic content ⚡ của trigger)
   - *Subject*: gõ `Mã đăng nhập Thời khoá biểu: ` rồi chèn ô **ma**
   - *Body*: VD `Mã đăng nhập của bạn là ` **ma** `. Mã có hiệu lực ` **het_han_phut**
     ` phút. Nếu bạn không yêu cầu, hãy bỏ qua thư này.`
4. **+ Thêm bước → Response**: *Status Code* `200`, *Body* `{"ok": true}`.
5. **Save** → mở lại trigger → copy **HTTP URL**.

### C2. Dán vào Secrets
```toml
[phan_quyen]
otp_url      = "<HTTP URL của flow TKB_GuiMaDangNhap>"
admin_emails = ["it.stp@igcschool.edu.vn"]   # email được làm admin
domains      = ["igcschool.edu.vn"]          # mọi email @igcschool.edu.vn là user
```
**Save** (+ **Reboot app**) → màn hình đăng nhập hiện ô **Email của trường** và nút
**📨 Gửi mã đăng nhập**. Không nhận được thư: xem mục Thư rác/Other, hoặc mở
**Run history** của flow.

> 🔒 Ai có URL của flow đều nhờ flow gửi thư được — chỉ dán vào Secrets, không gửi
> qua chat/email.

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
