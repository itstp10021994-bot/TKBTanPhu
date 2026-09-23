"""
Xếp phòng thi: chia học sinh đăng ký thi 1 môn vào các phòng thi theo sức
chứa, sinh số báo danh (SBD) nếu chưa có sẵn.

Độc lập hoàn toàn với bộ xếp thời khoá biểu (scheduler.py) — đây chỉ là
thuật toán chia đơn giản + round-robin để trộn lớp, không dùng CP-SAT.
"""

from __future__ import annotations

import random
import re
import unicodedata

import pandas as pd

# Cột chuẩn của bảng danh sách học sinh dự thi
COT_SBD = "SBD"
COT_HO_TEN = "Họ và tên (không bắt buộc)"
COT_LOP = "Lớp"
COT_MON = "Môn thi"
COT_CHUAN = [COT_SBD, COT_HO_TEN, COT_LOP, COT_MON]

# Ký tự ngăn cách các môn trong 1 ô, VD "Toán, Văn; Lý"
_TACH_MON = re.compile(r"[,;\n|]+")
# Giá trị đánh dấu "có thi môn này" ở file dạng mỗi môn 1 cột
_DANH_DAU_CO = {"x", "1", "co", "v", "yes", "y", "true", "dk", "dang_ky", "✓", "✔", "☑"}


def khoa(text) -> str:
    """Chuẩn hoá chuỗi để so khớp: bỏ dấu, chữ thường, gộp ký tự đặc biệt.
    VD 'Vật lí' -> 'vat_li', 'GDKT & PL' -> 'gdkt_pl'."""
    text = "" if text is None else str(text)
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _o_trong(v) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return str(v).strip().lower() in ("", "nan", "none", "nat")


def _chuoi(v) -> str:
    """Giá trị ô -> chuỗi gọn; số nguyên đọc từ Excel (VD 100001.0) giữ
    nguyên dạng '100001'."""
    if _o_trong(v):
        return ""
    if hasattr(v, "strftime"):  # ngày thi đọc từ Excel dạng ngày tháng
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def tach_mon(o_mon) -> list[str]:
    """'Toán, Ngữ văn; Vật lí' -> ['Toán', 'Ngữ văn', 'Vật lí'] (bỏ trùng)."""
    ket_qua, da_co = [], set()
    for m in _TACH_MON.split(_chuoi(o_mon)):
        m = m.strip()
        if m and khoa(m) not in da_co:
            da_co.add(khoa(m))
            ket_qua.append(m)
    return ket_qua


def khoi_tu_ten_lop(ten_lop: str) -> int:
    """'10A1' -> 10, '6 ESL' -> 6, không đoán được -> 0."""
    m = re.match(r"\s*(\d{1,2})", str(ten_lop or ""))
    return int(m.group(1)) if m else 0


def _nhan_dien_cot(ten_cot) -> str | None:
    k = khoa(ten_cot)
    if not k:
        return None
    if k in ("sbd", "so_bao_danh", "ma_hs", "ma_hoc_sinh", "ma_so", "ma_so_hs", "ma_so_bao_danh",
             "ma_dinh_danh", "mshs", "ma") or k.startswith(("sbd", "so_bao_danh", "ma_hs", "ma_hoc_sinh")):
        return COT_SBD
    if k.startswith(("ho_va_ten", "ho_ten", "hoten", "ten_hoc_sinh", "ten_hs", "ho_ten_hs")) or k == "ten":
        return COT_HO_TEN
    if k in ("lop", "ten_lop", "lop_hoc") or k.startswith("lop_"):
        return COT_LOP
    if k.startswith(("mon", "cac_mon", "to_hop")):
        return COT_MON
    if k in ("stt", "tt", "so_thu_tu"):
        return "__bo_qua__"
    return None


def chuan_hoa_danh_sach_hoc_sinh(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Đọc bảng học sinh upload lên (Excel/CSV) theo nhiều kiểu trình bày và
    đưa về 1 dòng / học sinh với 4 cột chuẩn COT_CHUAN.

    Hỗ trợ:
      1. Mỗi học sinh 1 dòng, cột 'Môn thi' ghi nhiều môn cách nhau dấu phẩy.
      2. Mỗi (học sinh, môn) 1 dòng — các dòng cùng SBD (hoặc cùng Họ tên +
         Lớp) được gộp lại thành 1 học sinh.
      3. Mỗi môn 1 cột (tiêu đề cột = tên môn), đánh dấu x / 1 / có vào ô
         nếu học sinh thi môn đó.
    Trả về (df_chuan, ghi_chu) — ghi_chu là các thông báo cho người dùng.
    """
    ghi_chu: list[str] = []
    if df is None or df.empty:
        return pd.DataFrame(columns=COT_CHUAN), ["File không có dòng dữ liệu nào."]

    df = df.dropna(how="all")
    anh_xa: dict[str, str] = {}
    cot_mon_rieng: list[str] = []
    ten_mon_cot: dict[str, str] = {}
    for cot in df.columns:
        loai = _nhan_dien_cot(cot)
        if loai == "__bo_qua__":
            continue
        if loai in (COT_SBD, COT_HO_TEN, COT_LOP):
            if loai not in anh_xa.values():
                anh_xa[cot] = loai
            continue
        gia_tri = {khoa(v) for v in df[cot] if not _o_trong(v)}
        if gia_tri and gia_tri <= _DANH_DAU_CO:
            # cột đánh dấu x cho 1 môn: "Toán" hoặc "Môn Toán" -> môn "Toán"
            cot_mon_rieng.append(cot)
            ten_mon_cot[cot] = re.sub(r"^\s*m[oôố]n\s+", "", str(cot).strip(), flags=re.IGNORECASE) or str(cot)
        elif loai == COT_MON and COT_MON not in anh_xa.values():
            anh_xa[cot] = loai

    if COT_LOP not in anh_xa.values():
        raise ValueError(
            "Không tìm thấy cột 'Lớp' trong file. Tiêu đề cột cần có: SBD (hoặc Mã HS), "
            "Lớp, Môn thi — hoặc mỗi môn 1 cột đánh dấu x."
        )
    if COT_MON not in anh_xa.values() and not cot_mon_rieng:
        ghi_chu.append(
            "⚠️ File không có cột 'Môn thi' (hoặc cột môn đánh dấu x) — học sinh sẽ thi theo "
            "'Lớp áp dụng' khai báo ở bảng Môn thi."
        )
    if cot_mon_rieng:
        ghi_chu.append(
            f"Nhận diện {len(cot_mon_rieng)} cột môn đánh dấu: "
            f"{', '.join(ten_mon_cot[c] for c in cot_mon_rieng)}."
        )

    nguoc = {v: k for k, v in anh_xa.items()}
    hoc_sinh: dict[tuple, dict] = {}
    thu_tu: list[tuple] = []
    for i, row in df.iterrows():
        sbd = _chuoi(row[nguoc[COT_SBD]]) if COT_SBD in nguoc else ""
        ho_ten = _chuoi(row[nguoc[COT_HO_TEN]]) if COT_HO_TEN in nguoc else ""
        lop = _chuoi(row[nguoc[COT_LOP]])
        if not lop and not sbd and not ho_ten:
            continue
        mon = tach_mon(row[nguoc[COT_MON]]) if COT_MON in nguoc else []
        mon += [ten_mon_cot[c] for c in cot_mon_rieng if not _o_trong(row[c])]

        # khoá gộp: SBD nếu có, không thì (Họ tên, Lớp); không có gì -> mỗi dòng 1 HS
        if sbd:
            k = ("sbd", sbd)
        elif ho_ten:
            k = ("ten", khoa(ho_ten), lop)
        else:
            k = ("dong", i)
        if k not in hoc_sinh:
            hoc_sinh[k] = {COT_SBD: sbd, COT_HO_TEN: ho_ten, COT_LOP: lop, "_mon": []}
            thu_tu.append(k)
        hs = hoc_sinh[k]
        if not hs[COT_LOP] and lop:
            hs[COT_LOP] = lop
        for m in mon:
            if khoa(m) not in {khoa(x) for x in hs["_mon"]}:
                hs["_mon"].append(m)

    rows = [
        {COT_SBD: hs[COT_SBD], COT_HO_TEN: hs[COT_HO_TEN], COT_LOP: hs[COT_LOP],
         COT_MON: ", ".join(hs["_mon"])}
        for hs in (hoc_sinh[k] for k in thu_tu)
    ]
    so_dong_goc = len(df)
    if len(rows) < so_dong_goc:
        ghi_chu.append(f"Đã gộp {so_dong_goc} dòng thành {len(rows)} học sinh (cùng SBD / cùng tên + lớp).")
    return pd.DataFrame(rows, columns=COT_CHUAN), ghi_chu


def hoc_sinh_thi_mon(hs: dict, ten_mon: str, lop_ap_dung: list[str]) -> bool:
    """Học sinh hs {'lop', 'mon': [..]} có thi môn ten_mon không?
    - Có ghi môn thi riêng -> thi nếu môn nằm trong danh sách đó.
    - Không ghi môn nào -> thi nếu lớp nằm trong 'Lớp áp dụng' của môn.
    - 'Lớp áp dụng' (nếu có điền) luôn dùng làm bộ lọc giới hạn thêm theo lớp.
    """
    lop_khoa = {khoa(l) for l in lop_ap_dung}
    if lop_khoa and khoa(hs["lop"]) not in lop_khoa:
        return False
    if hs.get("mon"):
        return khoa(ten_mon) in {khoa(m) for m in hs["mon"]}
    return bool(lop_khoa)


def sinh_sbd_tu_dong(danh_sach_hs: list[dict]) -> list[dict]:
    """Với mỗi học sinh chưa có 'ma_hs' (rỗng/None), sinh SBD dạng
    {khoi:02d}{stt:04d} — VD khối 10, học sinh thứ 7 của khối đó -> '100007'.
    Mỗi học sinh CẦN có sẵn khoá 'khoi' (int) — vì 1 môn thi giờ có thể áp
    dụng cho các lớp thuộc nhiều khối khác nhau, số đếm STT được đếm RIÊNG
    cho từng khối để SBD không bị lẫn lộn.
    Học sinh đã có sẵn 'sbd' (hoặc 'ma_hs') thì dùng luôn mã đó làm SBD.
    Trả về list mới (không sửa list gốc), mỗi phần tử có thêm khoá 'sbd'.
    """
    ket_qua = []
    dem_theo_khoi: dict[int, int] = {}
    for hs in danh_sach_hs:
        ma_hs = (hs.get("sbd") or hs.get("ma_hs") or "").strip()
        if ma_hs:
            sbd = ma_hs
        else:
            khoi = int(hs.get("khoi") or 0)
            dem_theo_khoi[khoi] = dem_theo_khoi.get(khoi, 0) + 1
            sbd = f"{khoi:02d}{dem_theo_khoi[khoi]:04d}"
        ket_qua.append({**hs, "sbd": sbd})
    return ket_qua


def sap_xep_thu_tu_hoc_sinh(danh_sach_hs: list[dict], che_do: str) -> list[dict]:
    """Sắp thứ tự học sinh trước khi chia vào phòng.

    - che_do == "theo_lop": giữ nguyên lớp liền nhau (ổn định theo lớp),
      trong cùng lớp giữ nguyên thứ tự đưa vào ban đầu.
    - che_do == "tron_khoi": trộn round-robin — lần lượt lấy 1 học sinh từ
      mỗi lớp xoay vòng, để 2 học sinh cùng lớp không ngồi cạnh nhau.
    """
    if che_do == "tron_khoi":
        theo_lop: dict[str, list[dict]] = {}
        for hs in danh_sach_hs:
            theo_lop.setdefault(hs["lop"], []).append(hs)
        con_lai = {lop: list(ds) for lop, ds in theo_lop.items()}
        thu_tu = []
        con_lop = list(con_lai.keys())
        while any(con_lai[lop] for lop in con_lop):
            for lop in con_lop:
                if con_lai[lop]:
                    thu_tu.append(con_lai[lop].pop(0))
        return thu_tu

    # "theo_lop" (mặc định): sort ổn định theo tên lớp, giữ thứ tự gốc trong lớp
    return sorted(danh_sach_hs, key=lambda hs: hs["lop"])


def chia_vao_phong(danh_sach_hs_theo_thu_tu: list[dict], danh_sach_phong: list[dict]):
    """Chia danh sách học sinh (đã sắp thứ tự) vào các phòng theo sức chứa,
    lấp đầy phòng này rồi mới sang phòng kế tiếp.

    danh_sach_phong: list[dict] mỗi phần tử có 'ten_phong', 'suc_chua'.

    Trả về (ket_qua, con_thieu):
    - ket_qua: list[dict] {"ten_phong", "hoc_sinh": [...]}
    - con_thieu: list[dict] học sinh KHÔNG xếp được vì hết chỗ (tổng sức
      chứa các phòng nhỏ hơn số học sinh) — rỗng nếu đủ chỗ.
    """
    ket_qua = []
    idx = 0
    tong_hs = len(danh_sach_hs_theo_thu_tu)
    for phong in danh_sach_phong:
        if idx >= tong_hs:
            break
        suc_chua = max(int(phong["suc_chua"]), 0)
        nhom = danh_sach_hs_theo_thu_tu[idx: idx + suc_chua]
        idx += len(nhom)
        if nhom:
            ket_qua.append({"ten_phong": phong["ten_phong"], "hoc_sinh": nhom})

    con_thieu = danh_sach_hs_theo_thu_tu[idx:] if idx < tong_hs else []
    return ket_qua, con_thieu


def xao_tron_cho_ngoi(hoc_sinh_trong_phong: list[dict]) -> list[dict]:
    """Trả về 1 bản SAO đã xáo trộn ngẫu nhiên thứ tự học sinh trong 1
    phòng — dùng riêng cho SƠ ĐỒ CHỖ NGỒI, không ảnh hưởng danh sách phòng
    thi gốc (danh sách vẫn giữ thứ tự ổn định để dễ dò tên/ký tên)."""
    ban_sao = list(hoc_sinh_trong_phong)
    random.shuffle(ban_sao)
    return ban_sao


def sap_xep_so_do_cho_ngoi(hoc_sinh_trong_phong: list[dict], so_cot: int) -> list[list]:
    """Chia danh sách học sinh ĐÃ Ở TRONG 1 PHÒNG thành lưới chỗ ngồi theo
    số cột bàn, xếp lần lượt trái → phải, hàng trên → hàng dưới (hàng đầu
    gần bảng/bục giảng nhất).

    Trả về list các hàng ghế; mỗi hàng là list các ô, mỗi ô là dict học
    sinh hoặc None nếu ô đó trống (phòng không lấp đầy hết lưới).
    """
    so_cot = max(int(so_cot), 1)
    hang_ghe = []
    for i in range(0, len(hoc_sinh_trong_phong), so_cot):
        nhom = list(hoc_sinh_trong_phong[i:i + so_cot])
        while len(nhom) < so_cot:
            nhom.append(None)
        hang_ghe.append(nhom)
    return hang_ghe


def xep_phong_thi(danh_sach_hs: list[dict], danh_sach_phong: list[dict], che_do: str):
    """Hàm tổng hợp: sinh SBD -> sắp thứ tự theo chế độ -> chia vào phòng.

    danh_sach_hs: list[dict] mỗi phần tử {"sbd": str|"", "ho_ten": str,
    "lop": str, "khoi": int} — bắt buộc có "khoi" để sinh SBD đúng khối.
    Nên sinh SBD 1 lần cho TOÀN BỘ danh sách trước (sinh_sbd_tu_dong) để 1
    học sinh giữ nguyên 1 SBD ở mọi môn thi; ở đây chỉ sinh cho HS còn thiếu.
    danh_sach_phong: list[dict] {"ten_phong": str, "suc_chua": int}
    che_do: "theo_lop" | "tron_khoi"

    Trả về (ket_qua, con_thieu) — xem chia_vao_phong().
    Mỗi học sinh trong kết quả có thêm 'sbd' và giữ nguyên 'lop'.
    """
    co_sbd = sinh_sbd_tu_dong(danh_sach_hs)
    da_sap = sap_xep_thu_tu_hoc_sinh(co_sbd, che_do)
    return chia_vao_phong(da_sap, danh_sach_phong)
