"""
Ứng dụng Streamlit: xếp thời khoá biểu tự động 100% theo ràng buộc.
Giao diện dạng BẢNG NHẬP LIỆU (giống Excel) — không cần biết JSON.

Chạy local:  streamlit run app.py
Deploy:      đẩy lên GitHub rồi deploy trên https://share.streamlit.io
"""

import html
import io
import random
import re
import unicodedata
from datetime import date, datetime, time, timedelta

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
    width:104px; min-height:54px; border-radius:10px; display:flex; flex-direction:column;
    align-items:center; justify-content:center; text-align:center; padding:6px;
}
.seat.filled{
    background:linear-gradient(180deg, #FFFFFF 0%, #FBFCFE 100%);
    border:1.5px solid var(--navy-700);
    box-shadow:0 4px 10px -4px rgba(18,41,75,0.30), 0 1px 0 rgba(255,255,255,0.7) inset;
}
.seat.empty{ background:var(--gray-100); border:1.5px dashed var(--gray-200); }
.seat-sbd{ font-weight:800; color:var(--navy-800) !important; font-size:1.02rem; letter-spacing:.3px; }
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


def excel_io_row(state_key: str, label: str, transform=None):
    """Thanh công cụ Xuất/Nhập Excel cho 1 bảng dữ liệu (session_state[state_key]).
    transform: hàm chuẩn hoá DataFrame vừa đọc từ file (tuỳ chọn)."""
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
                    if transform is not None:
                        new_df = transform(new_df)
                    st.session_state[state_key] = new_df
                    st.session_state[f"_imported_{state_key}"] = marker
                    # xoá trạng thái chỉnh sửa cũ của bảng để hiện đúng dữ liệu mới
                    st.session_state.pop(f"editor_{state_key}", None)
                    st.success(f"Đã nhập {len(new_df)} dòng từ Excel vào mục '{label}'.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Không đọc được file Excel: {e}")


# ---------------------------------------------------------------------
# THỜI GIAN BIỂU THEO TỪNG KHỐI, TỪNG NGÀY
# Bảng st.session_state.grade_times: Khối | Thứ | Tiết | Giờ bắt đầu | Giờ kết thúc
#   - Thứ = "Tất cả các ngày": áp dụng cho mọi ngày của khối đó, TRỪ những
#     ngày đã khai báo riêng (dòng Thứ cụ thể luôn được ưu tiên).
#   - Tiết = 0: khối đó NGHỈ cả ngày hôm đó.
#   - Khối nào có khai báo thì ngày đó CHỈ được xếp vào đúng các tiết đã khai
#     báo (ràng buộc thật cho bộ giải). Khối không khai báo dòng nào thì học
#     đủ "Số tiết/ngày tối đa", nhãn hiển thị mặc định là 'Tiết N'.
# ---------------------------------------------------------------------
THU_TAT_CA = "Tất cả các ngày"
DAY_OPTIONS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
NAME_TO_DAY = {v: k for k, v in DAY_NAMES.items()}
GRADE_TIME_COLUMNS = ["Khối", "Thứ", "Tiết", "Giờ bắt đầu", "Giờ kết thúc"]


def _o_trong(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip().lower() in ("", "nan", "none", "nat")


def chuan_hoa_bang_gio(df: pd.DataFrame) -> pd.DataFrame:
    """Đảm bảo bảng giờ học có đủ cột (tương thích file Excel cũ chưa có cột
    'Thứ' — khi đó coi như áp dụng cho tất cả các ngày)."""
    df = df.copy() if df is not None else pd.DataFrame(columns=GRADE_TIME_COLUMNS)
    if "Thứ" not in df.columns:
        df.insert(1 if "Khối" in df.columns else 0, "Thứ", THU_TAT_CA)
    for col in GRADE_TIME_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["Thứ"] = df["Thứ"].apply(lambda v: THU_TAT_CA if _o_trong(v) else str(v).strip())
    for col in ("Giờ bắt đầu", "Giờ kết thúc"):
        df[col] = df[col].apply(lambda v: "" if _o_trong(v) else str(v).strip()[:5])
    return df[GRADE_TIME_COLUMNS + [c for c in df.columns if c not in GRADE_TIME_COLUMNS]]


def lich_hoc_theo_khoi_ngay(df: pd.DataFrame, days: list[int]):
    """Đọc bảng giờ học -> ({(khoi, day): {tiet: "07:15–08:00" | ""}}, errors).
    Có key (khoi, day) nghĩa là khối đó ngày đó CHỈ học các tiết trong dict
    (dict rỗng = nghỉ cả ngày)."""
    errors: list[str] = []
    rieng: dict[tuple[int, int], dict[int, str]] = {}
    chung: dict[int, dict[int, str]] = {}
    if df is None or df.empty:
        return {}, errors
    df = chuan_hoa_bang_gio(df)
    for i, row in df.iterrows():
        khoi = pd.to_numeric(row["Khối"], errors="coerce")
        tiet = pd.to_numeric(row["Tiết"], errors="coerce")
        if pd.isna(khoi) and pd.isna(tiet):
            continue  # dòng trống
        if pd.isna(khoi) or pd.isna(tiet):
            errors.append(f"Thời gian biểu dòng {i + 1}: thiếu Khối hoặc Tiết.")
            continue
        khoi, tiet = int(khoi), int(tiet)
        bd, kt = row["Giờ bắt đầu"], row["Giờ kết thúc"]
        gio = f"{bd}–{kt}" if bd and kt else bd
        thu = row["Thứ"]
        if thu == THU_TAT_CA:
            dich = chung.setdefault(khoi, {})
        elif thu in NAME_TO_DAY:
            d = NAME_TO_DAY[thu]
            if d not in days:
                continue  # ngày không nằm trong số ngày học/tuần đã chọn
            dich = rieng.setdefault((khoi, d), {})
        else:
            errors.append(f"Thời gian biểu dòng {i + 1}: giá trị Thứ '{thu}' không hợp lệ.")
            continue
        if tiet > 0:
            dich[tiet] = gio

    lich = dict(rieng)
    for khoi, tiet_dict in chung.items():
        for d in days:
            lich.setdefault((khoi, d), dict(tiet_dict))
    return lich, errors


def tao_bang_gio_tu_dong(
    khoi_list, thu_list, so_tiet_sang: int, gio_sang, so_tiet_chieu: int, gio_chieu,
    tiet_dau_chieu: int, thoi_luong: int, nghi_giua_tiet: int, ra_choi_sau: int, ra_choi_phut: int,
) -> list[dict]:
    """Sinh các dòng thời gian biểu cho mọi cặp (khối, thứ) đã chọn. Tiết buổi
    chiều được đánh số từ `tiet_dau_chieu` (= số tiết buổi sáng của toàn
    trường + 1) để khớp với số tiết chung mà bộ giải dùng."""
    def _sinh(so_tiet, bat_dau, tiet_dau):
        rows, t = [], datetime.combine(date.today(), bat_dau)
        for k in range(so_tiet):
            ket_thuc = t + timedelta(minutes=thoi_luong)
            rows.append((tiet_dau + k, t.strftime("%H:%M"), ket_thuc.strftime("%H:%M")))
            nghi = ra_choi_phut if (ra_choi_sau and k + 1 == ra_choi_sau) else nghi_giua_tiet
            t = ket_thuc + timedelta(minutes=nghi)
        return rows

    tiet_trong_ngay = _sinh(so_tiet_sang, gio_sang, 1) + _sinh(so_tiet_chieu, gio_chieu, tiet_dau_chieu)
    out = []
    for khoi in khoi_list:
        for thu in thu_list:
            if not tiet_trong_ngay:
                out.append({"Khối": int(khoi), "Thứ": thu, "Tiết": 0,
                            "Giờ bắt đầu": "Nghỉ", "Giờ kết thúc": ""})
            for tiet, bd, kt in tiet_trong_ngay:
                out.append({"Khối": int(khoi), "Thứ": thu, "Tiết": tiet,
                            "Giờ bắt đầu": bd, "Giờ kết thúc": kt})
    return out


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
                # Sơ đồ chỗ ngồi chỉ hiện SỐ BÁO DANH (không hiện tên học sinh)
                o_html.append(
                    f'<div class="seat filled">'
                    f'<div class="seat-sbd">{html.escape(str(o["sbd"]))}</div>'
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

def _mau_gio(khoi, thu_list, so_sang, gio_sang, so_chieu, gio_chieu):
    return tao_bang_gio_tu_dong(
        [khoi], thu_list, so_sang, gio_sang, so_chieu, gio_chieu,
        tiet_dau_chieu=4, thoi_luong=45, nghi_giua_tiet=5, ra_choi_sau=2, ra_choi_phut=20,
    )


# Mẫu: khối 6 cấu hình RIÊNG từng ngày; khối 7 & 10 dùng chung "Tất cả các
# ngày", riêng khối 10 Thứ 7 chỉ học buổi sáng (dòng riêng được ưu tiên).
SAMPLE_GRADE_TIMES = pd.DataFrame(
    _mau_gio(6, ["Thứ 2", "Thứ 4", "Thứ 6"], 3, time(7, 15), 1, time(13, 30))
    + _mau_gio(6, ["Thứ 3", "Thứ 5"], 3, time(7, 15), 2, time(13, 30))
    + _mau_gio(6, ["Thứ 7"], 3, time(7, 15), 0, time(13, 30))
    + _mau_gio(7, [THU_TAT_CA], 3, time(7, 30), 2, time(13, 45))
    + _mau_gio(10, [THU_TAT_CA], 3, time(7, 0), 2, time(13, 15))
    + _mau_gio(10, ["Thứ 7"], 3, time(7, 0), 0, time(13, 15)),
    columns=GRADE_TIME_COLUMNS,
)

# Danh sách học sinh dự thi: KHÔNG cần họ tên, chỉ cần SBD (để trống thì hệ
# thống tự sinh), Lớp và các môn thi của học sinh đó (cách nhau dấu phẩy) —
# vì cùng 1 lớp, mỗi học sinh có thể chọn các môn lựa chọn khác nhau.
EXAM_STUDENT_COLUMNS = ["SBD", "Họ và tên (không bắt buộc)", "Lớp", "Môn thi"]
SAMPLE_EXAM_STUDENTS = pd.DataFrame([
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "10A1", "Môn thi": "Toán, Ngữ văn, Vật lí, Hoá học"},
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "10A1", "Môn thi": "Toán, Ngữ văn, Địa lí, GDKT&PL"},
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "10A1", "Môn thi": "Toán, Ngữ văn, Vật lí, Tin học"},
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "10A1", "Môn thi": "Toán, Ngữ văn, Địa lí, Hoá học"},
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "11A1", "Môn thi": "Toán, Ngữ văn, Vật lí, Hoá học"},
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "11A1", "Môn thi": "Toán, Ngữ văn, Địa lí, GDKT&PL"},
    {"SBD": "", "Họ và tên (không bắt buộc)": "", "Lớp": "11A1", "Môn thi": "Toán, Ngữ văn, Tin học, GDKT&PL"},
], columns=EXAM_STUDENT_COLUMNS)

SAMPLE_EXAM_ROOMS = pd.DataFrame([
    {"Tên phòng": "P101", "Sức chứa": 24, "Số cột bàn": 4},
    {"Tên phòng": "P102", "Sức chứa": 24, "Số cột bàn": 4},
    {"Tên phòng": "P103", "Sức chứa": 24, "Số cột bàn": 4},
])

EXAM_SUBJECT_COLUMNS = ["Môn thi", "Lớp áp dụng (không bắt buộc)", "Ngày thi", "Ca thi", "Chế độ xếp"]
SAMPLE_EXAM_SUBJECTS = pd.DataFrame([
    {"Môn thi": "Toán", "Lớp áp dụng (không bắt buộc)": "", "Ngày thi": "15/09/2026", "Ca thi": "Sáng",
     "Chế độ xếp": "Trộn theo khối (xáo giữa các lớp)"},
    {"Môn thi": "Ngữ văn", "Lớp áp dụng (không bắt buộc)": "", "Ngày thi": "15/09/2026", "Ca thi": "Chiều",
     "Chế độ xếp": "Trộn theo khối (xáo giữa các lớp)"},
    {"Môn thi": "Vật lí", "Lớp áp dụng (không bắt buộc)": "", "Ngày thi": "16/09/2026", "Ca thi": "Sáng",
     "Chế độ xếp": "Theo lớp (giữ nguyên lớp)"},
    {"Môn thi": "Địa lí", "Lớp áp dụng (không bắt buộc)": "", "Ngày thi": "16/09/2026", "Ca thi": "Sáng",
     "Chế độ xếp": "Theo lớp (giữ nguyên lớp)"},
], columns=EXAM_SUBJECT_COLUMNS)

DEFAULTS = dict(
    departments=SAMPLE_DEPARTMENTS, teachers=SAMPLE_TEACHERS, classes=SAMPLE_CLASSES,
    rooms=SAMPLE_ROOMS, activities=SAMPLE_ACTIVITIES, grade_times=SAMPLE_GRADE_TIMES,
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
        st.session_state.exam_all_students = []
        st.session_state.substitutions = {}
        for k in ("editor_grade_times", "editor_exam_students", "editor_exam_subjects"):
            st.session_state.pop(k, None)
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
            "2", "Thời gian biểu theo từng khối, từng ngày (không bắt buộc)",
            "Cấu hình RIÊNG cho từng khối và từng ngày: khối đó ngày đó học những tiết nào, "
            "giờ bắt đầu/kết thúc của từng tiết. Cột <b>Thứ</b> chọn <i>Tất cả các ngày</i> để "
            "áp dụng chung cho cả tuần — ngày nào khai báo riêng thì dòng riêng được ưu tiên. "
            "<b>Tiết = 0</b> nghĩa là khối đó nghỉ cả ngày. Đây là ràng buộc THẬT: khối đã khai "
            "báo thì ngày đó CHỈ được xếp vào đúng các tiết có trong bảng. Khối nào không có dòng "
            "nào sẽ học đủ 'Số tiết/ngày tối đa' với nhãn mặc định 'Tiết N'. Tiết buổi chiều được "
            f"đánh số tiếp theo buổi sáng (buổi sáng hiện có {int(morning_count)} tiết → buổi "
            f"chiều bắt đầu từ Tiết {int(morning_count) + 1}).",
        )
        st.session_state.grade_times = chuan_hoa_bang_gio(st.session_state.grade_times)

        grades_known = sorted({
            int(g) for g in pd.to_numeric(st.session_state.classes["Khối"], errors="coerce").dropna()
        }) or list(range(1, 13))
        thu_hien_co = DAY_OPTIONS[:int(num_days)]
        so_tiet_chieu_toi_da = max(int(periods_per_day) - int(morning_count), 0)

        with st.expander("⚡ Tạo nhanh thời gian biểu cho nhiều khối / nhiều ngày", expanded=False):
            with st.form("form_tao_gio_hoc"):
                g1, g2 = st.columns(2)
                with g1:
                    tg_khoi = st.multiselect("Khối áp dụng", grades_known, default=grades_known[:1])
                with g2:
                    tg_thu = st.multiselect(
                        "Ngày áp dụng", [THU_TAT_CA] + thu_hien_co, default=[THU_TAT_CA],
                        help="Chọn 'Tất cả các ngày' để dùng chung cho cả tuần, hoặc chọn từng ngày "
                             "cụ thể để cấu hình riêng.",
                    )
                g3, g4, g5, g6 = st.columns(4)
                with g3:
                    tg_so_sang = st.number_input(
                        "Số tiết buổi sáng", 0, int(morning_count), int(morning_count), step=1)
                with g4:
                    tg_gio_sang = st.time_input("Giờ vào học buổi sáng", time(7, 0), step=300)
                with g5:
                    tg_so_chieu = st.number_input(
                        "Số tiết buổi chiều", 0, so_tiet_chieu_toi_da, so_tiet_chieu_toi_da, step=1)
                with g6:
                    tg_gio_chieu = st.time_input("Giờ vào học buổi chiều", time(13, 30), step=300)
                g7, g8, g9, g10 = st.columns(4)
                with g7:
                    tg_thoi_luong = st.number_input("Thời lượng 1 tiết (phút)", 20, 120, 45, step=5)
                with g8:
                    tg_nghi = st.number_input("Nghỉ giữa 2 tiết (phút)", 0, 60, 5, step=5)
                with g9:
                    tg_ra_choi_sau = st.number_input(
                        "Ra chơi sau tiết thứ (của mỗi buổi)", 0, 10, 2, step=1,
                        help="Để 0 nếu không có giờ ra chơi dài.")
                with g10:
                    tg_ra_choi = st.number_input("Thời gian ra chơi (phút)", 0, 60, 20, step=5)
                tao_btn = st.form_submit_button(
                    "⚡ Tạo / ghi đè thời gian biểu cho các khối & ngày đã chọn",
                    type="primary", use_container_width=True,
                )
            if tao_btn:
                if not tg_khoi or not tg_thu:
                    st.error("Chọn ít nhất 1 khối và 1 ngày.")
                else:
                    moi = tao_bang_gio_tu_dong(
                        tg_khoi, tg_thu, int(tg_so_sang), tg_gio_sang, int(tg_so_chieu), tg_gio_chieu,
                        tiet_dau_chieu=int(morning_count) + 1, thoi_luong=int(tg_thoi_luong),
                        nghi_giua_tiet=int(tg_nghi), ra_choi_sau=int(tg_ra_choi_sau),
                        ra_choi_phut=int(tg_ra_choi),
                    )
                    cu = st.session_state.grade_times
                    khoi_cu = pd.to_numeric(cu["Khối"], errors="coerce")
                    giu_lai = cu[~(khoi_cu.isin(tg_khoi) & cu["Thứ"].isin(tg_thu))]
                    st.session_state.grade_times = pd.concat(
                        [giu_lai, pd.DataFrame(moi, columns=GRADE_TIME_COLUMNS)], ignore_index=True,
                    ).sort_values(
                        ["Khối", "Thứ", "Tiết"],
                        key=lambda col: col.map(
                            lambda v: ([THU_TAT_CA] + DAY_OPTIONS).index(v)
                            if v in ([THU_TAT_CA] + DAY_OPTIONS) else 99
                        ) if col.name == "Thứ" else pd.to_numeric(col, errors="coerce"),
                    ).reset_index(drop=True)
                    st.session_state.pop("editor_grade_times", None)
                    st.rerun()

        excel_io_row("grade_times", "Thoi_gian_bieu", transform=chuan_hoa_bang_gio)
        st.session_state.grade_times = st.data_editor(
            st.session_state.grade_times, num_rows="dynamic", use_container_width=True,
            key="editor_grade_times",
            column_config={
                "Khối": st.column_config.NumberColumn(min_value=1, max_value=12, step=1, required=True),
                "Thứ": st.column_config.SelectboxColumn(
                    options=[THU_TAT_CA] + DAY_OPTIONS, required=True,
                    help="'Tất cả các ngày' = dùng chung cả tuần; dòng của ngày cụ thể được ưu tiên.",
                ),
                "Tiết": st.column_config.NumberColumn(
                    min_value=0, max_value=15, step=1, required=True,
                    help="Số thứ tự tiết trong ngày. Nhập 0 nếu khối đó NGHỈ cả ngày hôm đó.",
                ),
                "Giờ bắt đầu": st.column_config.TextColumn(help="Định dạng HH:MM, VD 07:15"),
                "Giờ kết thúc": st.column_config.TextColumn(help="Định dạng HH:MM, VD 08:00"),
            },
        )

        # Xem lại dạng lưới cho từng khối: dòng = Tiết, cột = Thứ
        lich_xem, loi_xem = lich_hoc_theo_khoi_ngay(
            st.session_state.grade_times, list(range(1, int(num_days) + 1))
        )
        for e in loi_xem:
            st.warning(e)
        khoi_da_cau_hinh = sorted({k for k, _ in lich_xem})
        if khoi_da_cau_hinh:
            st.markdown("**👀 Xem lại thời gian biểu theo khối**")
            khoi_tabs = st.tabs([f"Khối {k}" for k in khoi_da_cau_hinh])
            for tab, k in zip(khoi_tabs, khoi_da_cau_hinh):
                with tab:
                    luoi = pd.DataFrame(
                        "", index=[f"Tiết {p}" for p in range(1, int(periods_per_day) + 1)],
                        columns=thu_hien_co,
                    )
                    for d in range(1, int(num_days) + 1):
                        tiet_dict = lich_xem.get((k, d))
                        for p in range(1, int(periods_per_day) + 1):
                            if tiet_dict is None:
                                luoi.iloc[p - 1, d - 1] = "(mặc định)"
                            elif p in tiet_dict:
                                luoi.iloc[p - 1, d - 1] = tiet_dict[p] or "✔"
                            else:
                                luoi.iloc[p - 1, d - 1] = "—"
                    st.dataframe(luoi, use_container_width=True)
            st.caption("— = khối không học tiết đó; (mặc định) = ngày đó chưa khai báo, học đủ các tiết.")
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

        # Thời gian biểu theo (khối, ngày) -> tập tiết được phép học
        lich_hoc, loi_lich = lich_hoc_theo_khoi_ngay(
            st.session_state.grade_times, list(range(1, num_days + 1))
        )
        errors.extend(loi_lich)
        grade_day_periods = []
        for (khoi, d), tiet_dict in sorted(lich_hoc.items()):
            vuot = [t for t in tiet_dict if t > int(periods_per_day)]
            if vuot:
                errors.append(
                    f"Thời gian biểu: Khối {khoi} - {DAY_NAMES[d]} có Tiết {vuot}, vượt quá "
                    f"'Số tiết/ngày tối đa' ({int(periods_per_day)}) ở mục 1 — tăng số đó lên trước."
                )
                continue
            grade_day_periods.append(
                GradeDayCapacity(grade=khoi, day=d, allowed_periods=sorted(tiet_dict))
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
            tuan_bat_dau = st.session_state.tuan_bat_dau
            lich_hoc, _ = lich_hoc_theo_khoi_ngay(st.session_state.get("grade_times"), days)

            # map teacher_id -> tên hiển thị (để hiện tên GV thay vì mã nội bộ)
            teacher_id_to_name = {
                slugify(n, "gv_"): n for n in st.session_state.teachers["Tên giáo viên"].dropna()
            }

            # Nhãn dòng "Tiết N (giờ-giờ)" theo khối của từng lớp. Nếu giờ của 1
            # tiết KHÁC NHAU giữa các ngày (thời gian biểu cấu hình riêng từng
            # ngày) thì nhãn dòng chỉ ghi "Tiết N", giờ được ghi trong từng ô.
            period_labels_by_class, cell_times_by_class, off_slots_by_class = {}, {}, {}
            for c in classes:
                labels, cell_times, off = {}, {}, set()
                for p in periods:
                    gio_cac_ngay = {}
                    for d in days:
                        tiet_dict = lich_hoc.get((c.grade, d))
                        if tiet_dict is None:
                            continue
                        if p in tiet_dict:
                            gio_cac_ngay[d] = tiet_dict[p]
                        else:
                            off.add((d, p))
                    gio_khac_nhau = {g for g in gio_cac_ngay.values() if g}
                    if len(gio_khac_nhau) == 1:
                        labels[p] = f"Tiết {p} ({gio_khac_nhau.pop()})"
                    else:
                        labels[p] = f"Tiết {p}"
                        cell_times.update({(d, p): g for d, g in gio_cac_ngay.items() if g})
                period_labels_by_class[c.id] = labels
                cell_times_by_class[c.id] = cell_times
                off_slots_by_class[c.id] = off

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
                for p in periods:
                    for d in days:
                        if (d, p) in off_slots_by_class[c.id]:
                            grid.loc[period_labels_by_class[c.id][p], day_col_labels[d]] = "✕ không học"
                        elif (d, p) in cell_times_by_class[c.id]:
                            grid.loc[period_labels_by_class[c.id][p], day_col_labels[d]] = (
                                f"🕘 {cell_times_by_class[c.id][(d, p)]}"
                            )
                for lesson in result.lessons:
                    if c.id in lesson.class_ids:
                        row_label = period_labels_by_class[c.id].get(lesson.period)
                        col_label = day_col_labels.get(lesson.day)
                        if row_label in grid.index and col_label in grid.columns:
                            teacher_display = ", ".join(
                                teacher_id_to_name.get(tid, tid) for tid in lesson.teacher_ids
                            )
                            text = f"{lesson.activity_name} ({teacher_display})"
                            gio = cell_times_by_class[c.id].get((lesson.day, lesson.period))
                            grid.loc[row_label, col_label] = f"{text} · {gio}" if gio else text
                return grid

            # ---------------- Xuất kết quả: PDF & Excel ----------------
            exp_c1, exp_c2, _ = st.columns([1, 1, 2])
            with exp_c1:
                pdf_bytes = timetable_to_pdf_bytes(
                    classes, config, result.lessons, day_col_labels, teacher_id_to_name,
                    dept_free_sessions=result.department_free_sessions,
                    school_name=school_name,
                    period_labels_by_class=period_labels_by_class,
                    cell_times_by_class=cell_times_by_class,
                    off_slots_by_class=off_slots_by_class,
                )
                st.download_button(
                    "📄 Xuất PDF thời khoá biểu", data=pdf_bytes,
                    file_name="thoi_khoa_bieu.pdf", mime="application/pdf",
                    type="primary", use_container_width=True,
                )
            with exp_c2:
                xls_buf = io.BytesIO()
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
    class_to_grade = {
        str(row["Tên lớp"]).strip(): int(row["Khối"])
        for _, row in st.session_state.classes.dropna(subset=["Tên lớp", "Khối"]).iterrows()
    }

    def khoi_cua_lop(lop: str) -> int:
        """Ưu tiên khối khai báo ở bảng Lớp học (module TKB); lớp không có ở
        đó thì đoán từ tên lớp, VD '10A1' -> 10."""
        return class_to_grade.get(lop) or er.khoi_tu_ten_lop(lop)

    def chuan_hoa_bang_mon_thi(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "Lớp áp dụng" in df.columns and "Lớp áp dụng (không bắt buộc)" not in df.columns:
            df = df.rename(columns={"Lớp áp dụng": "Lớp áp dụng (không bắt buộc)"})
        for col in EXAM_SUBJECT_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[EXAM_SUBJECT_COLUMNS]

    def chuan_hoa_bang_hoc_sinh(df: pd.DataFrame) -> pd.DataFrame:
        if list(df.columns) == er.COT_CHUAN:
            return df
        df_moi, _ = er.chuan_hoa_danh_sach_hoc_sinh(df)
        return df_moi

    # tương thích dữ liệu cũ trong phiên làm việc / file Excel định dạng cũ
    try:
        st.session_state.exam_students = chuan_hoa_bang_hoc_sinh(st.session_state.exam_students)
    except ValueError:
        st.session_state.exam_students = pd.DataFrame(columns=er.COT_CHUAN)
    st.session_state.exam_subjects = chuan_hoa_bang_mon_thi(st.session_state.exam_subjects)

    # ------------------------------------------------------------------
    # 1. Danh sách học sinh dự thi (upload file)
    # ------------------------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "1", "Danh sách học sinh dự thi — Lớp & Môn thi của từng học sinh",
        "Tải lên file <b>Excel (.xlsx/.xls) hoặc CSV</b> gồm các cột: <b>SBD</b> (hoặc Mã HS — để "
        "trống thì hệ thống tự sinh), <b>Lớp</b>, <b>Môn thi</b>. KHÔNG cần họ tên học sinh. Vì 1 lớp "
        "có thể có nhiều môn lựa chọn khác nhau, môn thi được khai báo RIÊNG cho từng học sinh, "
        "theo 1 trong 3 kiểu: (1) cột <i>Môn thi</i> ghi nhiều môn cách nhau dấu phẩy; (2) mỗi môn "
        "1 dòng (các dòng cùng SBD tự gộp lại); (3) mỗi môn 1 cột, đánh dấu <code>x</code> nếu HS "
        "thi môn đó.",
    )
    up_c1, up_c2, up_c3 = st.columns(3)
    with up_c1:
        st.download_button(
            "📄 Tải file mẫu", use_container_width=True, key="dl_mau_hs_thi",
            data=df_to_excel_bytes(SAMPLE_EXAM_STUDENTS.drop(columns=[er.COT_HO_TEN]), "Danh_sach_HS_thi"),
            file_name="mau_danh_sach_hoc_sinh_thi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with up_c2:
        st.download_button(
            "📥 Xuất Excel danh sách hiện tại", use_container_width=True, key="dl_exam_students",
            data=df_to_excel_bytes(st.session_state.exam_students, "Danh_sach_HS_thi"),
            file_name="danh_sach_hoc_sinh_thi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with up_c3:
        file_hs = st.file_uploader(
            "📤 Upload danh sách học sinh (thay thế bảng)", type=["xlsx", "xls", "csv"],
            key="up_exam_students",
        )
    if file_hs is not None:
        marker = f"{file_hs.name}:{file_hs.size}"
        if st.session_state.get("_imported_exam_students") != marker:
            try:
                if file_hs.name.lower().endswith(".csv"):
                    raw_df = pd.read_csv(file_hs, dtype=str, encoding="utf-8-sig", sep=None, engine="python")
                else:
                    raw_df = pd.read_excel(file_hs, dtype=str)
                df_moi, ghi_chu = er.chuan_hoa_danh_sach_hoc_sinh(raw_df)
                st.session_state.exam_students = df_moi
                st.session_state["_imported_exam_students"] = marker
                st.session_state["_ghi_chu_upload_hs"] = (
                    [f"✅ Đã nhập {len(df_moi)} học sinh từ file '{file_hs.name}'."] + ghi_chu
                )
                st.session_state.pop("editor_exam_students", None)
                st.session_state.exam_results = {}
                st.rerun()
            except Exception as e:
                st.error(f"Không đọc được file: {e}")
    for gc in st.session_state.pop("_ghi_chu_upload_hs", []):
        (st.success if gc.startswith("✅") else st.info)(gc)

    st.session_state.exam_students = st.data_editor(
        st.session_state.exam_students, num_rows="dynamic", use_container_width=True,
        key="editor_exam_students",
        column_config={
            er.COT_SBD: st.column_config.TextColumn(help="Để trống thì hệ thống tự sinh SBD theo khối."),
            er.COT_HO_TEN: st.column_config.TextColumn(help="Không bắt buộc — có thể bỏ trống."),
            er.COT_LOP: st.column_config.TextColumn(required=True),
            er.COT_MON: st.column_config.TextColumn(
                width="large",
                help="Các môn học sinh này thi, cách nhau dấu phẩy. VD: Toán, Ngữ văn, Vật lí. "
                     "Để trống = thi theo 'Lớp áp dụng' ở bảng Môn thi.",
            ),
        },
    )

    # đọc bảng học sinh -> list[dict]
    ds_hoc_sinh = []
    for _, r in st.session_state.exam_students.iterrows():
        lop = er._chuoi(r.get(er.COT_LOP))
        if not lop:
            continue
        ds_hoc_sinh.append({
            "sbd": er._chuoi(r.get(er.COT_SBD)),
            "ho_ten": er._chuoi(r.get(er.COT_HO_TEN)),
            "lop": lop, "khoi": khoi_cua_lop(lop),
            "mon": er.tach_mon(r.get(er.COT_MON)),
        })

    # tên hiển thị của từng môn (theo cách viết gặp đầu tiên)
    mon_trong_ds: dict[str, str] = {}
    for hs in ds_hoc_sinh:
        for m in hs["mon"]:
            mon_trong_ds.setdefault(er.khoa(m), m)

    if ds_hoc_sinh:
        with st.expander(
            f"📊 Thống kê: {len(ds_hoc_sinh)} học sinh · "
            f"{len({hs['lop'] for hs in ds_hoc_sinh})} lớp · {len(mon_trong_ds)} môn", expanded=False,
        ):
            dong_tk = [
                {"Lớp": hs["lop"], "Môn": mon_trong_ds[er.khoa(m)]}
                for hs in ds_hoc_sinh for m in hs["mon"]
            ]
            if dong_tk:
                bang_tk = pd.crosstab(
                    pd.DataFrame(dong_tk)["Lớp"], pd.DataFrame(dong_tk)["Môn"],
                    margins=True, margins_name="Tổng",
                )
                st.caption("Số học sinh đăng ký thi theo từng lớp × môn:")
                st.dataframe(bang_tk, use_container_width=True)
            else:
                st.caption("Chưa học sinh nào có cột Môn thi.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 2. Phòng thi
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 3. Môn thi
    # ------------------------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "3", "Môn thi & chế độ xếp phòng",
        "Mỗi môn thi tự lấy đúng các học sinh có đăng ký môn đó trong danh sách ở mục 1. "
        "<b>Lớp áp dụng</b> (không bắt buộc): điền nếu muốn giới hạn thêm theo lớp (VD "
        "<code>10A1,10A2</code>), hoặc dùng cho học sinh không ghi cột Môn thi. <b>Chế độ xếp</b>: "
        "\"Theo lớp\" giữ nguyên từng lớp (chỉ tách khi 1 lớp đông hơn sức chứa 1 phòng); "
        "\"Trộn theo khối\" xáo học sinh từ các lớp khác nhau ngồi xen kẽ nhau (hạn chế quay cóp).",
    )
    mon_da_khai_bao = {
        er.khoa(m) for m in st.session_state.exam_subjects["Môn thi"] if not er._o_trong(m)
    }
    mon_chua_co = [ten for k, ten in mon_trong_ds.items() if k not in mon_da_khai_bao]
    if mon_chua_co:
        mc1, mc2 = st.columns([3, 1])
        with mc1:
            st.info(
                f"Có {len(mon_chua_co)} môn trong danh sách học sinh chưa có ở bảng Môn thi: "
                + ", ".join(mon_chua_co)
            )
        with mc2:
            if st.button("➕ Thêm các môn này", use_container_width=True, key="them_mon_tu_ds"):
                them = pd.DataFrame([
                    {"Môn thi": m, "Lớp áp dụng (không bắt buộc)": "", "Ngày thi": "", "Ca thi": "Sáng",
                     "Chế độ xếp": "Trộn theo khối (xáo giữa các lớp)"}
                    for m in mon_chua_co
                ], columns=EXAM_SUBJECT_COLUMNS)
                st.session_state.exam_subjects = pd.concat(
                    [st.session_state.exam_subjects, them], ignore_index=True,
                )
                st.session_state.pop("editor_exam_subjects", None)
                st.rerun()

    excel_io_row("exam_subjects", "Mon_thi", transform=chuan_hoa_bang_mon_thi)
    st.session_state.exam_subjects = st.data_editor(
        st.session_state.exam_subjects, num_rows="dynamic", use_container_width=True,
        key="editor_exam_subjects",
        column_config={
            "Môn thi": st.column_config.TextColumn(required=True),
            "Lớp áp dụng (không bắt buộc)": st.column_config.TextColumn(
                help="Để trống = tất cả học sinh đăng ký môn này. Điền các lớp cách nhau dấu phẩy "
                     "để giới hạn, VD: 10A1,10A2",
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

    hien_ho_ten = st.checkbox(
        "Hiện họ tên trong danh sách phòng thi / thẻ báo danh (nếu file có họ tên). "
        "Sơ đồ chỗ ngồi luôn CHỈ hiện số báo danh.",
        value=False, key="exam_show_names",
    )
    xep_phong_btn = st.button("🪑 Xếp phòng thi cho tất cả môn", type="primary", use_container_width=True)

    if xep_phong_btn:
        loi_xep_phong, canh_bao = [], []
        ket_qua_moi = {}
        rooms_list_all = [
            {"ten_phong": str(r["Tên phòng"]), "suc_chua": int(r["Sức chứa"])}
            for _, r in st.session_state.exam_rooms.dropna(subset=["Tên phòng", "Sức chứa"]).iterrows()
        ]
        room_so_cot = {
            str(r["Tên phòng"]): int(r["Số cột bàn"]) if pd.notna(r.get("Số cột bàn")) else 4
            for _, r in st.session_state.exam_rooms.dropna(subset=["Tên phòng"]).iterrows()
        }
        if not rooms_list_all:
            loi_xep_phong.append("Chưa khai báo phòng thi nào ở mục 2.")
        if not ds_hoc_sinh:
            loi_xep_phong.append("Chưa có học sinh nào ở mục 1.")

        # Sinh SBD 1 LẦN cho toàn bộ danh sách (sắp theo khối, lớp) để mỗi
        # học sinh giữ nguyên 1 SBD ở mọi môn thi.
        thu_tu_sbd = sorted(range(len(ds_hoc_sinh)), key=lambda i: (ds_hoc_sinh[i]["khoi"], ds_hoc_sinh[i]["lop"]))
        co_sbd = er.sinh_sbd_tu_dong([ds_hoc_sinh[i] for i in thu_tu_sbd])
        hs_co_sbd = [None] * len(ds_hoc_sinh)
        for i, hs in zip(thu_tu_sbd, co_sbd):
            hs_co_sbd[i] = hs
        dem_sbd: dict[str, int] = {}
        for hs in hs_co_sbd:
            dem_sbd[hs["sbd"]] = dem_sbd.get(hs["sbd"], 0) + 1
        sbd_trung = [s for s, n in dem_sbd.items() if n > 1]
        if sbd_trung:
            loi_xep_phong.append(
                f"Có {len(sbd_trung)} SBD bị trùng giữa các học sinh: {', '.join(sbd_trung[:10])}"
                + (" ..." if len(sbd_trung) > 10 else "") + " — sửa lại ở mục 1."
            )

        subjects_df = st.session_state.exam_subjects.dropna(subset=["Môn thi"])
        subjects_df = subjects_df[subjects_df["Môn thi"].astype(str).str.strip() != ""]
        if subjects_df.empty:
            loi_xep_phong.append("Chưa khai báo môn thi nào ở mục 3.")

        lich_thi_cua_hs: dict[str, list] = {}  # sbd -> [(ngay, ca, mon)]
        if not loi_xep_phong:
            for _, mon in subjects_df.iterrows():
                ten_mon = str(mon["Môn thi"]).strip()
                ngay, ca = er._chuoi(mon.get("Ngày thi")), er._chuoi(mon.get("Ca thi"))
                if not ngay or not ca:
                    loi_xep_phong.append(f"Môn '{ten_mon}': chưa điền Ngày thi / Ca thi.")
                    continue
                lop_ap_dung = [
                    l.strip() for l in er._chuoi(mon.get("Lớp áp dụng (không bắt buộc)")).split(",") if l.strip()
                ]
                che_do = "tron_khoi" if "Trộn" in str(mon["Chế độ xếp"]) else "theo_lop"
                hs_dang_ky = [hs for hs in hs_co_sbd if er.hoc_sinh_thi_mon(hs, ten_mon, lop_ap_dung)]
                if not hs_dang_ky:
                    loi_xep_phong.append(
                        f"Môn '{ten_mon}': không có học sinh nào đăng ký môn này"
                        + (f" trong các lớp {lop_ap_dung}." if lop_ap_dung else ".")
                    )
                    continue
                for hs in hs_dang_ky:
                    lich_thi_cua_hs.setdefault(hs["sbd"], []).append((ngay, ca, ten_mon))

                ket_qua, thieu = er.xep_phong_thi(hs_dang_ky, rooms_list_all, che_do)
                for phong in ket_qua:
                    phong["so_cot"] = room_so_cot.get(phong["ten_phong"], 4)
                    phong["hoc_sinh_cho_ngoi"] = er.xao_tron_cho_ngoi(phong["hoc_sinh"])
                ket_qua_moi[ten_mon] = {
                    "rooms": ket_qua, "thieu": thieu, "ngay": ngay, "ca": ca,
                    "lop_ap_dung": lop_ap_dung, "so_hs": len(hs_dang_ky),
                }

        # cảnh báo 1 học sinh thi 2 môn trùng ngày + ca
        for sbd, lich in lich_thi_cua_hs.items():
            theo_ca: dict[tuple, list] = {}
            for ngay, ca, ten_mon in lich:
                theo_ca.setdefault((ngay, ca), []).append(ten_mon)
            for (ngay, ca), ds_mon in theo_ca.items():
                if len(ds_mon) > 1:
                    canh_bao.append(f"SBD {sbd}: thi {', '.join(ds_mon)} cùng ngày {ngay} ca {ca}.")

        for e in loi_xep_phong:
            st.error(e)
        if canh_bao:
            st.warning(
                f"⚠️ {len(canh_bao)} trường hợp học sinh bị trùng lịch thi (cùng ngày, cùng ca):\n\n"
                + "\n".join(f"- {c}" for c in canh_bao[:15])
                + ("\n- ..." if len(canh_bao) > 15 else "")
            )
        if ket_qua_moi:
            st.session_state.exam_results = ket_qua_moi
            st.session_state.exam_all_students = hs_co_sbd
            st.success(f"✅ Đã xếp phòng thi cho {len(ket_qua_moi)} môn.")

    if st.session_state.exam_results:
        st.divider()
        st.markdown('<div class="section-title"><h3>📋 Kết quả xếp phòng thi</h3></div>', unsafe_allow_html=True)

        # Bảng tổng hợp: mỗi học sinh 1 dòng, mỗi môn 1 cột = phòng thi
        phong_cua_hs: dict[str, dict] = {}
        for ten_mon, kq in st.session_state.exam_results.items():
            for phong in kq["rooms"]:
                for hs in phong["hoc_sinh"]:
                    phong_cua_hs.setdefault(hs["sbd"], {})[ten_mon] = phong["ten_phong"]
        tong_hop = []
        for hs in st.session_state.get("exam_all_students", []):
            if hs["sbd"] not in phong_cua_hs:
                continue
            dong = {"SBD": hs["sbd"]}
            if hien_ho_ten:
                dong["Họ và tên"] = hs.get("ho_ten", "")
            dong["Lớp"] = hs["lop"]
            for ten_mon in st.session_state.exam_results:
                dong[f"Phòng thi {ten_mon}"] = phong_cua_hs[hs["sbd"]].get(ten_mon, "")
            tong_hop.append(dong)
        if tong_hop:
            st.download_button(
                "📊 Xuất Excel tổng hợp: SBD + phòng thi từng môn của mỗi học sinh",
                data=df_to_excel_bytes(pd.DataFrame(tong_hop), "Tong_hop_SBD"),
                file_name="tong_hop_sbd_phong_thi.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="xls_tong_hop_sbd",
            )

        mon_chon = st.selectbox("Chọn môn thi để xem", options=list(st.session_state.exam_results.keys()))
        entry = st.session_state.exam_results[mon_chon]
        st.caption(
            f"📚 Môn: **{mon_chon}** · Số thí sinh: **{entry.get('so_hs', '')}** · "
            + (f"Giới hạn lớp: **{', '.join(entry['lop_ap_dung'])}** · " if entry["lop_ap_dung"] else "")
            + f"Ngày thi: {entry['ngay']} · Ca: {entry['ca']}"
        )

        if entry["thieu"]:
            st.warning(
                f"⚠️ Không đủ chỗ cho {len(entry['thieu'])} học sinh (hết phòng), SBD: "
                + ", ".join(hs["sbd"] for hs in entry["thieu"][:15])
                + (" ..." if len(entry["thieu"]) > 15 else "")
                + ". Vào mục 2 thêm phòng thi hoặc tăng sức chứa rồi xếp lại."
            )

        exp1, exp2, exp3 = st.columns([1, 1, 1])
        with exp1:
            pdf_bytes_exam = exam_rooms_to_pdf_bytes(
                mon_chon, entry["ngay"], entry["ca"], entry["rooms"], school_name=school_name,
                hien_ho_ten=hien_ho_ten,
            )
            st.download_button(
                "📄 Xuất PDF (danh sách + sơ đồ)", data=pdf_bytes_exam,
                file_name=f"phong_thi_{slugify(mon_chon)}.pdf", mime="application/pdf",
                type="primary", use_container_width=True, key=f"pdf_exam_{mon_chon}",
            )
        with exp2:
            xls_bytes_exam = exam_rooms_to_excel_bytes(
                mon_chon, entry["ngay"], entry["ca"], entry["rooms"], hien_ho_ten=hien_ho_ten,
            )
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
            room_tabs = st.tabs([f'{r["ten_phong"]} ({len(r["hoc_sinh"])})' for r in entry["rooms"]])
            for tab, r in zip(room_tabs, entry["rooms"]):
                with tab:
                    df_show = pd.DataFrame([
                        {"STT": i + 1, "SBD": hs["sbd"],
                         **({"Họ và tên": hs.get("ho_ten", "")} if hien_ho_ten else {}),
                         "Lớp": hs["lop"]}
                        for i, hs in enumerate(r["hoc_sinh"])
                    ])
                    st.dataframe(df_show, use_container_width=True, hide_index=True)

                    st.markdown(
                        '<div class="section-title" style="margin-top:18px;">'
                        '<h3>🪑 Sơ đồ chỗ ngồi (chỉ ghi số báo danh, xếp ngẫu nhiên)</h3></div>',
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
