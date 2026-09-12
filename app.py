"""
Ứng dụng Streamlit: xếp thời khoá biểu tự động 100% theo ràng buộc.
Giao diện dạng BẢNG NHẬP LIỆU (giống Excel) — không cần biết JSON.

Chạy local:  streamlit run app.py
Deploy:      đẩy lên GitHub rồi deploy trên https://share.streamlit.io
"""

import random
import re
import unicodedata
from datetime import date, timedelta

import streamlit as st
import pandas as pd

from models import (
    TimetableInput, ScheduleConfig, Department, Teacher, SchoolClass,
    Room, Activity, Slot, GradeDayCapacity,
)
from scheduler import solve_timetable, SchedulerError
from exports import (
    df_to_excel_bytes, timetable_to_pdf_bytes, exam_rooms_to_excel_bytes,
    exam_rooms_to_pdf_bytes, substitution_to_pdf_bytes,
)
import exam_rooms as er

st.set_page_config(page_title="Xếp Thời Khoá Biểu", layout="wide", page_icon="🗓️")

DAY_NAMES = {1: "Thứ 2", 2: "Thứ 3", 3: "Thứ 4", 4: "Thứ 5", 5: "Thứ 6", 6: "Thứ 7", 7: "CN"}

# =======================================================================
# GIAO DIỆN — tông xanh đậm (navy) + xám, kiểu "dashboard" hiện đại
# =======================================================================
st.markdown("""
<style>
:root{
    --navy-900:#0B1E39;
    --navy-800:#122A4E;
    --navy-700:#1D3E68;
    --navy-600:#2C5282;
    --accent-500:#2F7DE1;
    --accent-400:#4C9AFF;
    --accent-glow:rgba(47,125,225,0.35);
    --navy-100:#E9EFF7;
    --gray-50:#F3F6FB;
    --gray-100:#EAEFF6;
    --gray-200:#DCE3EE;
    --gray-500:#69758A;
    --text-900:#16233A;
}
html, body, [class*="css"]{ font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif; }
.stApp{
    background:
        radial-gradient(1100px 500px at 8% -10%, rgba(76,154,255,0.10), transparent 60%),
        radial-gradient(900px 460px at 100% 0%, rgba(47,125,225,0.08), transparent 55%),
        linear-gradient(180deg, var(--gray-50) 0%, var(--gray-100) 100%);
}

/* ---- Header banner (nổi khối, có glow nhẹ) ---- */
.app-hero{
    background:linear-gradient(135deg, var(--navy-900) 0%, var(--navy-700) 55%, var(--navy-600) 100%);
    padding:30px 34px; border-radius:22px; margin-bottom:24px;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.08) inset,
        0 18px 40px -14px rgba(11,30,57,0.55),
        0 0 0 1px rgba(255,255,255,0.04) inset;
    position:relative; overflow:hidden;
}
.app-hero::after{
    content:""; position:absolute; inset:0; pointer-events:none;
    background:radial-gradient(420px 180px at 85% -20%, rgba(76,154,255,0.35), transparent 70%);
}
.app-hero h1{ color:#fff; font-size:1.7rem; margin:0 0 6px 0; font-weight:800; letter-spacing:.2px;
    text-shadow:0 2px 10px rgba(0,0,0,0.25);}
.app-hero p{ color:#CBD9EE; margin:0; font-size:0.93rem; line-height:1.55; position:relative; z-index:1;}

/* ---- Section card: hiệu ứng nổi khối 3D, đổ bóng 2 lớp mềm ---- */
.section-card{
    background:linear-gradient(180deg, #FFFFFF 0%, #FBFCFE 100%);
    border:1px solid var(--gray-200); border-radius:18px;
    padding:20px 22px 10px 22px; margin-bottom:20px;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.7) inset,
        0 2px 6px -2px rgba(18,41,75,0.08),
        0 16px 32px -18px rgba(18,41,75,0.28);
    transition:box-shadow .2s ease, transform .2s ease;
}
.section-card:hover{
    box-shadow:
        0 1px 0 rgba(255,255,255,0.7) inset,
        0 4px 10px -2px rgba(18,41,75,0.10),
        0 22px 40px -16px rgba(18,41,75,0.32);
}
.section-title{
    display:flex; align-items:center; gap:10px; margin-bottom:2px;
}
.section-badge{
    background:linear-gradient(145deg, var(--accent-400), var(--navy-800));
    color:#fff; font-size:0.78rem; font-weight:700;
    width:28px; height:28px; border-radius:9px; display:flex; align-items:center;
    justify-content:center; flex-shrink:0;
    box-shadow:0 3px 8px -1px var(--accent-glow), 0 1px 0 rgba(255,255,255,0.4) inset;
}
.section-title h3{ margin:0; color:var(--navy-900); font-size:1.06rem; font-weight:800;}
.section-sub{ color:var(--gray-500); font-size:0.86rem; margin:2px 0 14px 38px; line-height:1.5;}

/* ---- Buttons: kiểu nút 3D nổi, nhấn xuống khi bấm ---- */
.stButton>button, .stDownloadButton>button{
    border-radius:12px !important; border:1px solid var(--gray-200) !important;
    font-weight:700 !important; color:var(--navy-800) !important; background:#fff !important;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.8) inset,
        0 3px 8px -2px rgba(18,41,75,0.18) !important;
    transition:transform .12s ease, box-shadow .12s ease !important;
}
.stButton>button:hover, .stDownloadButton>button:hover{
    transform:translateY(-1px);
    box-shadow:
        0 1px 0 rgba(255,255,255,0.8) inset,
        0 8px 16px -4px rgba(18,41,75,0.24) !important;
    background:var(--navy-100) !important;
}
.stButton>button:active, .stDownloadButton>button:active{
    transform:translateY(1px);
    box-shadow:0 2px 4px -1px rgba(18,41,75,0.20) !important;
}
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"]{
    background:linear-gradient(145deg, var(--accent-400) 0%, var(--navy-800) 100%) !important;
    color:#fff !important; border:none !important;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.25) inset,
        0 10px 22px -6px var(--accent-glow) !important;
}
.stButton>button[kind="primary"]:hover, .stDownloadButton>button[kind="primary"]:hover{
    box-shadow:
        0 1px 0 rgba(255,255,255,0.3) inset,
        0 14px 28px -6px var(--accent-glow) !important;
}

/* ---- Tabs: dạng viên thuốc nổi khối ---- */
.stTabs [data-baseweb="tab-list"]{ gap:6px; border-bottom:2px solid var(--gray-200); padding-bottom:2px;}
.stTabs [data-baseweb="tab"]{
    background:var(--gray-100); border-radius:12px 12px 0 0; padding:9px 18px;
    color:var(--navy-800); font-weight:700; transition:all .15s ease;
}
.stTabs [aria-selected="true"]{
    background:linear-gradient(145deg, var(--navy-800), var(--navy-900)) !important; color:#fff !important;
    box-shadow:0 -3px 10px -3px rgba(18,41,75,0.35);
}

/* ---- Expander (cấu hình) ---- */
.streamlit-expanderHeader{
    background:linear-gradient(145deg, var(--navy-800), var(--navy-900)) !important;
    color:#fff !important; border-radius:12px !important;
}

/* ---- Constraint checkbox rows: nổi nhẹ, bo tròn hơn ---- */
.constraint-row{
    background:#fff; border:1px solid var(--gray-200); border-radius:13px;
    padding:11px 15px; margin-bottom:9px;
    box-shadow:0 2px 6px -3px rgba(18,41,75,0.12);
}
.constraint-row b{ color:var(--navy-900); }
.constraint-locked{
    background:var(--navy-100); border:1px solid var(--navy-100);
    box-shadow:none;
}

/* ---- Status pill ---- */
.status-ok{
    background:linear-gradient(145deg, #E9F8EF, #DDF3E6); color:#1B7A45; border:1px solid #BFE8CE;
    padding:11px 18px; border-radius:13px; font-weight:700;
    box-shadow:0 4px 12px -6px rgba(27,122,69,0.35);
}

/* ---- Sơ đồ chỗ ngồi ---- */
.seating-chart{ margin:10px 0 20px 0; }
.board-label{
    text-align:center; background:linear-gradient(145deg, var(--navy-800), var(--navy-900));
    color:#fff !important; padding:10px; border-radius:10px; margin-bottom:16px;
    font-weight:800; letter-spacing:1.5px; font-size:0.85rem;
    box-shadow:0 6px 14px -6px rgba(18,41,75,0.4);
}
.seat-row{ display:flex; gap:10px; margin-bottom:10px; justify-content:center; flex-wrap:wrap; }
.seat{
    width:104px; min-height:64px; border-radius:10px; display:flex; flex-direction:column;
    align-items:center; justify-content:center; text-align:center; padding:6px;
}
.seat.filled{
    background:linear-gradient(180deg, #FFFFFF 0%, #FBFCFE 100%);
    border:1.5px solid var(--navy-700);
    box-shadow:0 4px 10px -4px rgba(18,41,75,0.30), 0 1px 0 rgba(255,255,255,0.7) inset;
}
.seat.empty{ background:var(--gray-100); border:1.5px dashed var(--gray-200); }
.seat-sbd{ font-weight:800; color:var(--navy-800) !important; font-size:0.86rem; }
.seat-name{ color:var(--text-900) !important; font-size:0.72rem; line-height:1.2; margin-top:2px; }
.seat-class{ color:var(--gray-500) !important; font-size:0.68rem; margin-top:1px; }

/* ---- Footer ---- */
.app-footer{
    text-align:center; color:var(--gray-500); font-size:0.82rem;
    margin-top:32px; padding-top:16px; border-top:1px solid var(--gray-200);
}

/* ---- Sidebar: thanh dọc chuyển module ---- */
section[data-testid="stSidebar"]{
    background:linear-gradient(180deg, var(--navy-900) 0%, #0A1730 100%);
    box-shadow:4px 0 20px -8px rgba(0,0,0,0.35);
}
section[data-testid="stSidebar"] *{ color:#E7EEF9 !important; }
.sidebar-brand{
    font-size:1.05rem; font-weight:800; color:#fff !important; line-height:1.35;
    padding:6px 2px 16px 2px; margin-bottom:10px;
    border-bottom:1px solid rgba(255,255,255,0.14);
}
section[data-testid="stSidebar"] [data-baseweb="radio"]{
    background:rgba(255,255,255,0.05); border-radius:12px; padding:4px;
}
section[data-testid="stSidebar"] label{
    padding:10px 12px !important; border-radius:10px !important; margin-bottom:4px !important;
    transition:background .15s ease;
}
section[data-testid="stSidebar"] label:hover{ background:rgba(255,255,255,0.08) !important; }
section[data-testid="stSidebar"] .stButton>button{
    background:rgba(255,255,255,0.06) !important; color:#fff !important;
    border:1px solid rgba(255,255,255,0.18) !important; box-shadow:none !important;
}
section[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(255,255,255,0.14) !important; transform:none;
}
section[data-testid="stSidebar"] hr{ border-color:rgba(255,255,255,0.14) !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-hero">
  <h1>🗓️ Hệ thống Xếp Thời Khoá Biểu</h1>
  <p>Nhập dữ liệu trực tiếp (giống Excel) hoặc nhập/xuất file <b>.xlsx</b> cho từng mục.
  Chọn ràng buộc cần áp dụng, bấm <b>Xếp thời khoá biểu</b> — hệ thống dùng CP-SAT giải tự động
  100%, sau đó có thể xuất kết quả ra <b>PDF</b> hoặc <b>Excel</b>, hoặc bấm xếp lại để có thêm
  phương án khác.</p>
</div>
""", unsafe_allow_html=True)


def slugify(text: str, prefix: str = "") -> str:
    """Tự sinh mã (id) ngắn gọn từ tên tiếng Việt, VD 'Cô Lan (Toán)' -> 'co_lan_toan'."""
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return f"{prefix}{text}" if text else f"{prefix}x"


def dedupe_ids(raw_ids: list[str]) -> list[str]:
    """Nếu 2 dòng tạo ra cùng 1 id (trùng tên), tự thêm số phân biệt."""
    seen: dict[str, int] = {}
    result = []
    for rid in raw_ids:
        if rid not in seen:
            seen[rid] = 0
            result.append(rid)
        else:
            seen[rid] += 1
            result.append(f"{rid}_{seen[rid]}")
    return result


def section_header(number: str, title: str, subtitle: str = ""):
    sub_html = f'<div class="section-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="section-title"><div class="section-badge">{number}</div><h3>{title}</h3></div>
    {sub_html}
    """, unsafe_allow_html=True)


def excel_io_row(state_key: str, label: str):
    """Thanh công cụ Xuất/Nhập Excel cho 1 bảng dữ liệu (session_state[state_key])."""
    c1, c2 = st.columns(2)
    df_now = st.session_state[state_key]
    with c1:
        st.download_button(
            "📥 Xuất Excel",
            data=df_to_excel_bytes(df_now, label),
            file_name=f"{state_key}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_{state_key}",
        )
    with c2:
        uploaded = st.file_uploader(
            "📤 Nhập từ Excel (thay thế bảng)", type=["xlsx"],
            key=f"up_{state_key}", label_visibility="visible",
        )
        if uploaded is not None:
            marker = f"{uploaded.name}:{uploaded.size}"
            if st.session_state.get(f"_imported_{state_key}") != marker:
                try:
                    new_df = pd.read_excel(uploaded)
                    st.session_state[state_key] = new_df
                    st.session_state[f"_imported_{state_key}"] = marker
                    st.success(f"Đã nhập {len(new_df)} dòng từ Excel vào mục '{label}'.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Không đọc được file Excel: {e}")


def gio_tiet_label(khoi, tiet: int, grade_times_df: pd.DataFrame) -> str:
    """Trả về '07:15–08:00' nếu khối đó có khai báo giờ riêng cho tiết này,
    ngược lại trả về chuỗi rỗng (dùng nhãn 'Tiết N' mặc định)."""
    if grade_times_df is None or grade_times_df.empty:
        return ""
    try:
        match = grade_times_df[
            (pd.to_numeric(grade_times_df["Khối"], errors="coerce") == khoi)
            & (pd.to_numeric(grade_times_df["Tiết"], errors="coerce") == tiet)
        ]
    except Exception:
        return ""
    if match.empty:
        return ""
    row = match.iloc[0]
    bd = str(row.get("Giờ bắt đầu") or "").strip()
    kt = str(row.get("Giờ kết thúc") or "").strip()
    if not bd or bd.lower() == "nan":
        return ""
    return f"{bd}–{kt}" if kt and kt.lower() != "nan" else bd


def period_label(khoi, tiet: int, grade_times_df: pd.DataFrame) -> str:
    gio = gio_tiet_label(khoi, tiet, grade_times_df)
    return f"Tiết {tiet} ({gio})" if gio else f"Tiết {tiet}"


def ve_so_do_cho_ngoi_html(hang_ghe: list[list]) -> str:
    """hang_ghe: list các hàng ghế, mỗi hàng là list ô (dict hs hoặc None).
    Trả về chuỗi HTML vẽ sơ đồ lớp học — bảng/bục giảng ở trên cùng, các
    hàng bàn xếp dần xuống dưới."""
    hang_html = []
    for hang in hang_ghe:
        o_html = []
        for o in hang:
            if o is None:
                o_html.append('<div class="seat empty"></div>')
            else:
                o_html.append(
                    f'<div class="seat filled">'
                    f'<div class="seat-sbd">{o["sbd"]}</div>'
                    f'<div class="seat-name">{o["ho_ten"]}</div>'
                    f'<div class="seat-class">{o.get("lop", "")}</div>'
                    f'</div>'
                )
        hang_html.append(f'<div class="seat-row">{"".join(o_html)}</div>')
    return (
        '<div class="seating-chart">'
        '<div class="board-label">BẢNG / BỤC GIẢNG</div>'
        + "".join(hang_html) +
        '</div>'
    )


def ngay_dau_tuan_mac_dinh() -> date:
    """Thứ 2 của tuần hiện tại (hoặc hôm nay nếu hôm nay là Thứ 2)."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def nhan_ngay_thuc_te(d: int, ngay_thu2: date) -> str:
    """VD d=1 (Thứ 2), ngay_thu2=09/09 -> 'Thứ 2 (09/09)'."""
    ten = DAY_NAMES.get(d, f"Ngày {d}")
    thuc_te = ngay_thu2 + timedelta(days=d - 1)
    return f"{ten} ({thuc_te.strftime('%d/%m')})"


def buoi_cua_tiet(p: int, config) -> str:
    if p in config.morning_periods:
        return "morning"
    if p in config.afternoon_periods:
        return "afternoon"
    return "other"


def thu_tu_tiet_co_ngan_buoi(config) -> list:
    """Trả về danh sách các 'dòng' để hiển thị: số tiết (int) hoặc chuỗi
    nhãn phân cách buổi (str) chèn giữa buổi sáng và buổi chiều."""
    periods = list(range(1, config.periods_per_day + 1))
    morning = [p for p in periods if buoi_cua_tiet(p, config) == "morning"]
    afternoon = [p for p in periods if buoi_cua_tiet(p, config) == "afternoon"]
    other = [p for p in periods if buoi_cua_tiet(p, config) == "other"]
    rows = []
    if morning:
        rows.append("☀️ BUỔI SÁNG")
        rows.extend(morning)
    if afternoon:
        rows.append("🌙 BUỔI CHIỀU")
        rows.extend(afternoon)
    if other:
        rows.extend(other)
    return rows


# ---------------------------------------------------------------------
# Dữ liệu mẫu ban đầu (dạng bảng thân thiện) để người dùng có ví dụ sẵn
# ---------------------------------------------------------------------
SAMPLE_DEPARTMENTS = pd.DataFrame([
    {"Tên tổ": "Tổ Toán"},
    {"Tên tổ": "Tổ Văn"},
    {"Tên tổ": "Tổ Ngoại ngữ"},
])

SAMPLE_TEACHERS = pd.DataFrame([
    {"Tên giáo viên": "Cô Lan (Toán)", "Tổ chuyên môn": "Tổ Toán"},
    {"Tên giáo viên": "Thầy Minh (Toán)", "Tổ chuyên môn": "Tổ Toán"},
    {"Tên giáo viên": "Cô Hoa (Văn - dạy toàn trường)", "Tổ chuyên môn": "Tổ Văn"},
    {"Tên giáo viên": "Thầy Nam (Tiếng Anh)", "Tổ chuyên môn": "Tổ Ngoại ngữ"},
    {"Tên giáo viên": "Cô Mai (Tiếng Anh + CLB Debate)", "Tổ chuyên môn": "Tổ Ngoại ngữ"},
    {"Tên giáo viên": "Thầy Đức (Tin học)", "Tổ chuyên môn": ""},
    {"Tên giáo viên": "Mr. John (GVNN)", "Tổ chuyên môn": "Tổ Ngoại ngữ"},
    {"Tên giáo viên": "Cô Thu (GVTG - Kỹ năng sống)", "Tổ chuyên môn": ""},
    {"Tên giáo viên": "Thầy Hùng (trợ giảng Toán)", "Tổ chuyên môn": "Tổ Toán"},
])

SAMPLE_CLASSES = pd.DataFrame([
    {"Tên lớp": "10A1", "Khối": 10, "Nhóm thứ tự": 1},
    {"Tên lớp": "11A1", "Khối": 11, "Nhóm thứ tự": 1},
    {"Tên lớp": "6 ESL", "Khối": 6, "Nhóm thứ tự": 1},
    {"Tên lớp": "12A1", "Khối": 12, "Nhóm thứ tự": 2},
    {"Tên lớp": "6A1", "Khối": 6, "Nhóm thứ tự": 3},
    {"Tên lớp": "7A1", "Khối": 7, "Nhóm thứ tự": 3},
])

SAMPLE_ROOMS = pd.DataFrame([
    {"Tên phòng": "Phòng máy 1", "Loại phòng": "computer_lab", "Số phòng cùng loại": 1},
])

SAMPLE_ACTIVITIES = pd.DataFrame([
    {"Tên hoạt động": "Toán 10A1", "Môn": "toan", "Số tiết/tuần": 3, "Lớp": "10A1",
     "GV chính": "Cô Lan (Toán)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Toán 11A1", "Môn": "toan", "Số tiết/tuần": 3, "Lớp": "11A1",
     "GV chính": "Thầy Minh (Toán)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Văn 10A1", "Môn": "van", "Số tiết/tuần": 4, "Lớp": "10A1",
     "GV chính": "Cô Hoa (Văn - dạy toàn trường)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Văn 11A1", "Môn": "van", "Số tiết/tuần": 4, "Lớp": "11A1",
     "GV chính": "Cô Hoa (Văn - dạy toàn trường)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Văn 6ESL", "Môn": "van", "Số tiết/tuần": 4, "Lớp": "6 ESL",
     "GV chính": "Cô Hoa (Văn - dạy toàn trường)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Văn 12A1", "Môn": "van", "Số tiết/tuần": 4, "Lớp": "12A1",
     "GV chính": "Cô Hoa (Văn - dạy toàn trường)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Văn 6A1", "Môn": "van", "Số tiết/tuần": 4, "Lớp": "6A1",
     "GV chính": "Cô Hoa (Văn - dạy toàn trường)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Toán 6A1 (đồng giảng)", "Môn": "toan", "Số tiết/tuần": 3, "Lớp": "6A1",
     "GV chính": "Cô Lan (Toán)", "GV phụ (đồng giảng)": "Thầy Hùng (trợ giảng Toán)",
     "Loại phòng cần": "", "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "CLB Thể thao", "Môn": "clb", "Số tiết/tuần": 1, "Lớp": "10A1,11A1",
     "GV chính": "Thầy Minh (Toán)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "clb_khoi_10_11", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "CLB Debate", "Môn": "clb", "Số tiết/tuần": 1, "Lớp": "10A1,11A1",
     "GV chính": "Cô Mai (Tiếng Anh + CLB Debate)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "clb_khoi_10_11", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Tiếng Anh với GVNN (10A1)", "Môn": "tieng_anh", "Số tiết/tuần": 1, "Lớp": "10A1",
     "GV chính": "Mr. John (GVNN)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": "2:2"},
    {"Tên hoạt động": "Kỹ năng sống (11A1)", "Môn": "ky_nang_song", "Số tiết/tuần": 1, "Lớp": "11A1",
     "GV chính": "Cô Thu (GVTG - Kỹ năng sống)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": "4:4"},
    {"Tên hoạt động": "Tin học 10A1", "Môn": "tin_hoc", "Số tiết/tuần": 2, "Lớp": "10A1",
     "GV chính": "Thầy Đức (Tin học)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "computer_lab",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Tin học 11A1", "Môn": "tin_hoc", "Số tiết/tuần": 2, "Lớp": "11A1",
     "GV chính": "Thầy Đức (Tin học)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "computer_lab",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Tiếng Anh 6A1", "Môn": "tieng_anh", "Số tiết/tuần": 3, "Lớp": "6A1",
     "GV chính": "Thầy Nam (Tiếng Anh)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Tiếng Anh 7A1", "Môn": "tieng_anh", "Số tiết/tuần": 3, "Lớp": "7A1",
     "GV chính": "Thầy Nam (Tiếng Anh)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
    {"Tên hoạt động": "Tiếng Anh 12A1", "Môn": "tieng_anh", "Số tiết/tuần": 3, "Lớp": "12A1",
     "GV chính": "Cô Mai (Tiếng Anh + CLB Debate)", "GV phụ (đồng giảng)": "", "Loại phòng cần": "",
     "Mã đồng bộ (CLB/tự chọn)": "", "Cố định trước (Thứ:Tiết,...)": ""},
])

SAMPLE_GRADE_TIMES = pd.DataFrame([
    {"Khối": 6, "Tiết": 1, "Giờ bắt đầu": "07:15", "Giờ kết thúc": "08:00"},
    {"Khối": 6, "Tiết": 2, "Giờ bắt đầu": "08:05", "Giờ kết thúc": "08:50"},
    {"Khối": 7, "Tiết": 1, "Giờ bắt đầu": "07:30", "Giờ kết thúc": "08:15"},
    {"Khối": 7, "Tiết": 2, "Giờ bắt đầu": "08:20", "Giờ kết thúc": "09:05"},
])

SAMPLE_GRADE_DAY_PERIODS = pd.DataFrame([
    {"Khối": 6, "Thứ": "Thứ 2", "Số tiết": 4},
    {"Khối": 6, "Thứ": "Thứ 3", "Số tiết": 5},
    {"Khối": 6, "Thứ": "Thứ 4", "Số tiết": 4},
    {"Khối": 6, "Thứ": "Thứ 5", "Số tiết": 5},
    {"Khối": 6, "Thứ": "Thứ 6", "Số tiết": 4},
    {"Khối": 6, "Thứ": "Thứ 7", "Số tiết": 3},
    {"Khối": 10, "Thứ": "Thứ 2", "Số tiết": 5},
    {"Khối": 10, "Thứ": "Thứ 7", "Số tiết": 4},
])

SAMPLE_EXAM_STUDENTS = pd.DataFrame([
    {"Mã HS (không bắt buộc)": "", "Họ và tên": "Nguyễn Văn An", "Lớp": "10A1"},
    {"Mã HS (không bắt buộc)": "", "Họ và tên": "Lê Thị Bình", "Lớp": "10A1"},
    {"Mã HS (không bắt buộc)": "", "Họ và tên": "Trần Văn Cường", "Lớp": "10A1"},
    {"Mã HS (không bắt buộc)": "HS2025004", "Họ và tên": "Phạm Thị Dung", "Lớp": "11A1"},
    {"Mã HS (không bắt buộc)": "", "Họ và tên": "Hoàng Văn Em", "Lớp": "11A1"},
    {"Mã HS (không bắt buộc)": "", "Họ và tên": "Vũ Thị Phương", "Lớp": "11A1"},
])

SAMPLE_EXAM_ROOMS = pd.DataFrame([
    {"Tên phòng": "P101", "Sức chứa": 24, "Số cột bàn": 4},
    {"Tên phòng": "P102", "Sức chứa": 24, "Số cột bàn": 4},
    {"Tên phòng": "P103", "Sức chứa": 24, "Số cột bàn": 4},
])

SAMPLE_EXAM_SUBJECTS = pd.DataFrame([
    {"Môn thi": "Toán", "Lớp áp dụng": "10A1,11A1", "Ngày thi": "15/09/2026", "Ca thi": "Sáng",
     "Chế độ xếp": "Trộn theo khối (xáo giữa các lớp)"},
    {"Môn thi": "Ngữ văn", "Lớp áp dụng": "11A1", "Ngày thi": "15/09/2026", "Ca thi": "Chiều",
     "Chế độ xếp": "Theo lớp (giữ nguyên lớp)"},
])

DEFAULTS = dict(
    departments=SAMPLE_DEPARTMENTS, teachers=SAMPLE_TEACHERS, classes=SAMPLE_CLASSES,
    rooms=SAMPLE_ROOMS, activities=SAMPLE_ACTIVITIES, grade_times=SAMPLE_GRADE_TIMES,
    grade_day_periods=SAMPLE_GRADE_DAY_PERIODS,
    exam_students=SAMPLE_EXAM_STUDENTS, exam_rooms=SAMPLE_EXAM_ROOMS,
    exam_subjects=SAMPLE_EXAM_SUBJECTS,
    free_depts=["Tổ Ngoại ngữ"],
)

DEFAULT_CONSTRAINT_TOGGLES = dict(
    ct_period_spread=True,
    ct_room_capacity=True,
    ct_order_group=True,
    ct_dept_free_session=True,
    ct_no_gap=True,
)

for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default.copy() if hasattr(default, "copy") else default

for key, default in DEFAULT_CONSTRAINT_TOGGLES.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "result" not in st.session_state:
    st.session_state.result = None
if "solutions_history" not in st.session_state:
    st.session_state.solutions_history = []  # list[dict]: result/classes/config/signature
if "selected_solution_idx" not in st.session_state:
    st.session_state.selected_solution_idx = 0
if "tuan_bat_dau" not in st.session_state:
    st.session_state.tuan_bat_dau = ngay_dau_tuan_mac_dinh()
if "exam_results" not in st.session_state:
    st.session_state.exam_results = {}  # {ten_mon: {"rooms": [...], "thieu": [...], "ngay":..., "ca":...}}

# =======================================================================
# GIÁ TRỊ DÙNG CHUNG NHIỀU MODULE — đọc từ session_state với giá trị mặc
# định, để module nào cũng dùng được kể cả khi chưa mở tab "Cấu hình
# chung" trong phiên làm việc này (do giờ có sidebar chọn module, không
# phải lúc nào tab đó cũng được render).
# =======================================================================
if "substitutions" not in st.session_state:
    st.session_state.substitutions = {}  # {(ngay_thu, tiet, lop_key): {...}}

num_days = st.session_state.get("cfg_num_days", 6)
periods_per_day = st.session_state.get("cfg_periods_per_day", 5)
morning_count = st.session_state.get("cfg_morning_count", 3)
max_seconds = st.session_state.get("cfg_max_seconds", 30)
school_name = st.session_state.get("cfg_school_name", "")

dept_names = [d for d in st.session_state.departments["Tên tổ"].dropna().tolist() if str(d).strip()]
teacher_names = [t for t in st.session_state.teachers["Tên giáo viên"].dropna().tolist() if str(t).strip()]
class_names = [c for c in st.session_state.classes["Tên lớp"].dropna().tolist() if str(c).strip()]
room_types = [r for r in st.session_state.rooms["Loại phòng"].dropna().tolist() if str(r).strip()]
class_to_grade = {
    row["Tên lớp"]: row["Khối"]
    for _, row in st.session_state.classes.dropna(subset=["Tên lớp", "Khối"]).iterrows()
}
teacher_to_dept = {
    row["Tên giáo viên"]: (row.get("Tổ chuyên môn") or "")
    for _, row in st.session_state.teachers.dropna(subset=["Tên giáo viên"]).iterrows()
}

# =======================================================================
# SIDEBAR — thanh dọc chuyển giữa 3 module lớn
# =======================================================================
with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">🏫 Hệ thống Quản lý<br/>Trường học</div>',
        unsafe_allow_html=True,
    )
    module = st.radio(
        "CHỌN MODULE",
        [
            "📅 Xếp Thời Khoá Biểu",
            "🪑 Xếp Phòng Thi",
            "🔄 Phân Công Dạy Thay",
        ],
        key="active_module",
        label_visibility="visible",
    )
    st.divider()
    if st.button("↺ Khôi phục dữ liệu mẫu (toàn bộ)", use_container_width=True):
        for key, default in DEFAULTS.items():
            st.session_state[key] = default.copy() if hasattr(default, "copy") else default
        for key, default in DEFAULT_CONSTRAINT_TOGGLES.items():
            st.session_state[key] = default
        st.session_state.result = None
        st.session_state.solutions_history = []
        st.session_state.selected_solution_idx = 0
        st.session_state.exam_results = {}
        st.session_state.substitutions = {}
        st.rerun()
    st.caption(
        f"📆 TKB áp dụng từ: **{st.session_state.tuan_bat_dau.strftime('%d/%m/%Y')}**"
    )
    st.caption("Đổi ngày này ở tab ⚙️ Cấu hình chung.")

if module == "📅 Xếp Thời Khoá Biểu":
    tab_cfg, tab_data, tab_activities, tab_constraints, tab_result = st.tabs([
        "⚙️ Cấu hình chung",
        "🏢 Tổ / GV / Lớp / Phòng",
        "📚 Môn học & phân công",
        "⚖️ Ràng buộc & Xếp lịch",
        "📅 Kết quả",
    ])


    # ---------------------------------------------------------------------
    # TAB 1 — Cấu hình chung + giờ học theo khối
    # ---------------------------------------------------------------------
    with tab_cfg:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header("1", "Cấu hình lịch học")
        c1, c2, c3 = st.columns(3)
        with c1:
            num_days = st.selectbox("Số ngày học/tuần", [5, 6], index=1, key="cfg_num_days")
        with c2:
            periods_per_day = st.number_input(
                "Số tiết/ngày TỐI ĐA", min_value=1, max_value=15, value=5,
                help="Số tiết của ngày học DÀI NHẤT trong tuần (tính trên toàn trường). "
                     "Nếu 1 số khối có ít tiết hơn vào 1 số ngày, khai báo ở mục '3. Số tiết mỗi "
                     "ngày theo từng khối' bên dưới — không cần đổi số này xuống thấp.",
                key="cfg_periods_per_day",
            )
        with c3:
            morning_count = st.number_input(
                "Số tiết buổi sáng (còn lại là buổi chiều)", min_value=1,
                max_value=int(periods_per_day), value=min(3, int(periods_per_day)),
                key="cfg_morning_count",
            )
        max_seconds = st.slider(
            "Thời gian tối đa cho solver tìm lời giải (giây)", 5, 120, 30, key="cfg_max_seconds"
        )
        school_name = st.text_input(
            "Tên trường (hiển thị trên PDF xuất ra, không bắt buộc)", value="",
            key="cfg_school_name",
        )
        st.session_state.tuan_bat_dau = st.date_input(
            "📆 Ngày bắt đầu áp dụng TKB (Thứ 2 của tuần đầu tiên áp dụng)",
            value=st.session_state.tuan_bat_dau,
            help="Ngày này vừa là mốc TKB bắt đầu có hiệu lực, vừa dùng để hiện ngày thực tế "
                 "(VD 'Thứ 2 (08/09)') trên thời khoá biểu, phòng thi và phân công dạy thay.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "2", "Giờ học theo từng khối (không bắt buộc)",
            "Mỗi khối có thể có giờ vào học khác nhau, VD Khối 6 học Tiết 1 lúc 07:15–08:00, "
            "Khối 7 học Tiết 1 lúc 07:30–08:15. Đây CHỈ là nhãn hiển thị trên màn hình/PDF/Excel — "
            "việc xếp lịch vẫn dùng chung số Tiết 1..N cho toàn trường để tránh trùng giờ GV dạy "
            "nhiều khối. Khối nào không khai báo ở đây sẽ hiện nhãn mặc định 'Tiết N'.",
        )
        excel_io_row("grade_times", "Gio_hoc_theo_khoi")
        st.session_state.grade_times = st.data_editor(
            st.session_state.grade_times, num_rows="dynamic", use_container_width=True,
            key="editor_grade_times",
            column_config={
                "Khối": st.column_config.NumberColumn(min_value=1, max_value=12, step=1, required=True),
                "Tiết": st.column_config.NumberColumn(min_value=1, max_value=15, step=1, required=True),
                "Giờ bắt đầu": st.column_config.TextColumn(help="Định dạng HH:MM, VD 07:15"),
                "Giờ kết thúc": st.column_config.TextColumn(help="Định dạng HH:MM, VD 08:00"),
            },
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "3", "Số tiết mỗi ngày theo từng khối (không bắt buộc)",
            "Khai báo nếu các khối có SỐ TIẾT KHÁC NHAU tuỳ ngày, VD Khối 6 Thứ 2 chỉ học 4 tiết "
            "nhưng Thứ 3 học 5 tiết. Khối/ngày nào KHÔNG khai báo ở đây sẽ mặc định dùng đủ "
            "'Số tiết/ngày tối đa' ở mục 1. Đây là ràng buộc THẬT (không phải chỉ để hiển thị) — "
            "hệ thống sẽ không xếp giờ học nào cho khối đó vượt quá số tiết khai báo trong ngày đó.",
        )
        excel_io_row("grade_day_periods", "So_tiet_theo_khoi_ngay")
        st.session_state.grade_day_periods = st.data_editor(
            st.session_state.grade_day_periods, num_rows="dynamic", use_container_width=True,
            key="editor_grade_day_periods",
            column_config={
                "Khối": st.column_config.NumberColumn(min_value=1, max_value=12, step=1, required=True),
                "Thứ": st.column_config.SelectboxColumn(
                    options=["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"],
                    required=True,
                ),
                "Số tiết": st.column_config.NumberColumn(
                    min_value=0, max_value=15, step=1, required=True,
                    help="Để 0 nếu khối đó KHÔNG học ngày này (VD trường học Thứ 7 nhưng khối 6 nghỉ).",
                ),
            },
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------------------
    # TAB 2 — Tổ chuyên môn / Giáo viên / Lớp học / Phòng đặc biệt
    # ---------------------------------------------------------------------
    with tab_data:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header("1", "Tổ chuyên môn")
        excel_io_row("departments", "To_chuyen_mon")
        st.session_state.departments = st.data_editor(
            st.session_state.departments, num_rows="dynamic", use_container_width=True,
            key="editor_departments",
            column_config={"Tên tổ": st.column_config.TextColumn(required=True)},
        )
        st.markdown('</div>', unsafe_allow_html=True)
        dept_names = [d for d in st.session_state.departments["Tên tổ"].dropna().tolist() if d.strip()]

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header("2", "Giáo viên")
        excel_io_row("teachers", "Giao_vien")
        st.session_state.teachers = st.data_editor(
            st.session_state.teachers, num_rows="dynamic", use_container_width=True,
            key="editor_teachers",
            column_config={
                "Tên giáo viên": st.column_config.TextColumn(required=True),
                "Tổ chuyên môn": st.column_config.SelectboxColumn(options=[""] + dept_names),
            },
        )
        st.markdown('</div>', unsafe_allow_html=True)
        teacher_names = [t for t in st.session_state.teachers["Tên giáo viên"].dropna().tolist() if t.strip()]

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "3", "Lớp học",
            "<b>Nhóm thứ tự</b>: dùng cho ràng buộc “lệch giờ khi 1 GV dạy toàn trường” — các lớp cùng "
            "nhóm sẽ được GV đó dạy liền nhau, nhóm số nhỏ dạy trước. VD: Nhóm 1 = K10/K11/6-ESL, "
            "Nhóm 2 = K12, Nhóm 3 = K6-9. Nếu trường không có ràng buộc này, để tất cả cùng 1 nhóm.",
        )
        excel_io_row("classes", "Lop_hoc")
        st.session_state.classes = st.data_editor(
            st.session_state.classes, num_rows="dynamic", use_container_width=True,
            key="editor_classes",
            column_config={
                "Tên lớp": st.column_config.TextColumn(required=True),
                "Khối": st.column_config.NumberColumn(min_value=1, max_value=12, step=1, required=True),
                "Nhóm thứ tự": st.column_config.NumberColumn(min_value=0, max_value=9, step=1, required=True),
            },
        )
        st.markdown('</div>', unsafe_allow_html=True)
        class_names = [c for c in st.session_state.classes["Tên lớp"].dropna().tolist() if c.strip()]

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "4", "Phòng đặc biệt (không bắt buộc)",
            "Chỉ khai báo nếu có phòng bị giới hạn số lượng (VD chỉ có 1 phòng máy → không thể 2 lớp "
            "học Tin cùng lúc). Bỏ trống nếu không cần.",
        )
        excel_io_row("rooms", "Phong_dac_biet")
        st.session_state.rooms = st.data_editor(
            st.session_state.rooms, num_rows="dynamic", use_container_width=True,
            key="editor_rooms",
            column_config={
                "Tên phòng": st.column_config.TextColumn(),
                "Loại phòng": st.column_config.TextColumn(help="Mã loại phòng, VD: computer_lab"),
                "Số phòng cùng loại": st.column_config.NumberColumn(min_value=1, step=1),
            },
        )
        st.markdown('</div>', unsafe_allow_html=True)
        room_types = [r for r in st.session_state.rooms["Loại phòng"].dropna().tolist() if r.strip()]

    # ---------------------------------------------------------------------
    # TAB 3 — Môn học / phân công giảng dạy (Activities)
    # ---------------------------------------------------------------------
    with tab_activities:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "5", "Môn học & phân công giảng dạy",
            "Mỗi dòng = 1 khối cần xếp lịch. <b>Lớp</b>: nhiều lớp cách nhau dấu phẩy cho môn tự chọn "
            "liên lớp. <b>GV phụ</b>: điền nếu đồng giảng. <b>Mã đồng bộ</b>: các dòng cùng mã sẽ luôn "
            "học cùng giờ. <b>Cố định trước</b>: dạng <code>Thứ:Tiết</code>, VD <code>2:2,4:4</code>.",
        )
        excel_io_row("activities", "Mon_hoc_phan_cong")
        st.session_state.activities = st.data_editor(
            st.session_state.activities, num_rows="dynamic", use_container_width=True,
            key="editor_activities",
            column_config={
                "Tên hoạt động": st.column_config.TextColumn(required=True),
                "Môn": st.column_config.TextColumn(help="Mã môn học, VD: toan, van, tieng_anh"),
                "Số tiết/tuần": st.column_config.NumberColumn(min_value=1, max_value=15, step=1, required=True),
                "Lớp": st.column_config.TextColumn(
                    required=True, help="1 lớp, hoặc nhiều lớp cách nhau dấu phẩy cho môn tự chọn liên lớp"
                ),
                "GV chính": st.column_config.SelectboxColumn(options=teacher_names, required=True),
                "GV phụ (đồng giảng)": st.column_config.SelectboxColumn(options=[""] + teacher_names),
                "Loại phòng cần": st.column_config.SelectboxColumn(options=[""] + room_types),
                "Mã đồng bộ (CLB/tự chọn)": st.column_config.TextColumn(),
                "Cố định trước (Thứ:Tiết,...)": st.column_config.TextColumn(),
            },
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------------------
    # TAB 4 — Ràng buộc + nút xếp lịch
    # ---------------------------------------------------------------------
    with tab_constraints:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "6", "Ràng buộc áp dụng khi xếp lịch",
            "Các ràng buộc <b>cốt lõi</b> (không trùng giờ GV/lớp, đồng bộ tiết chung, đủ số tiết/tuần, "
            "giờ cố định trước) luôn bật vì tắt đi sẽ tạo lịch chồng giờ. Các ràng buộc <b>tuỳ chọn</b> "
            "bên dưới có thể tắt nếu trường không cần.",
        )

        lock_c1, lock_c2 = st.columns(2)
        with lock_c1:
            st.markdown(
                '<div class="constraint-row constraint-locked">🔒 <b>Không trùng giờ Giáo viên</b> '
                '— luôn bật</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="constraint-row constraint-locked">🔒 <b>Không trùng giờ Lớp học</b> '
                '— luôn bật</div>', unsafe_allow_html=True)
        with lock_c2:
            st.markdown(
                '<div class="constraint-row constraint-locked">🔒 <b>Đồng bộ tiết chung (Mã đồng bộ)</b> '
                '— luôn bật</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="constraint-row constraint-locked">🔒 <b>Giờ cố định trước / đồng giảng</b> '
                '— luôn bật</div>', unsafe_allow_html=True)

        opt_c1, opt_c2 = st.columns(2)
        with opt_c1:
            st.markdown('<div class="constraint-row">', unsafe_allow_html=True)
            st.session_state.ct_period_spread = st.checkbox(
                "Không dồn tiết trong ngày (3-4 tiết/tuần ≤2 tiết/ngày; ≥5 tiết/tuần ≤3 tiết/ngày)",
                value=st.session_state.ct_period_spread,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="constraint-row">', unsafe_allow_html=True)
            st.session_state.ct_order_group = st.checkbox(
                "Lệch giờ giữa các khối khi 1 GV dạy toàn trường (theo Nhóm thứ tự)",
                value=st.session_state.ct_order_group,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="constraint-row">', unsafe_allow_html=True)
            st.session_state.ct_no_gap = st.checkbox(
                "Không ngắt quãng: 2 tiết cùng môn trong 1 ngày phải liền kề nhau "
                "(không xếp kiểu Tiết A → môn khác → lại Tiết A)",
                value=st.session_state.ct_no_gap,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with opt_c2:
            st.markdown('<div class="constraint-row">', unsafe_allow_html=True)
            st.session_state.ct_room_capacity = st.checkbox(
                "Giới hạn phòng đặc biệt (VD chỉ 1 phòng máy → không xếp 2 lớp Tin cùng lúc)",
                value=st.session_state.ct_room_capacity,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="constraint-row">', unsafe_allow_html=True)
            st.session_state.ct_dept_free_session = st.checkbox(
                "Buổi trống chung cho tổ chuyên môn (chọn tổ ở bên dưới)",
                value=st.session_state.ct_dept_free_session,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.session_state.free_depts = st.multiselect(
            "Tổ nào cần 1 buổi trống chung/tuần (toàn bộ GV của tổ đều rảnh)?",
            options=dept_names, default=[d for d in st.session_state.free_depts if d in dept_names],
            disabled=not st.session_state.ct_dept_free_session,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        gen_c1, gen_c2 = st.columns([2, 1])
        with gen_c1:
            generate = st.button("🗓️  Xếp thời khoá biểu", type="primary", use_container_width=True)
        with gen_c2:
            regenerate = st.button(
                "🔀 Xếp phương án khác",
                use_container_width=True,
                disabled=not st.session_state.solutions_history,
                help="Chỉ dùng được sau khi đã xếp thành công ít nhất 1 lần. Giữ nguyên toàn bộ dữ "
                     "liệu/ràng buộc, chỉ tìm 1 cách sắp xếp KHÁC với các phương án trước đó.",
            )


    def build_input_from_tables():
        errors = []

        dept_df = st.session_state.departments.dropna(subset=["Tên tổ"])
        dept_df = dept_df[dept_df["Tên tổ"].str.strip() != ""]
        dept_ids = dedupe_ids([slugify(n, "to_") for n in dept_df["Tên tổ"]])
        dept_name_to_id = dict(zip(dept_df["Tên tổ"], dept_ids))
        departments = [Department(id=i, name=n) for i, n in zip(dept_ids, dept_df["Tên tổ"])]

        teacher_df = st.session_state.teachers.dropna(subset=["Tên giáo viên"])
        teacher_df = teacher_df[teacher_df["Tên giáo viên"].str.strip() != ""]
        teacher_ids = dedupe_ids([slugify(n, "gv_") for n in teacher_df["Tên giáo viên"]])
        teacher_name_to_id = dict(zip(teacher_df["Tên giáo viên"], teacher_ids))
        teachers = [
            Teacher(id=tid, name=name, department_id=dept_name_to_id.get(dept) or None)
            for tid, name, dept in zip(teacher_ids, teacher_df["Tên giáo viên"], teacher_df["Tổ chuyên môn"])
        ]

        class_df = st.session_state.classes.dropna(subset=["Tên lớp"])
        class_df = class_df[class_df["Tên lớp"].str.strip() != ""]
        class_ids = dedupe_ids([slugify(n, "lop_") for n in class_df["Tên lớp"]])
        class_name_to_id = dict(zip(class_df["Tên lớp"], class_ids))
        classes = [
            SchoolClass(id=cid, name=name, grade=int(grade), order_group=int(og))
            for cid, name, grade, og in zip(
                class_ids, class_df["Tên lớp"], class_df["Khối"], class_df["Nhóm thứ tự"]
            )
        ]

        room_df = st.session_state.rooms.dropna(subset=["Loại phòng"])
        room_df = room_df[room_df["Loại phòng"].astype(str).str.strip() != ""]
        rooms = [
            Room(id=slugify(rt, "room_"), name=(name or rt), room_type=rt, capacity=int(cap) if pd.notna(cap) else 1)
            for name, rt, cap in zip(room_df.get("Tên phòng", []), room_df["Loại phòng"], room_df["Số phòng cùng loại"])
        ]

        activities = []
        act_df = st.session_state.activities.dropna(subset=["Tên hoạt động"])
        act_df = act_df[act_df["Tên hoạt động"].str.strip() != ""]
        act_ids = dedupe_ids([slugify(n, "act_") for n in act_df["Tên hoạt động"]])
        for act_id, (_, row) in zip(act_ids, act_df.iterrows()):
            class_names_raw = [c.strip() for c in str(row["Lớp"]).split(",") if c.strip()]
            teacher_main = row["GV chính"]
            missing_classes = [c for c in class_names_raw if c not in class_name_to_id]
            if missing_classes:
                errors.append(
                    f"Hoạt động '{row['Tên hoạt động']}': lớp {missing_classes} chưa khai báo ở "
                    f"bảng Lớp học."
                )
                continue
            if not class_names_raw:
                errors.append(f"Hoạt động '{row['Tên hoạt động']}': chưa điền cột Lớp.")
                continue
            if teacher_main not in teacher_name_to_id:
                errors.append(f"Hoạt động '{row['Tên hoạt động']}': GV '{teacher_main}' chưa khai báo ở bảng Giáo viên.")
                continue
            blocked_class_ids = [class_name_to_id[c] for c in class_names_raw]
            teacher_ids_for_act = [teacher_name_to_id[teacher_main]]
            teacher_2 = row.get("GV phụ (đồng giảng)") or ""
            if isinstance(teacher_2, str) and teacher_2.strip():
                if teacher_2 not in teacher_name_to_id:
                    errors.append(f"Hoạt động '{row['Tên hoạt động']}': GV phụ '{teacher_2}' chưa khai báo.")
                    continue
                teacher_ids_for_act.append(teacher_name_to_id[teacher_2])

            room_type = None if pd.isna(row.get("Loại phòng cần")) else str(row.get("Loại phòng cần")).strip() or None
            sync_key = (row.get("Mã đồng bộ (CLB/tự chọn)") or "").strip() or None

            fixed_slots = []
            raw_fixed = (row.get("Cố định trước (Thứ:Tiết,...)") or "").strip()
            if raw_fixed:
                try:
                    for pair in raw_fixed.split(","):
                        d_str, p_str = pair.strip().split(":")
                        fixed_slots.append(Slot(day=int(d_str), period=int(p_str)))
                except Exception:
                    errors.append(
                        f"Hoạt động '{row['Tên hoạt động']}': cột 'Cố định trước' sai định dạng "
                        f"'{raw_fixed}' — cần dạng Thứ:Tiết, VD 2:2,4:4"
                    )
                    continue

            activities.append(Activity(
                id=act_id, name=row["Tên hoạt động"], subject_id=(row.get("Môn") or act_id),
                periods_per_week=int(row["Số tiết/tuần"]),
                blocked_classes=blocked_class_ids,
                teachers=teacher_ids_for_act,
                room_type=room_type, sync_key=sync_key, fixed_slots=fixed_slots,
            ))

        free_dept_ids = (
            [dept_name_to_id[d] for d in st.session_state.free_depts if d in dept_name_to_id]
            if st.session_state.ct_dept_free_session else []
        )

        name_to_day = {v: k for k, v in DAY_NAMES.items()}
        grade_day_periods = []
        gdp_df = st.session_state.grade_day_periods.dropna(subset=["Khối", "Thứ", "Số tiết"])
        for _, row in gdp_df.iterrows():
            thu_str = str(row["Thứ"]).strip()
            if thu_str not in name_to_day:
                errors.append(f"Mục 'Số tiết mỗi ngày theo khối': giá trị Thứ '{thu_str}' không hợp lệ.")
                continue
            d = name_to_day[thu_str]
            if d > num_days:
                continue  # ngày này không nằm trong số ngày học/tuần đã chọn -> bỏ qua
            so_tiet = int(row["Số tiết"])
            if so_tiet > int(periods_per_day):
                errors.append(
                    f"Mục 'Số tiết mỗi ngày theo khối': Khối {int(row['Khối'])} - {thu_str} có "
                    f"{so_tiet} tiết, vượt quá 'Số tiết/ngày tối đa' ({int(periods_per_day)}) ở "
                    f"mục 1 — tăng số đó lên trước."
                )
                continue
            grade_day_periods.append(
                GradeDayCapacity(grade=int(row["Khối"]), day=d, periods_count=so_tiet)
            )

        if not classes:
            errors.append("Chưa khai báo lớp học nào.")
        if not teachers:
            errors.append("Chưa khai báo giáo viên nào.")
        if not activities:
            errors.append("Chưa khai báo hoạt động (môn học/phân công) nào.")

        if errors:
            for e in errors:
                st.error(e)
            return None

        config = ScheduleConfig(
            days=list(range(1, num_days + 1)),
            periods_per_day=int(periods_per_day),
            morning_periods=list(range(1, int(morning_count) + 1)),
            afternoon_periods=list(range(int(morning_count) + 1, int(periods_per_day) + 1)),
            max_solver_seconds=float(max_seconds),
        )

        return TimetableInput(
            config=config, departments=departments, teachers=teachers, classes=classes,
            rooms=rooms, activities=activities, departments_needing_free_session=free_dept_ids,
            grade_day_periods=grade_day_periods,
        )


    constraint_flags = {
        "period_spread": st.session_state.ct_period_spread,
        "room_capacity": st.session_state.ct_room_capacity,
        "order_group": st.session_state.ct_order_group,
        "dept_free_session": st.session_state.ct_dept_free_session,
        "no_gap": st.session_state.ct_no_gap,
    }

    if generate:
        data = build_input_from_tables()
        if data is not None:
            with st.spinner("Đang xếp lịch bằng CP-SAT..."):
                try:
                    result = solve_timetable(
                        data, enabled=constraint_flags, random_seed=random.randint(1, 10_000_000)
                    )
                    if result.status in ("INFEASIBLE", "ERROR"):
                        st.session_state.result = result
                        st.session_state.solutions_history = []
                    else:
                        st.session_state.solutions_history = [{
                            "result": result, "classes": data.classes, "config": data.config,
                        }]
                        st.session_state.selected_solution_idx = 0
                        st.session_state.result = result
                        st.session_state.result_classes = data.classes
                        st.session_state.result_config = data.config
                except SchedulerError as e:
                    st.error(f"Lỗi ràng buộc dữ liệu: {e}")
                    st.session_state.result = None
                    st.session_state.solutions_history = []

    if regenerate and st.session_state.solutions_history:
        data = build_input_from_tables()
        if data is not None:
            with st.spinner("Đang tìm phương án khác..."):
                try:
                    prev_signatures = [
                        h["result"].solution_signature for h in st.session_state.solutions_history
                    ]
                    result = solve_timetable(
                        data, enabled=constraint_flags,
                        forbid_signatures=prev_signatures,
                        random_seed=random.randint(1, 10_000_000),
                    )
                    if result.status in ("INFEASIBLE", "ERROR"):
                        st.warning(
                            "Không tìm được phương án nào khác nữa với cùng dữ liệu/ràng buộc này "
                            "(đã hết lựa chọn khả thi, hoặc solver hết thời gian). Các phương án cũ "
                            "vẫn còn nguyên, bạn có thể xem lại ở dưới."
                        )
                    else:
                        st.session_state.solutions_history.append({
                            "result": result, "classes": data.classes, "config": data.config,
                        })
                        st.session_state.selected_solution_idx = len(st.session_state.solutions_history) - 1
                        st.session_state.result = result
                        st.session_state.result_classes = data.classes
                        st.session_state.result_config = data.config
                except SchedulerError as e:
                    st.error(f"Lỗi ràng buộc dữ liệu: {e}")

    # ---------------------------------------------------------------------
    # TAB 5 — Kết quả
    # ---------------------------------------------------------------------
    with tab_result:
        result = st.session_state.result

        if result is None:
            st.info("Chưa có kết quả — sang tab \"⚖️ Ràng buộc & Xếp lịch\" rồi bấm \"🗓️ Xếp thời khoá biểu\".")
        elif result.status in ("INFEASIBLE", "ERROR"):
            st.error(result.message)
            st.info(
                "Gợi ý: kiểm tra lại xem có GV bị giao quá nhiều tiết cùng lúc, số tiết/tuần quá "
                "lớn so với số ngày/tiết có sẵn, hoặc các giờ cố định trước bị chồng nhau không. "
                "Bạn cũng có thể thử tắt bớt ràng buộc tuỳ chọn ở tab Ràng buộc rồi xếp lại."
            )
        else:
            history = st.session_state.solutions_history
            if len(history) > 1:
                options = list(range(len(history)))
                chosen = st.selectbox(
                    "📋 Chọn phương án để xem",
                    options=options,
                    index=st.session_state.selected_solution_idx,
                    format_func=lambda i: f"Phương án {i + 1}"
                    + (" (mới nhất)" if i == len(history) - 1 else ""),
                )
                st.session_state.selected_solution_idx = chosen
                entry = history[chosen]
                result = entry["result"]
                st.session_state.result_classes = entry["classes"]
                st.session_state.result_config = entry["config"]
                st.caption(
                    f"Đang xem Phương án {chosen + 1}/{len(history)}. Bấm \"🔀 Xếp phương án khác\" "
                    f"ở tab Ràng buộc để có thêm lựa chọn."
                )

            st.markdown(
                f'<div class="status-ok">✅ Trạng thái: {result.status} — {result.message}</div>',
                unsafe_allow_html=True,
            )
            st.write("")

            if result.department_free_sessions:
                with st.container(border=True):
                    st.markdown("**Buổi trống chung theo tổ:**")
                    for dept, when in result.department_free_sessions.items():
                        st.markdown(f"- {dept}: {when}")

            classes = st.session_state.result_classes
            config = st.session_state.result_config
            periods = list(range(1, config.periods_per_day + 1))
            days = config.days
            grade_times_df = st.session_state.get("grade_times")
            tuan_bat_dau = st.session_state.tuan_bat_dau

            # map teacher_id -> tên hiển thị (để hiện tên GV thay vì mã nội bộ)
            teacher_id_to_name = {
                slugify(n, "gv_"): n for n in st.session_state.teachers["Tên giáo viên"].dropna()
            }

            # nhãn "Tiết N (giờ-giờ)" riêng theo khối của từng lớp
            period_labels_by_class = {
                c.id: {p: period_label(c.grade, p, grade_times_df) for p in periods}
                for c in classes
            }

            # cột ngày dùng NGÀY THỰC TẾ theo lịch, VD "Thứ 2 (08/09)"
            day_col_labels = {d: nhan_ngay_thuc_te(d, tuan_bat_dau) for d in days}

            # thứ tự dòng hiển thị: chèn dòng ngăn "BUỔI SÁNG"/"BUỔI CHIỀU"
            hang_hien_thi = thu_tu_tiet_co_ngan_buoi(config)

            def xay_grid_cho_lop(c):
                row_labels = [
                    (item if isinstance(item, str) else period_labels_by_class[c.id][item])
                    for item in hang_hien_thi
                ]
                grid = pd.DataFrame(
                    "", index=row_labels, columns=[day_col_labels[d] for d in days],
                )
                for lesson in result.lessons:
                    if c.id in lesson.class_ids:
                        row_label = period_labels_by_class[c.id].get(lesson.period)
                        col_label = day_col_labels.get(lesson.day)
                        if row_label in grid.index and col_label in grid.columns:
                            teacher_display = ", ".join(
                                teacher_id_to_name.get(tid, tid) for tid in lesson.teacher_ids
                            )
                            grid.loc[row_label, col_label] = f"{lesson.activity_name} ({teacher_display})"
                return grid

            # ---------------- Xuất kết quả: PDF & Excel ----------------
            exp_c1, exp_c2, _ = st.columns([1, 1, 2])
            with exp_c1:
                pdf_bytes = timetable_to_pdf_bytes(
                    classes, config, result.lessons, day_col_labels, teacher_id_to_name,
                    dept_free_sessions=result.department_free_sessions,
                    school_name=school_name,
                    period_labels_by_class=period_labels_by_class,
                )
                st.download_button(
                    "📄 Xuất PDF thời khoá biểu", data=pdf_bytes,
                    file_name="thoi_khoa_bieu.pdf", mime="application/pdf",
                    type="primary", use_container_width=True,
                )
            with exp_c2:
                import io as _io
                xls_buf = _io.BytesIO()
                with pd.ExcelWriter(xls_buf, engine="openpyxl") as writer:
                    for c in classes:
                        xay_grid_cho_lop(c).to_excel(writer, sheet_name=c.name[:31])
                st.download_button(
                    "📊 Xuất Excel thời khoá biểu", data=xls_buf.getvalue(),
                    file_name="thoi_khoa_bieu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            st.write("")
            class_tabs = st.tabs([c.name for c in classes])
            for tab, c in zip(class_tabs, classes):
                with tab:
                    st.dataframe(
                        xay_grid_cho_lop(c), use_container_width=True,
                        height=(len(hang_hien_thi) + 1) * 38,
                    )

# ---------------------------------------------------------------------
# TAB 6 — Phòng thi (xếp SBD + phòng thi theo môn)
# ---------------------------------------------------------------------
elif module == "🪑 Xếp Phòng Thi":
    class_names_for_exam = [c for c in st.session_state.classes["Tên lớp"].dropna().tolist() if str(c).strip()]
    class_to_grade = {
        row["Tên lớp"]: row["Khối"]
        for _, row in st.session_state.classes.dropna(subset=["Tên lớp", "Khối"]).iterrows()
    }

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "1", "Danh sách học sinh dự thi",
        "Lớp ở đây PHẢI trùng tên với bảng \"Lớp học\" ở tab 🏢 để hệ thống biết khối tương ứng. "
        "Mã HS để trống thì hệ thống tự sinh số báo danh.",
    )
    excel_io_row("exam_students", "Danh_sach_hoc_sinh_thi")
    st.session_state.exam_students = st.data_editor(
        st.session_state.exam_students, num_rows="dynamic", use_container_width=True,
        key="editor_exam_students",
        column_config={
            "Mã HS (không bắt buộc)": st.column_config.TextColumn(),
            "Họ và tên": st.column_config.TextColumn(required=True),
            "Lớp": st.column_config.SelectboxColumn(options=class_names_for_exam, required=True),
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "2", "Danh sách phòng thi",
        "<b>Số cột bàn</b>: dùng để vẽ sơ đồ chỗ ngồi (chia học sinh vào lưới theo đúng số cột "
        "bàn thật của phòng, xếp từ hàng gần bảng xuống dần).",
    )
    excel_io_row("exam_rooms", "Danh_sach_phong_thi")
    st.session_state.exam_rooms = st.data_editor(
        st.session_state.exam_rooms, num_rows="dynamic", use_container_width=True,
        key="editor_exam_rooms",
        column_config={
            "Tên phòng": st.column_config.TextColumn(required=True),
            "Sức chứa": st.column_config.NumberColumn(min_value=1, max_value=100, step=1, required=True),
            "Số cột bàn": st.column_config.NumberColumn(
                min_value=1, max_value=12, step=1, required=True,
                help="Số cột bàn thật trong phòng, VD phòng 24 chỗ xếp 4 cột x 6 hàng thì nhập 4.",
            ),
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "3", "Môn thi & chế độ xếp phòng",
        "<b>Lớp áp dụng</b>: liệt kê đúng các lớp thi môn này, cách nhau dấu phẩy (VD "
        "<code>10A1,10A2,11CV</code>) — các lớp cùng khối vẫn có thể thi môn khác nhau (lớp "
        "chuyên, lớp chọn môn...), nên ghi rõ lớp thay vì chỉ chọn khối. <b>Chế độ xếp</b>: "
        "\"Theo lớp\" giữ nguyên từng lớp (chỉ tách khi 1 lớp đông hơn sức chứa 1 phòng); "
        "\"Trộn theo khối\" xáo học sinh từ các lớp khác nhau ngồi xen kẽ nhau trong cùng phòng "
        "(hạn chế quay cóp).",
    )
    excel_io_row("exam_subjects", "Mon_thi")
    st.session_state.exam_subjects = st.data_editor(
        st.session_state.exam_subjects, num_rows="dynamic", use_container_width=True,
        key="editor_exam_subjects",
        column_config={
            "Môn thi": st.column_config.TextColumn(required=True),
            "Lớp áp dụng": st.column_config.TextColumn(
                required=True, help="Các lớp thi môn này, cách nhau dấu phẩy. VD: 10A1,10A2,11CV",
            ),
            "Ngày thi": st.column_config.TextColumn(help="VD: 15/09/2026", required=True),
            "Ca thi": st.column_config.SelectboxColumn(options=["Sáng", "Chiều", "Tối"], required=True),
            "Chế độ xếp": st.column_config.SelectboxColumn(
                options=["Theo lớp (giữ nguyên lớp)", "Trộn theo khối (xáo giữa các lớp)"],
                required=True,
            ),
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

    xep_phong_btn = st.button("🪑 Xếp phòng thi cho tất cả môn", type="primary", use_container_width=True)

    if xep_phong_btn:
        loi_xep_phong = []
        ket_qua_moi = {}
        students_df = st.session_state.exam_students.dropna(subset=["Họ và tên", "Lớp"])
        rooms_list_all = [
            {"ten_phong": r["Tên phòng"], "suc_chua": int(r["Sức chứa"])}
            for _, r in st.session_state.exam_rooms.dropna(subset=["Tên phòng", "Sức chứa"]).iterrows()
        ]
        room_so_cot = {
            r["Tên phòng"]: int(r["Số cột bàn"]) if pd.notna(r.get("Số cột bàn")) else 4
            for _, r in st.session_state.exam_rooms.dropna(subset=["Tên phòng"]).iterrows()
        }
        if not rooms_list_all:
            loi_xep_phong.append("Chưa khai báo phòng thi nào ở mục 2.")

        subjects_df = st.session_state.exam_subjects.dropna(
            subset=["Môn thi", "Lớp áp dụng", "Ngày thi", "Ca thi", "Chế độ xếp"]
        )
        if subjects_df.empty:
            loi_xep_phong.append("Chưa khai báo môn thi nào ở mục 3.")

        for _, mon in subjects_df.iterrows():
            lop_ap_dung = [l.strip() for l in str(mon["Lớp áp dụng"]).split(",") if l.strip()]
            che_do = "tron_khoi" if "Trộn" in str(mon["Chế độ xếp"]) else "theo_lop"

            lop_khong_ton_tai = [l for l in lop_ap_dung if l not in class_names_for_exam]
            if lop_khong_ton_tai:
                loi_xep_phong.append(
                    f"Môn '{mon['Môn thi']}': lớp {lop_khong_ton_tai} chưa khai báo ở bảng "
                    f"Lớp học (tab 🏢) — kiểm tra lại tên lớp cho đúng."
                )
                continue

            hs_dang_ky = []
            for _, hs in students_df.iterrows():
                lop = hs["Lớp"]
                if lop in lop_ap_dung:
                    hs_dang_ky.append({
                        "ma_hs": str(hs.get("Mã HS (không bắt buộc)") or "").strip(),
                        "ho_ten": hs["Họ và tên"], "lop": lop,
                        "khoi": int(class_to_grade.get(lop) or 0),
                    })

            if not hs_dang_ky:
                loi_xep_phong.append(
                    f"Môn '{mon['Môn thi']}': không có học sinh nào thuộc lớp {lop_ap_dung} "
                    f"trong danh sách dự thi."
                )
                continue

            if not rooms_list_all:
                continue

            ket_qua, thieu = er.xep_phong_thi(hs_dang_ky, rooms_list_all, che_do)
            for phong in ket_qua:
                phong["so_cot"] = room_so_cot.get(phong["ten_phong"], 4)
                phong["hoc_sinh_cho_ngoi"] = er.xao_tron_cho_ngoi(phong["hoc_sinh"])
            ket_qua_moi[mon["Môn thi"]] = {
                "rooms": ket_qua, "thieu": thieu,
                "ngay": mon["Ngày thi"], "ca": mon["Ca thi"], "lop_ap_dung": lop_ap_dung,
            }

        if loi_xep_phong:
            for e in loi_xep_phong:
                st.error(e)
        if ket_qua_moi:
            st.session_state.exam_results = ket_qua_moi
            st.success(f"✅ Đã xếp phòng thi cho {len(ket_qua_moi)} môn.")

    if st.session_state.exam_results:
        st.divider()
        st.markdown('<div class="section-title"><h3>📋 Kết quả xếp phòng thi</h3></div>', unsafe_allow_html=True)

        mon_chon = st.selectbox("Chọn môn thi để xem", options=list(st.session_state.exam_results.keys()))
        entry = st.session_state.exam_results[mon_chon]
        st.caption(
            f"📚 Môn: **{mon_chon}** · Áp dụng lớp: **{', '.join(entry['lop_ap_dung'])}** · "
            f"Ngày thi: {entry['ngay']} · Ca: {entry['ca']}"
        )

        if entry["thieu"]:
            st.warning(
                f"⚠️ Không đủ chỗ cho {len(entry['thieu'])} học sinh (hết phòng): "
                + ", ".join(hs["ho_ten"] for hs in entry["thieu"][:10])
                + (" ..." if len(entry["thieu"]) > 10 else "")
                + ". Vào mục 2 thêm phòng thi hoặc tăng sức chứa rồi xếp lại."
            )

        exp1, exp2, exp3 = st.columns([1, 1, 1])
        with exp1:
            pdf_bytes_exam = exam_rooms_to_pdf_bytes(
                mon_chon, entry["ngay"], entry["ca"], entry["rooms"], school_name=school_name,
            )
            st.download_button(
                "📄 Xuất PDF (danh sách + sơ đồ)", data=pdf_bytes_exam,
                file_name=f"phong_thi_{slugify(mon_chon)}.pdf", mime="application/pdf",
                type="primary", use_container_width=True, key=f"pdf_exam_{mon_chon}",
            )
        with exp2:
            xls_bytes_exam = exam_rooms_to_excel_bytes(mon_chon, entry["ngay"], entry["ca"], entry["rooms"])
            st.download_button(
                "📊 Xuất Excel (theo phòng)", data=xls_bytes_exam,
                file_name=f"phong_thi_{slugify(mon_chon)}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key=f"xls_exam_{mon_chon}",
            )
        with exp3:
            if st.button(
                "🔀 Xáo lại chỗ ngồi", use_container_width=True, key=f"xao_lai_{mon_chon}",
                help="Chỉ xáo lại VỊ TRÍ NGỒI ngẫu nhiên trong từng phòng — không đổi danh sách "
                     "phòng/SBD đã xếp.",
            ):
                for phong in entry["rooms"]:
                    phong["hoc_sinh_cho_ngoi"] = er.xao_tron_cho_ngoi(phong["hoc_sinh"])
                st.rerun()

        st.write("")
        if not entry["rooms"]:
            st.info("Chưa có phòng nào được xếp cho môn này.")
        else:
            room_tabs = st.tabs([r["ten_phong"] for r in entry["rooms"]])
            for tab, r in zip(room_tabs, entry["rooms"]):
                with tab:
                    df_show = pd.DataFrame([
                        {"SBD": hs["sbd"], "Họ và tên": hs["ho_ten"], "Lớp": hs["lop"]}
                        for hs in r["hoc_sinh"]
                    ])
                    st.dataframe(df_show, use_container_width=True, hide_index=True)

                    st.markdown(
                        '<div class="section-title" style="margin-top:18px;">'
                        '<h3>🪑 Sơ đồ chỗ ngồi (xếp ngẫu nhiên theo SBD)</h3></div>',
                        unsafe_allow_html=True,
                    )
                    so_cot_hien_thi = r.get("so_cot", 4)
                    hs_cho_so_do = r.get("hoc_sinh_cho_ngoi") or r["hoc_sinh"]
                    hang_ghe = er.sap_xep_so_do_cho_ngoi(hs_cho_so_do, so_cot_hien_thi)
                    st.markdown(ve_so_do_cho_ngoi_html(hang_ghe), unsafe_allow_html=True)


# ---------------------------------------------------------------------
# MODULE 3 — Phân công dạy thay
# ---------------------------------------------------------------------
elif module == "🔄 Phân Công Dạy Thay":
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "1", "Phân công dạy thay",
        "Dựa trên thời khoá biểu đã xếp ở module 📅 để tìm giáo viên còn TRỐNG TIẾT đúng "
        "khung giờ giáo viên nghỉ dạy, gợi ý người dạy thay phù hợp.",
    )

    ket_qua_tkb = st.session_state.get("result")
    if not ket_qua_tkb or ket_qua_tkb.status in ("INFEASIBLE", "ERROR"):
        st.info(
            "⚠️ Chưa có thời khoá biểu nào được xếp thành công. Sang module "
            "\"📅 Xếp Thời Khoá Biểu\" → tab \"⚖️ Ràng buộc & Xếp lịch\" → bấm "
            "\"🗓️ Xếp thời khoá biểu\" trước, rồi quay lại đây."
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        cfg_tkb = st.session_state.result_config
        classes_tkb = st.session_state.result_classes
        class_id_to_name = {c.id: c.name for c in classes_tkb}
        teacher_id_to_name_sub = {slugify(n, "gv_"): n for n in teacher_names}
        teacher_name_to_id_sub = {v: k for k, v in teacher_id_to_name_sub.items()}

        # GV nào dạy môn nào (subject_id) -> để ưu tiên gợi ý GV cùng chuyên môn
        teacher_subjects: dict[str, set] = {}
        for lesson in ket_qua_tkb.lessons:
            for tid in lesson.teacher_ids:
                teacher_subjects.setdefault(tid, set()).add(lesson.subject_id)

        c1, c2 = st.columns(2)
        with c1:
            ngay_chon = st.selectbox(
                "Ngày cần phân công dạy thay",
                options=cfg_tkb.days,
                format_func=lambda d: nhan_ngay_thuc_te(d, st.session_state.tuan_bat_dau),
                key="sub_ngay_chon",
            )
        with c2:
            gv_nghi_ten = st.selectbox("Giáo viên nghỉ dạy", options=teacher_names, key="sub_gv_nghi")

        gv_nghi_id = teacher_name_to_id_sub.get(gv_nghi_ten)

        tiet_cua_gv = sorted(
            [
                lesson for lesson in ket_qua_tkb.lessons
                if gv_nghi_id in lesson.teacher_ids and lesson.day == ngay_chon
            ],
            key=lambda l: l.period,
        )

        if not tiet_cua_gv:
            st.success(
                f"🎉 {gv_nghi_ten} không có tiết dạy nào vào "
                f"{nhan_ngay_thuc_te(ngay_chon, st.session_state.tuan_bat_dau)} — không cần dạy thay."
            )
        else:
            st.caption(
                f"{gv_nghi_ten} có {len(tiet_cua_gv)} tiết vào "
                f"{nhan_ngay_thuc_te(ngay_chon, st.session_state.tuan_bat_dau)}. Chọn GV dạy thay "
                f"cho từng tiết cần thiết bên dưới (bỏ trống nếu không cần thay, VD tiết trống/sinh hoạt)."
            )

            # GV bận tại (ngay, tiet) -> để tính GV rảnh
            ban_tai: dict[int, set] = {}
            for lesson in ket_qua_tkb.lessons:
                if lesson.day == ngay_chon:
                    ban_tai.setdefault(lesson.period, set()).update(lesson.teacher_ids)

            phan_cong_tam = []

            with st.form("form_phan_cong_day_thay"):
                for lesson in tiet_cua_gv:
                    lop_ten = ", ".join(class_id_to_name.get(cid, cid) for cid in lesson.class_ids)
                    st.markdown(
                        f'<div class="constraint-row"><b>Tiết {lesson.period}</b> — Lớp {lop_ten} '
                        f'— Môn: {lesson.activity_name}</div>',
                        unsafe_allow_html=True,
                    )

                    ban_tiet_nay = ban_tai.get(lesson.period, set()) | {gv_nghi_id}
                    ung_vien_ids = [tid for tid in teacher_id_to_name_sub if tid not in ban_tiet_nay]

                    # Ưu tiên GV cùng môn (subject_id trùng), sau đó theo tên
                    mon_can_thay = lesson.subject_id
                    ung_vien_ids.sort(
                        key=lambda tid: (
                            0 if mon_can_thay in teacher_subjects.get(tid, set()) else 1,
                            teacher_id_to_name_sub[tid],
                        )
                    )
                    nhan_ung_vien = ["— Không phân công —"] + [
                        teacher_id_to_name_sub[tid]
                        + (" ⭐ cùng môn" if mon_can_thay in teacher_subjects.get(tid, set()) else "")
                        for tid in ung_vien_ids
                    ]
                    lua_chon = st.selectbox(
                        f"GV dạy thay cho Tiết {lesson.period} ({lop_ten})",
                        options=nhan_ung_vien,
                        key=f"sub_chon_{ngay_chon}_{lesson.period}_{'_'.join(lesson.class_ids)}",
                        label_visibility="collapsed",
                    )
                    gv_thay_ten = None
                    if lua_chon != "— Không phân công —":
                        gv_thay_ten = lua_chon.split(" ⭐")[0]

                    phan_cong_tam.append({
                        "tiet": lesson.period, "lop": lop_ten, "mon": lesson.activity_name,
                        "gv_nghi": gv_nghi_ten, "gv_thay": gv_thay_ten,
                    })

                luu_btn = st.form_submit_button(
                    "💾 Lưu phân công dạy thay cho ngày này", type="primary", use_container_width=True,
                )

                if luu_btn:
                    ngay_key = f"{ngay_chon}_{gv_nghi_ten}"
                    st.session_state.substitutions[ngay_key] = {
                        "ngay": ngay_chon,
                        "ngay_hien_thi": nhan_ngay_thuc_te(ngay_chon, st.session_state.tuan_bat_dau),
                        "gv_nghi": gv_nghi_ten,
                        "phan_cong": phan_cong_tam,
                    }
                    st.success("✅ Đã lưu phân công dạy thay!")

        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.substitutions:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            section_header("2", "Các phân công đã lưu")

            for key_luu, ban_ghi in list(st.session_state.substitutions.items()):
                with st.expander(
                    f"{ban_ghi['ngay_hien_thi']} — GV nghỉ: {ban_ghi['gv_nghi']} "
                    f"({len(ban_ghi['phan_cong'])} tiết)"
                ):
                    df_xem = pd.DataFrame(ban_ghi["phan_cong"])[["tiet", "lop", "mon", "gv_thay"]]
                    df_xem.columns = ["Tiết", "Lớp", "Môn", "GV dạy thay"]
                    df_xem["GV dạy thay"] = df_xem["GV dạy thay"].fillna("— chưa phân công —")
                    st.dataframe(df_xem, use_container_width=True, hide_index=True)

                    bc1, bc2, bc3 = st.columns([1, 1, 2])
                    with bc1:
                        pdf_sub = substitution_to_pdf_bytes(
                            ban_ghi["ngay_hien_thi"], ban_ghi["phan_cong"], school_name=school_name,
                        )
                        st.download_button(
                            "📄 Xuất PDF", data=pdf_sub,
                            file_name=f"day_thay_{slugify(ban_ghi['gv_nghi'])}.pdf",
                            mime="application/pdf", use_container_width=True, key=f"pdf_sub_{key_luu}",
                        )
                    with bc2:
                        if st.button("🗑️ Xoá", use_container_width=True, key=f"del_sub_{key_luu}"):
                            del st.session_state.substitutions[key_luu]
                            st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="app-footer">Ứng dụng được phát triển bởi Chuyên viên Quản lý hệ thống — '
    'Trường TH, THCS và THPT Tân Phú</div>',
    unsafe_allow_html=True,
)
