"""
Dữ liệu mẫu cho trường quy mô nhỏ (~10 lớp) để minh hoạ đầy đủ các loại
ràng buộc đã yêu cầu. Dùng để test nhanh hoặc làm điểm khởi đầu khi nhập
dữ liệu thật.
"""

from .models import (
    TimetableInput, ScheduleConfig, Department, Teacher, SchoolClass,
    Room, Activity, Slot,
)


def build_sample_input() -> TimetableInput:
    config = ScheduleConfig(
        days=[1, 2, 3, 4, 5, 6],
        periods_per_day=5,
        morning_periods=[1, 2, 3],
        afternoon_periods=[4, 5],
        max_solver_seconds=30,
    )

    departments = [
        Department(id="to_toan", name="Tổ Toán"),
        Department(id="to_van", name="Tổ Văn"),
        Department(id="to_ngoaingu", name="Tổ Ngoại ngữ"),
    ]

    teachers = [
        Teacher(id="gv_toan_1", name="Cô Lan (Toán)", department_id="to_toan"),
        Teacher(id="gv_toan_2", name="Thầy Minh (Toán)", department_id="to_toan"),
        # 1 GV dạy toàn trường -> phải theo thứ tự order_group
        Teacher(id="gv_van_1", name="Cô Hoa (Văn - dạy toàn trường)", department_id="to_van"),
        Teacher(id="gv_anh_1", name="Thầy Nam (Tiếng Anh)", department_id="to_ngoaingu"),
        # GV dạy 2 phân môn khác nhau (Anh + CLB tiếng Anh)
        Teacher(id="gv_anh_2", name="Cô Mai (Tiếng Anh + CLB Debate)", department_id="to_ngoaingu"),
        Teacher(id="gv_tin", name="Thầy Đức (Tin học)", department_id=None),
        # GV nước ngoài - giờ cố định trước
        Teacher(id="gv_nn", name="Mr. John (GVNN)", department_id="to_ngoaingu"),
        # GV thỉnh giảng - giờ cố định trước
        Teacher(id="gv_tg", name="Cô Thu (GVTG - Kỹ năng sống)", department_id=None),
        # Đồng giảng cùng 1 lớp với gv_toan_1
        Teacher(id="gv_toan_tro_giang", name="Thầy Hùng (trợ giảng Toán)", department_id="to_toan"),
    ]

    classes = [
        SchoolClass(id="10A1", name="10A1", grade=10, order_group=1),
        SchoolClass(id="11A1", name="11A1", grade=11, order_group=1),
        SchoolClass(id="6ESL", name="6 ESL", grade=6, order_group=1),
        SchoolClass(id="12A1", name="12A1", grade=12, order_group=2),
        SchoolClass(id="6A1", name="6A1", grade=6, order_group=3),
        SchoolClass(id="7A1", name="7A1", grade=7, order_group=3),
    ]

    rooms = [
        Room(id="lab1", name="Phòng máy 1", room_type="computer_lab", capacity=1),
    ]

    activities: list[Activity] = []

    # --- Môn học thường, 3 tiết/tuần (không dồn 3 tiết/ngày) ---
    activities.append(Activity(
        id="toan_10a1", name="Toán 10A1", subject_id="toan",
        periods_per_week=3, blocked_classes=["10A1"], teachers=["gv_toan_1"],
    ))
    activities.append(Activity(
        id="toan_11a1", name="Toán 11A1", subject_id="toan",
        periods_per_week=3, blocked_classes=["11A1"], teachers=["gv_toan_2"],
    ))

    # --- Môn học >=4 tiết/tuần (tối đa 3 tiết/ngày) ---
    activities.append(Activity(
        id="van_10a1", name="Văn 10A1", subject_id="van",
        periods_per_week=4, blocked_classes=["10A1"], teachers=["gv_van_1"],
    ))
    activities.append(Activity(
        id="van_11a1", name="Văn 11A1", subject_id="van",
        periods_per_week=4, blocked_classes=["11A1"], teachers=["gv_van_1"],
    ))
    activities.append(Activity(
        id="van_6esl", name="Văn 6ESL", subject_id="van",
        periods_per_week=4, blocked_classes=["6ESL"], teachers=["gv_van_1"],
    ))
    activities.append(Activity(
        id="van_12a1", name="Văn 12A1", subject_id="van",
        periods_per_week=4, blocked_classes=["12A1"], teachers=["gv_van_1"],
    ))
    activities.append(Activity(
        id="van_6a1", name="Văn 6A1", subject_id="van",
        periods_per_week=4, blocked_classes=["6A1"], teachers=["gv_van_1"],
    ))
    # -> cô Hoa dạy toàn trường: 10A1/11A1/6ESL (group1) -> 12A1 (group2)
    #    -> 6A1 (group3). Ràng buộc thứ tự khối sẽ áp dụng cho GV này.

    # --- 2 giáo viên cùng dạy 1 lớp (đồng giảng) ---
    activities.append(Activity(
        id="toan_6a1_dongiang", name="Toán 6A1 (đồng giảng)", subject_id="toan",
        periods_per_week=3, blocked_classes=["6A1"],
        teachers=["gv_toan_1", "gv_toan_tro_giang"],
    ))

    # --- Đồng giờ trên khối: CLB khối 10-11, chia lớp nhỏ theo lựa chọn ---
    activities.append(Activity(
        id="clb_the_thao", name="CLB Thể thao (10A1)", subject_id="clb",
        periods_per_week=1, blocked_classes=["10A1"], teachers=["gv_toan_2"],
        sync_key="clb_khoi_10_11",
    ))
    activities.append(Activity(
        id="clb_debate", name="CLB Debate (11A1)", subject_id="clb",
        periods_per_week=1, blocked_classes=["11A1"], teachers=["gv_anh_2"],
        sync_key="clb_khoi_10_11",
    ))

    # --- Giờ GVNN cố định trước (Thứ 3, tiết 2) ---
    activities.append(Activity(
        id="gvnn_10a1", name="Tiếng Anh với GVNN (10A1)", subject_id="tieng_anh",
        periods_per_week=1, blocked_classes=["10A1"], teachers=["gv_nn"],
        fixed_slots=[Slot(day=2, period=2)],
    ))

    # --- Giờ GVTG cố định trước (Thứ 5, tiết 4) ---
    activities.append(Activity(
        id="gvtg_11a1", name="Kỹ năng sống (11A1)", subject_id="ky_nang_song",
        periods_per_week=1, blocked_classes=["11A1"], teachers=["gv_tg"],
        fixed_slots=[Slot(day=4, period=4)],
    ))

    # --- Giờ phòng máy (giới hạn 1 phòng máy -> không thể 2 lớp cùng lúc) ---
    activities.append(Activity(
        id="tin_10a1", name="Tin học 10A1", subject_id="tin_hoc",
        periods_per_week=2, blocked_classes=["10A1"], teachers=["gv_tin"],
        room_type="computer_lab",
    ))
    activities.append(Activity(
        id="tin_11a1", name="Tin học 11A1", subject_id="tin_hoc",
        periods_per_week=2, blocked_classes=["11A1"], teachers=["gv_tin"],
        room_type="computer_lab",
    ))

    # --- Tiếng Anh thường cho các lớp còn lại (để tổ Ngoại ngữ có nhiều GV bận) ---
    activities.append(Activity(
        id="anh_6a1", name="Tiếng Anh 6A1", subject_id="tieng_anh",
        periods_per_week=3, blocked_classes=["6A1"], teachers=["gv_anh_1"],
    ))
    activities.append(Activity(
        id="anh_7a1", name="Tiếng Anh 7A1", subject_id="tieng_anh",
        periods_per_week=3, blocked_classes=["7A1"], teachers=["gv_anh_1"],
    ))
    activities.append(Activity(
        id="anh_12a1", name="Tiếng Anh 12A1", subject_id="tieng_anh",
        periods_per_week=3, blocked_classes=["12A1"], teachers=["gv_anh_2"],
    ))

    return TimetableInput(
        config=config,
        departments=departments,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        activities=activities,
        # Tổ Ngoại ngữ cần 1 buổi trống chung / tuần
        departments_needing_free_session=["to_ngoaingu"],
    )
