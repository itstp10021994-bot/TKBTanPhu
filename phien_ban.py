"""Phiên bản ứng dụng — TĂNG mỗi lần cập nhật (x.y.z: x đổi lớn, y thêm tính năng, z sửa lỗi)
và ghi 1 dòng vào LICH_SU (mới nhất ở đầu). Hiện ở cuối thanh bên + mục "Có gì mới"."""

PHIEN_BAN = "2.3.1"
NGAY_PHAT_HANH = "09/11/2026"

LICH_SU = [
    ("2.3.1", "09/11/2026", ["Danh sách phòng môn tự chọn in khổ A4 NGANG, mỗi phòng 1 trang."]),
    ("2.3.0", "09/11/2026", [
        "Thi tốt nghiệp — danh sách phòng môn tự chọn ghi rõ từng em: cột Môn 1 (ca 1), Môn 2 (ca 2); tiêu đề "
        "cột môn ghi kèm ca; sơ đồ chỗ ngồi ghi 'Ca 1: …  Ca 2: …'.",
    ]),
    ("2.2.0", "09/11/2026", [
        "Thi tốt nghiệp: danh sách theo lớp — SBD và phòng thi cả 4 môn (Ngữ văn, Toán, 2 môn tự chọn); "
        "xem theo lớp trên app, Excel có sheet toàn trường + mỗi lớp 1 sheet.",
    ]),
    ("2.1.0", "07/11/2026", [
        "Thi tốt nghiệp: sơ đồ chỗ ngồi từng phòng (xem trên app + in Excel mỗi phòng 1 trang) cho môn tự chọn "
        "và Toán – Ngữ văn; chỉnh số dãy bàn, hiện / ẩn họ tên.",
    ]),
    ("2.0.0", "07/11/2026", [
        "Nhập liệu bằng form: sửa / thêm / xoá nhiều dòng rồi bấm Lưu 1 lần — app không còn nhảy sau mỗi ô.",
        "Lưu SharePoint nhanh hơn: dữ liệu được nén trước khi gửi, mỗi mục chứa nhiều hơn → ít lượt ghi / đọc.",
        "Thanh bên gọn: 1 ô trạng thái lưu, số phiên bản, mục Có gì mới; tiêu đề module gọn hơn.",
        "Xếp phòng thi: hết giờ tối ưu thì tự nới ràng buộc rồi xếp lại (không rơi về cách xếp thường).",
    ]),
    ("1.9.0", "07/11/2026", [
        "Thi tốt nghiệp chia 5 bước có thanh tiến trình; tài khoản & phân quyền (admin / quản lý TKB / "
        "quản lý phòng thi / giáo viên) ngay trên app.",
    ]),
    ("1.8.0", "06/11/2026", [
        "Thi tốt nghiệp: xuất danh sách phòng đúng mẫu của trường (tiêu ngữ, kẻ dòng, gạch chéo môn không thi); "
        "Toán – Văn dùng SBD môn tự chọn, chia đều phòng; mức ưu tiên phòng; trộn lớp; sĩ số tối thiểu.",
    ]),
    ("1.7.0", "06/11/2026", [
        "Thi tốt nghiệp: tối ưu môn thi số 1 / số 2 (mỗi môn gọn 1 ca), ≤ 2 môn số 2 mỗi phòng, số môn mỗi ca.",
    ]),
    ("1.6.0", "05/11/2026", [
        "Tự động lưu lên SharePoint, tự tạo List / cột còn thiếu, nạp lại khi mở app.",
    ]),
]
