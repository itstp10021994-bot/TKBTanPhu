# Hệ thống Xếp Thời Khoá Biểu

Ứng dụng web full-stack xếp thời khoá biểu trường học tự động bằng
**Google OR-Tools CP-SAT**, encode đầy đủ các ràng buộc:

1. Lệch giờ giữa các khối khi 1 GV dạy toàn trường (K10/11/6-ESL → K12 → K6-9).
2. Đồng giờ trên khối (tiết CLB / môn tự chọn, chia lớp nhỏ theo GV).
3. 2 giáo viên cùng dạy 1 lớp (đồng giảng).
4. 1 giáo viên dạy 2-3 phân môn khác nhau.
5. Buổi trống chung cho từng tổ chuyên môn (1 buổi/tuần).
6. Giờ phòng máy / GVNN / GVTG cố định trước.
7. Môn 3 tiết/tuần: không dồn cả 3 tiết trong 1 ngày (tối đa 2 tiết/ngày).
8. Môn 4 tiết/tuần: không dồn 3 tiết trong 1 ngày (tối đa 2 tiết/ngày).
   Môn ≥5 tiết/tuần: mỗi ngày tối đa 3 tiết.
9. Không ngắt quãng: nếu 1 ngày có ≥2 tiết của cùng 1 môn, các tiết đó phải
   liền kề nhau (không xếp kiểu Tiết A → môn khác → lại Tiết A).
10. Số tiết thực tế theo (khối, ngày): 1 khối có thể có ngày học 4 tiết,
    ngày khác học 5 tiết — khối/ngày nào không khai báo riêng thì dùng đủ
    "Số tiết/ngày tối đa" mặc định. Đây là ràng buộc THẬT áp trực tiếp vào
    bộ giải, không phải chỉ hiển thị.

Bản Streamlit (`streamlit_app/`) còn có thêm:
- Nhập/xuất **Excel (.xlsx)** cho từng bảng dữ liệu (Tổ, GV, Lớp, Phòng, Môn học,
  Giờ học theo khối) và cho chính kết quả thời khoá biểu.
- Xuất kết quả ra **PDF** (font tiếng Việt đầy đủ, nhúng sẵn font — chạy tốt cả
  khi deploy Streamlit Cloud).
- **Thời gian biểu theo từng khối, từng ngày** (tab Cấu hình chung, mục 2): mỗi
  dòng = Khối | Thứ | Tiết | Giờ bắt đầu | Giờ kết thúc. Cột Thứ chọn "Tất cả các
  ngày" để dùng chung cả tuần, dòng của ngày cụ thể được ưu tiên; Tiết = 0 là
  khối nghỉ cả ngày. Khối đã khai báo thì ngày đó CHỈ được xếp vào đúng các
  tiết có trong bảng (ràng buộc thật cho bộ giải — thay cho bảng "Số tiết mỗi
  ngày theo khối" cũ). Có nút **⚡ Tạo nhanh** sinh giờ tự động theo giờ vào
  học, thời lượng tiết, giờ ra chơi cho nhiều khối/ngày cùng lúc, và bảng xem
  lại dạng lưới cho từng khối. Nếu giờ của 1 tiết khác nhau giữa các ngày thì
  kết quả TKB (màn hình/PDF/Excel) ghi giờ ngay trong từng ô.
- Checkbox bật/tắt từng ràng buộc tuỳ chọn, ràng buộc cốt lõi hiện khoá 🔒 để
  biết hệ thống luôn áp dụng gì.
- **"🔀 Xếp phương án khác"**: sau khi xếp thành công, bấm nút này để CP-SAT tìm
  1 cách sắp xếp KHÁC với các phương án trước (không lặp lại), rồi chọn qua lại
  giữa các phương án đã tạo ra trong phiên làm việc qua ô "📋 Chọn phương án".
- Giao diện chia thành nhiều tab: Cấu hình chung, Tổ/GV/Lớp/Phòng, Môn học &
  phân công, Ràng buộc & Xếp lịch, Kết quả, **Phòng thi** — dễ theo dõi hơn so
  với 1 trang dài. Giao diện dùng hiệu ứng đổ bóng nhiều lớp kiểu 3D (nút bấm
  nổi khi hover, ấn xuống khi bấm, card có glow nhẹ) tông xanh navy + xám.
- **Xếp phòng thi** (độc lập với việc xếp thời khoá biểu): **upload file danh
  sách học sinh** (Excel/CSV) gồm SBD (hoặc Mã HS, để trống thì tự sinh), Lớp,
  Môn thi — KHÔNG cần họ tên. Vì 1 lớp có thể có nhiều môn lựa chọn, môn thi
  khai báo riêng cho từng học sinh theo 1 trong 3 kiểu: cột "Môn thi" ghi nhiều
  môn cách nhau dấu phẩy / mỗi môn 1 dòng (tự gộp theo SBD) / mỗi môn 1 cột
  đánh dấu x. Mỗi môn thi tự lấy đúng học sinh đăng ký môn đó ("Lớp áp dụng"
  chỉ còn là bộ lọc tuỳ chọn). SBD được sinh 1 lần cho mỗi học sinh nên giữ
  nguyên ở mọi môn; có cảnh báo SBD trùng và học sinh trùng lịch thi (cùng
  ngày, cùng ca). **Sơ đồ chỗ ngồi chỉ ghi số báo danh**; danh sách phòng /
  thẻ báo danh mặc định không có họ tên (bật checkbox nếu cần). Hỗ trợ 2 chế
  độ xếp chỗ theo từng môn thi:
  - **Theo lớp**: giữ nguyên từng lớp, chỉ tách sang phòng khác khi 1 lớp
    đông hơn sức chứa 1 phòng.
  - **Trộn theo khối**: xáo học sinh từ các lớp khác nhau ngồi xen kẽ nhau
    trong phòng, hạn chế quay cóp giữa các bạn cùng lớp.

  Xuất được **PDF** (danh sách theo từng phòng có cột ký tên, sơ đồ chỗ ngồi,
  thẻ báo danh), **Excel** theo phòng, và 1 file Excel tổng hợp SBD + phòng
  thi từng môn của mỗi học sinh.
- **☁️ Lưu trữ SharePoint** (module mới ở thanh bên trái): lưu/tải toàn bộ dữ
  liệu (bảng nhập liệu, cấu hình, kết quả TKB, phòng thi, dạy thay) lên thư
  viện tài liệu SharePoint — mỗi lần lưu tạo `<tên>.json` (để nạp lại) và
  `<tên>.xlsx` (xem trên SharePoint). Kết nối bằng Microsoft Graph (App
  Registration) hoặc qua flow Power Automate; cấu hình trong Secrets, xem
  **HUONG_DAN_SHAREPOINT.md**. Có thêm sao lưu/khôi phục file `.json` trên máy.
  Còn **đồng bộ trực tiếp từng bảng ⇄ SharePoint List** — qua Microsoft Graph,
  hoặc qua 1 flow Power Automate chạy bằng tài khoản người dùng (không cần
  admin, dùng được với "Danh sách của tôi")
  (ToChuyenMon, GiaoVien, LopHoc, ... — cột khớp theo tên hiển thị), kèm nút
  kiểm tra List/cột và file Excel mẫu để tạo List bằng "Từ Excel".
- **Ngày thực tế theo lịch**: chọn "Ngày bắt đầu tuần (Thứ 2)" ở tab Cấu hình
  chung, mọi nơi hiển thị "Thứ 2/3/4..." sẽ kèm luôn ngày thật (VD "Thứ 2
  (08/09)") trên màn hình, PDF và Excel.
- **Chia buổi sáng/chiều**: lưới thời khoá biểu (màn hình, PDF, Excel) tự
  chèn dòng ngăn "BUỔI SÁNG" / "BUỔI CHIỀU" dựa theo cấu hình "Số tiết buổi
  sáng" ở tab Cấu hình chung.

> **Lưu ý quan trọng**: môi trường soạn thảo mà mình dùng để viết code này
> không có kết nối mạng nên **chưa cài được `ortools`/`fastapi` để chạy thử
> trực tiếp**. Code đã được kiểm tra cú pháp (`py_compile`) và logic được
> viết cẩn thận theo đúng API của OR-Tools CP-SAT, nhưng bạn cần tự chạy
> `pip install -r requirements.txt` rồi test với dữ liệu mẫu trước khi dùng
> dữ liệu thật — nếu gặp lỗi khi chạy, gửi lại log để mình sửa tiếp.
> Các phần KHÔNG cần `ortools` (xuất Excel, xuất PDF, nhãn giờ theo khối) đã
> được chạy thử trực tiếp trong lúc viết code và cho kết quả đúng.


## Cấu trúc dự án

```
timetable-app/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app (API endpoints)
│       ├── models.py        # Pydantic schemas (Teacher, Class, Activity, ...)
│       ├── scheduler.py     # Bộ giải CP-SAT — nơi encode toàn bộ ràng buộc
│       └── sample_data.py   # Dữ liệu mẫu minh hoạ đủ 8 loại ràng buộc
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── styles.css
│       └── components/
│           ├── DataEditor.jsx     # Soạn dữ liệu đầu vào (JSON)
│           └── TimetableGrid.jsx  # Hiển thị kết quả solver (read-only, không chỉnh tay)
└── streamlit_app/            # Bản thay thế đơn giản, thuần Python
    ├── app.py                # Giao diện Streamlit
    ├── models.py             # (bản sao models.py dùng chung logic)
    ├── scheduler.py          # (bản sao scheduler.py dùng chung logic)
    ├── sample_data.py
    └── requirements.txt
```

## Cách chạy

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Kiểm tra nhanh: mở `http://localhost:8000/api/sample-data` phải trả về JSON
dữ liệu mẫu; `http://localhost:8000/docs` xem Swagger UI để test API
`/api/generate` trực tiếp.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`. Bấm **"Tải dữ liệu mẫu"** → **"Xếp thời khoá
biểu"** để xem kết quả minh hoạ. Frontend gọi tới backend qua proxy `/api`
(cấu hình sẵn trong `vite.config.js`, trỏ tới `localhost:8000`).

### 3. Bản Streamlit (thay thế đơn giản cho backend+frontend)

Nếu không muốn cài Node.js/React, có thể chạy thẳng bằng Streamlit (thuần
Python, dùng lại đúng bộ solver trong `scheduler.py`):

```bash
cd streamlit_app
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Trình duyệt sẽ tự mở `http://localhost:8501`. Giao diện: nhập **Giáo viên /
Lớp học / Môn học & phân công** trực tiếp vào các bảng dạng Excel (bấm dấu
**+** để thêm dòng), không cần biết JSON → bấm "Xếp thời khoá biểu" → xem
lịch theo từng lớp (dạng tab).

## Đưa lên GitHub & deploy Streamlit Cloud (miễn phí)

```bash
cd timetable-app
git init
git add .
git commit -m "Initial commit: timetable scheduler"
```

Sau đó tạo 1 repo mới trên https://github.com/new (đặt tên tuỳ ý, để
Public hoặc Private đều được), rồi nối repo local với remote:

```bash
git remote add origin https://github.com/<username>/<ten-repo>.git
git branch -M main
git push -u origin main
```

**Deploy Streamlit Cloud:**
1. Vào https://share.streamlit.io, đăng nhập bằng tài khoản GitHub.
2. Bấm **"New app"** → chọn đúng repo vừa đẩy lên.
3. **Main file path**: gõ `streamlit_app/app.py`
4. Bấm **Deploy** — Streamlit Cloud sẽ tự cài `streamlit_app/requirements.txt`
   và cho ra 1 đường link public dạng `https://<ten-app>.streamlit.app` để
   chia sẻ, không cần cài gì trên máy người xem.

> Lưu ý: bản Streamlit và bản backend/frontend (React) dùng chung logic
> solver (`scheduler.py`/`models.py`) nhưng là 2 file riêng — nếu bạn sửa
> ràng buộc trong `backend/app/scheduler.py`, nhớ áp dụng thay đổi tương tự
> vào `streamlit_app/scheduler.py` để 2 bản luôn đồng bộ.

## Cập nhật giao diện (bản Streamlit)

Bản `streamlit_app/` đã được nâng cấp:

- **Giao diện mới**: tông xanh đậm (navy) + xám, dạng thẻ (card), nút bấm và
  tab bo góc hiện đại hơn — xem `app.py` (CSS ở đầu file) và `exports.py`.
- **Excel cho từng mục**: mỗi bảng (Tổ chuyên môn / Giáo viên / Lớp học /
  Phòng đặc biệt / Môn học & phân công) đều có nút **📥 Xuất Excel** (tải
  đúng dữ liệu hiện tại ra `.xlsx`) và **📤 Nhập từ Excel** (tải file `.xlsx`
  lên để thay thế toàn bộ bảng đó — tiện khi đã có sẵn danh sách trong Excel
  hoặc muốn nhiều người cùng điền rồi gộp lại).
- **Ràng buộc dạng checkbox**: mục "6. Ràng buộc áp dụng khi xếp lịch" liệt
  kê rõ ràng buộc nào **cốt lõi** (khoá cứng, luôn bật — không trùng giờ
  GV/lớp, đồng bộ tiết chung, giờ cố định trước) và ràng buộc nào **tuỳ
  chọn** có thể tắt bằng checkbox (không dồn tiết/ngày, lệch giờ theo khối,
  giới hạn phòng đặc biệt, buổi trống chung theo tổ).
- **Xuất kết quả**: sau khi xếp xong, có nút **📄 Xuất PDF** (thời khoá biểu
  đầy đủ, mỗi lớp 1 trang, font tiếng Việt nhúng sẵn trong `assets/`) và
  **📊 Xuất Excel** (mỗi lớp 1 sheet).

Cần cài thêm `openpyxl` (đọc/ghi Excel) và `reportlab` (xuất PDF) — đã có
sẵn trong `streamlit_app/requirements.txt`.

> Lưu ý: các cập nhật giao diện này chỉ áp dụng cho bản **Streamlit**
> (`streamlit_app/`), vì đây là bản dùng bảng nhập liệu kiểu Excel — khớp
> với yêu cầu nhập/xuất Excel theo từng mục. Bản `backend/` + `frontend/`
> (FastAPI + React, nhập liệu bằng JSON) chưa được chỉnh theo yêu cầu này.

## Khái niệm dữ liệu cốt lõi: "Activity"

Thay vì mô hình hoá riêng "môn học của lớp" và "phân công GV" tách rời,
mọi thứ được gộp vào **1 `Activity`** = một khối cần xếp lịch:

| Trường | Ý nghĩa |
|---|---|
| `periods_per_week` | Số tiết/tuần — solver dùng để áp ràng buộc phân bổ (3 tiết không dồn ngày / ≥4 tiết tối đa 3 tiết-ngày). |
| `blocked_classes` | Lớp nào bị "chiếm chỗ" bởi activity này (thường 1 lớp). |
| `teachers` | 1 GV bình thường, hoặc 2 GV nếu đồng giảng. |
| `sync_key` | Đặt cùng giá trị cho các activity phải luôn học **cùng giờ** (VD các lớp nhỏ CLB của cùng khối). |
| `room_type` + `Room.capacity` | Dùng cho ràng buộc phòng học giới hạn số lượng (VD chỉ có 1 phòng máy). |
| `fixed_slots` | Nếu điền đủ số slot bằng `periods_per_week` → coi là **cố định trước** (giờ phòng máy/GVNN/GVTG đã chốt), solver không xếp lại mà chỉ dùng để chặn giờ bận liên quan. |

Ràng buộc "lệch giờ theo khối" dựa vào `SchoolClass.order_group`
(1 = K10/K11/6-ESL, 2 = K12, 3 = K6-9 thường — bạn có thể đổi số này tuỳ
cách chia thực tế của trường). Với mỗi GV dạy từ 2 `order_group` trở lên,
solver ép: trong cùng 1 ngày, mọi tiết của nhóm thấp hơn phải xong trước
khi nhóm cao hơn bắt đầu (không xen kẽ).

Ràng buộc "buổi trống chung theo tổ" khai báo qua
`departments_needing_free_session: ["to_ngoaingu", ...]` — solver sẽ tự
chọn ra đúng 1 (ngày, buổi sáng/chiều) mỗi tuần mà **toàn bộ GV của tổ đó**
rảnh hoàn toàn.

## Giới hạn hiện tại / việc cần làm tiếp

- Chưa có xác thực (auth), chưa có lưu trữ DB lâu dài (dữ liệu chỉ tồn tại
  trong session trình duyệt qua JSON) — cần thêm PostgreSQL + CRUD API nếu
  triển khai thật cho nhà trường quản lý dữ liệu lâu dài.
- Hệ thống chạy **hoàn toàn tự động** theo ràng buộc khai báo — bảng kết
  quả (`TimetableGrid.jsx`) chỉ hiển thị, không có thao tác chỉnh tay/kéo-
  thả. Mọi thay đổi phải đi qua việc sửa dữ liệu/ràng buộc đầu vào rồi chạy
  lại solver, để đảm bảo lịch luôn hợp lệ 100% theo đúng ràng buộc của
  trường.
- Ràng buộc phòng học hiện chỉ áp dụng cho `room_type` (VD phòng máy);
  chưa gán phòng học cụ thể cho môn học thường (nếu trường cần lớp học cố
  định theo phòng riêng, có thể bổ sung thêm).
- Với dữ liệu thật lớn hơn nhiều so với mẫu (nhiều lớp, nhiều tiết/ngày),
  nên tăng `max_solver_seconds` trong `config` nếu CP-SAT báo INFEASIBLE
  do chưa đủ thời gian tìm lời giải (khác với thực sự vô nghiệm).
