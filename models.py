"""
Data models cho hệ thống xếp thời khoá biểu.

Khái niệm cốt lõi: "Activity" (hoạt động dạy) là đơn vị lịch nhỏ nhất mà bộ
giải (solver) phải xếp vào các slot (ngày, tiết). Một Activity đại diện cho
một cặp (lớp/nhóm học sinh, môn học, giáo viên phụ trách) và có số tiết/tuần
riêng.

- Môn học bình thường của 1 lớp  -> 1 Activity, blocked_classes = [class_id]
- Tiết CLB / môn tự chọn đồng giờ trên khối -> mỗi lớp nhỏ (SubGroup) là 1
  Activity riêng nhưng cùng chung `sync_key` để bị ép xếp cùng (ngày, tiết).
- 2 giáo viên cùng dạy 1 lớp (đồng giảng) -> Activity có teachers = [gv1, gv2]
- Giờ cố định trước (phòng máy / GVNN / GVTG) -> Activity có `fixed_slots`
  điền sẵn đúng bằng periods_per_week, solver sẽ không tạo biến quyết định
  cho các tiết này mà chỉ dùng để chặn giờ bận của lớp/GV/phòng liên quan.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class Department(BaseModel):
    id: str
    name: str


class Teacher(BaseModel):
    id: str
    name: str
    department_id: Optional[str] = None


class SchoolClass(BaseModel):
    id: str
    name: str
    grade: int
    # order_group: nhóm thứ tự khi 1 GV dạy toàn trường phải xếp theo thứ tự
    # tăng dần của order_group trong cùng 1 ngày.
    # Ví dụ: K10/K11/6-ESL = 1 ; K12 = 2 ; K6,7,8,9 (thường) = 3
    order_group: int = 0


class Room(BaseModel):
    id: str
    name: str
    room_type: str = "normal"  # "normal" | "computer_lab" | ...
    capacity: int = 1  # số phòng cùng loại có thể dùng song song 1 slot


class Slot(BaseModel):
    day: int      # 1..6 (Thứ 2..Thứ 7)
    period: int   # 1..N (tiết trong ngày)


class GradeDayCapacity(BaseModel):
    """Số tiết thực tế của 1 khối vào 1 ngày cụ thể, VD Khối 6 - Thứ 2 - 4
    tiết. Nếu 1 (khối, ngày) không được khai báo ở đây, mặc định coi như
    khối đó dùng đủ toàn bộ periods_per_day của config. Các activity liên
    quan lớp thuộc khối này sẽ KHÔNG được xếp vào tiết > periods_count của
    đúng ngày đó (tiết 1..periods_count vẫn dùng bình thường)."""
    grade: int
    day: int
    periods_count: int = 0
    # Nếu điền: khối đó ngày đó CHỈ học đúng các tiết trong danh sách này
    # (VD [1,2,3,6,7] = 3 tiết sáng + 2 tiết chiều), bỏ qua periods_count.
    # Dùng khi cấu hình thời gian biểu chi tiết theo từng khối, từng ngày.
    allowed_periods: Optional[list[int]] = None


class Activity(BaseModel):
    id: str
    name: str
    subject_id: str
    periods_per_week: int
    blocked_classes: list[str] = Field(default_factory=list)
    teachers: list[str] = Field(default_factory=list)
    room_type: Optional[str] = None
    # Các activity cùng sync_key bị ép luôn nằm ở cùng (day, period)
    sync_key: Optional[str] = None
    # Nếu có sẵn (giờ phòng máy / GVNN / GVTG cố định trước), điền đúng
    # số lượng = periods_per_week, solver sẽ không xếp thêm mà chỉ khoá cứng.
    fixed_slots: list[Slot] = Field(default_factory=list)


class ScheduleConfig(BaseModel):
    days: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])
    periods_per_day: int = 10
    morning_periods: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    afternoon_periods: list[int] = Field(default_factory=lambda: [6, 7, 8, 9, 10])
    max_solver_seconds: float = 30.0


class TimetableInput(BaseModel):
    config: ScheduleConfig = Field(default_factory=ScheduleConfig)
    departments: list[Department] = Field(default_factory=list)
    teachers: list[Teacher] = Field(default_factory=list)
    classes: list[SchoolClass] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    # Mỗi tổ chuyên môn cần 1 buổi trống chung / tuần -> liệt kê tổ nào cần
    departments_needing_free_session: list[str] = Field(default_factory=list)
    # Số tiết thực tế theo (khối, ngày) — nếu khác nhau giữa các ngày/khối.
    grade_day_periods: list[GradeDayCapacity] = Field(default_factory=list)


class ScheduledLesson(BaseModel):
    activity_id: str
    activity_name: str
    subject_id: str
    class_ids: list[str]
    teacher_ids: list[str]
    day: int
    period: int


class TimetableResult(BaseModel):
    status: str  # "OPTIMAL" | "FEASIBLE" | "INFEASIBLE" | "ERROR"
    message: str = ""
    lessons: list[ScheduledLesson] = Field(default_factory=list)
    department_free_sessions: dict[str, str] = Field(default_factory=dict)
    # Chữ ký lời giải (khoá "activity_id|day|period" -> 1) cho các biến
    # KHÔNG cố định (fixed_slots) đã được chọn = 1. Dùng để tạo ràng buộc
    # "khác với lần trước" khi người dùng bấm xếp lại để có phương án khác.
    solution_signature: dict[str, int] = Field(default_factory=dict)
