# Đăng thời khoá biểu lên Microsoft Teams

Admin bấm **📢 Công bố** (module 👥, tick **"Đồng thời đăng lên Microsoft Teams"**) →
ứng dụng tạo tệp và đăng lên kênh Teams **giống như đăng tay**:

- **Bài đăng** trong kênh: tiêu đề, ngày áp dụng, **ảnh thời khoá biểu** của vài lớp
  (chọn được) hiện ngay trong bài, **thẻ tệp** PDF/Excel bấm vào là mở;
- **Tệp** lưu trong thư mục chỉ định của kênh (tab Tệp):
  `TKB_Lop_<ngày giờ>.pdf/.xlsx` (mỗi lớp 1 trang/sheet),
  `TKB_GiaoVien_<ngày giờ>.pdf/.xlsx` (mỗi giáo viên 1 trang/sheet),
  `Lich_coi_thi_<ngày giờ>.xlsx` (nếu đã phân công coi thi).

Tên tệp có ngày giờ nên bản cũ vẫn giữ. Không cần quyền admin — flow chạy bằng tài
khoản của bạn (phải là thành viên nhóm Teams; cần Power Automate Premium cho trigger
HTTP như các flow khác). Đăng lại khi lỗi: nút **📤 Chỉ đăng lên Teams**.

---

## Bước 0 — Lấy thông tin kênh
1. Trong Teams, vào kênh muốn đăng → tab **Tệp (Files / Shared)** → **+ Mới → Thư
   mục**, VD `Thời khoá biểu`.
2. **Link kênh**: bấm **⋯** cạnh tên kênh → **Lấy liên kết đến kênh (Get link to
   channel)** → **Sao chép**. Dạng:
   `https://teams.microsoft.com/l/channel/19%3a....%40thread.tacv2/Tên kênh?groupId=....&tenantId=....`
3. **Địa chỉ site**: tab Tệp → **⋯ → Mở trong SharePoint** → lấy phần đầu địa chỉ đến
   hết `/sites/<TênNhóm>`, VD `https://eduttc.sharepoint.com/sites/TPDayHoc`.
4. **Thư mục tệp của kênh**: trong trang SharePoint vừa mở, đường dẫn thường là
   `Shared Documents/<Tên kênh>` (kênh *Chung* hay có tên `General`). Ghi dạng
   `/Shared Documents/General`.

## Bước 1 — Tạo flow `TKB_DangTeams`
https://make.powerautomate.com → **+ Tạo → Luồng đám mây tức thì** → trigger
**When a HTTP request is received** → **Tạo**.

1. **Trigger**: *Who can trigger the flow* = **Anyone**; *Request Body JSON Schema*:
   ```json
   {"type": "object", "properties": {
     "thao_tac": {"type": "string"},
     "duong_dan": {"type": "string"},
     "thu_muc": {"type": "string"},
     "files": {"type": "array", "items": {"type": "object", "properties": {
       "ten": {"type": "string"}, "noi_dung_base64": {"type": "string"}}}},
     "graph_uri": {"type": "string"},
     "graph_body": {"type": "object"}}}
   ```
2. **Initialize variable** (ngay sau trigger): *Name* `ket_qua`, *Type* **Array**,
   *Value* `[]`.
3. **Condition**: ô trái (fx) `triggerBody()?['thao_tac']` · **is equal to** · `luu_tep`.

**Nhánh True — lưu tệp:**

4. **Apply to each** — *Select an output*: ô **files**. Bên trong, lần lượt:
   - **SharePoint → Create file** (đổi tên bước thành `Create_file`):
     *Site Address* = địa chỉ site (Bước 0.3) ·
     *Folder Path* = ô **duong_dan** (Dynamic content của trigger) ·
     *File Name* = ô **ten** ·
     *File Content* (fx) = `base64ToBinary(item()?['noi_dung_base64'])`
   - **Append to array variable**: *Name* `ket_qua`, *Value* (fx) = `body('Create_file')`
5. Sau vòng lặp: **Response** — *Status Code* `200`, *Body* (fx) = `variables('ket_qua')`

**Nhánh False — đăng bài:**

6. **Microsoft Teams → Send a Microsoft Graph HTTP request**:
   *URI* = ô **graph_uri** · *Method* `POST` ·
   *Body* (fx) = `triggerBody()?['graph_body']` ·
   *Content-Type* `application/json`
7. **Response** — *Status Code* `200`, *Body* `{"ok": true}`

**Save** → mở lại trigger → copy **HTTP URL**.

> Thư mục chỉ định phải **tạo trước** (Bước 0.1). Tên thư mục trong Secrets
> (`thu_muc`) phải đúng y tên đó.

## Bước 2 — Secrets
Streamlit Cloud → **Manage app → Settings → Secrets**:
```toml
[teams]
flow_url     = "<HTTP URL của flow TKB_DangTeams>"
kenh_link    = "<link kênh ở Bước 0.2>"
site_url     = "https://eduttc.sharepoint.com/sites/TPDayHoc"
thu_muc_kenh = "/Shared Documents/General"
thu_muc      = "Thời khoá biểu"
app_url      = "https://tkbtanphu.streamlit.app/"
```
**Save** → module 👥 hiện ô **📤 Đồng thời đăng lên Microsoft Teams (… bài đăng có
ảnh TKB và thẻ tệp)** và ô chọn **lớp hiện ảnh** trong bài (mặc định 2 lớp đầu).

> 🔒 Không gửi URL của flow qua chat/email — chỉ dán vào Secrets.

## Lỗi thường gặp
| Ứng dụng báo | Cách sửa |
|---|---|
| 401 / "Who can trigger" | Trigger để **Anyone**, copy lại HTTP URL sau khi Save |
| 502 / 504 | **Run history** của flow → bước đỏ: sai *Site Address*, thư mục chưa tạo, sai tên bước `Create_file`, thiếu **Response** |
| "Một số tệp không hiện dạng thẻ" | Thiếu bước **Append to array variable** hoặc Response không trả `variables('ket_qua')` → bài đăng dùng đường link thay thẻ |
| Bài đăng lỗi 403 ở bước Graph | Tài khoản tạo flow chưa là thành viên nhóm / kênh riêng tư |

---

## Chế độ đơn giản (không có ảnh / thẻ tệp)
Nếu **không** khai báo `kenh_link` + `site_url`, ứng dụng gọi flow 1 lần với
`{thu_muc, thong_diep, files}`: flow chỉ cần *Apply to each → Create file* (Folder
Path = `/Shared Documents/General/` + ô **thu_muc**) rồi **Post message in a chat or
channel** với *Message* = ô **thong_diep**, và **Response** 200 — tin nhắn là chữ
kèm danh sách tên tệp.
