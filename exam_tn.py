"""
Xếp phòng thi TỐT NGHIỆP THPT theo môn tự chọn (khối 12).

Mỗi học sinh thi 2 môn tự chọn (VD "Lý - Anh"). Cách xếp:
  1. Đếm số học sinh thi từng môn trên toàn khối. Với mỗi học sinh, môn có
     NHIỀU học sinh thi hơn là MÔN 1, môn còn lại là MÔN 2 (cùng số thì theo
     tên môn) -> "Lý - Anh" và "Anh - Lý" là cùng 1 cặp.
  2. Gom học sinh theo môn 1. Trong mỗi nhóm môn 1, học sinh cùng cặp
     (môn 1, môn 2) được xếp kín từng phòng trước (phòng thuần 1 cặp môn);
     phần lẻ của các cặp được ghép tiếp vào phòng chung môn 1, cặp đông
     trước -> số phòng ít nhất và nhiều phòng thi chung cả môn 1 lẫn môn 2.
  3. MỖI PHÒNG CHỈ CÓ 1 MÔN 1 (bắt buộc) — chỉ môn 2 được ghép. Nhóm môn 1 ít
     học sinh vẫn có phòng riêng.
  4. SBD đánh liên tục theo thứ tự phòng.

Độc lập với Streamlit để dễ kiểm thử.
"""

from __future__ import annotations

import io
import re
import time
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

COT_MA, COT_TEN, COT_LOP, COT_MON = "Mã HS", "Họ và tên", "Lớp", "Môn thi"
COT_CHUAN = [COT_MA, COT_TEN, COT_LOP, COT_MON]

# Tên viết tắt / cách ghi thường gặp -> tên môn chuẩn
_TEN_MON = {
    "ly": "Vật lí", "vatly": "Vật lí", "vatli": "Vật lí", "li": "Vật lí",
    "anh": "Tiếng Anh", "tienganh": "Tiếng Anh", "av": "Tiếng Anh", "nn": "Tiếng Anh", "ngoaingu": "Tiếng Anh",
    "dia": "Địa lí", "diali": "Địa lí", "dialy": "Địa lí",
    "su": "Lịch sử", "lichsu": "Lịch sử",
    "hoa": "Hóa học", "hoahoc": "Hóa học",
    "sinh": "Sinh học", "sinhhoc": "Sinh học",
    "gdktpl": "GDKT&PL", "gdkt": "GDKT&PL", "kinhtephapluat": "GDKT&PL", "giaoduckinhtevaphapluat": "GDKT&PL",
    "tin": "Tin học", "tinhoc": "Tin học",
    "congnghe": "Công nghệ", "cn": "Công nghệ",
    "cncn": "Công nghệ công nghiệp", "congnghecongnghiep": "Công nghệ công nghiệp",
    "cnnn": "Công nghệ nông nghiệp", "congnghenongnghiep": "Công nghệ nông nghiệp",
    "phap": "Tiếng Pháp", "tiengphap": "Tiếng Pháp", "nhat": "Tiếng Nhật", "tiengnhat": "Tiếng Nhật",
    "trung": "Tiếng Trung", "tiengtrung": "Tiếng Trung", "han": "Tiếng Hàn", "tienghan": "Tiếng Hàn",
}
_TACH = re.compile(r"\s*[-–—,;+/|&]\s*|\s+và\s+")


def khoa(text) -> str:
    t = str(text or "").replace("đ", "d").replace("Đ", "D")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _o_trong(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip().lower() in ("", "nan", "none")


def chuan_mon(ten: str) -> str:
    return _TEN_MON.get(khoa(ten), " ".join(str(ten).split()))


def tach_mon(o) -> list[str]:
    """'Lý - Anh ' -> ['Vật lí', 'Tiếng Anh'] ; 'GDKTPL-Địa' -> ['GDKT&PL', 'Địa lí']."""
    if _o_trong(o):
        return []
    text = str(o).replace("GDKT&PL", "GDKTPL").replace("GDKT-PL", "GDKTPL")
    ds = []
    for p in _TACH.split(text):
        if p.strip():
            m = chuan_mon(p)
            if m not in ds:
                ds.append(m)
    return ds


def _tim_cot(cot: list[str], mau: list[str], tranh: tuple = ()) -> str | None:
    for m in mau:
        for c in cot:
            k = khoa(c)
            if m in k and not any(t in k for t in tranh):
                return c
    return None


def doc_danh_sach(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Bảng học sinh upload lên (tự tìm dòng tiêu đề và các cột) -> 4 cột chuẩn."""
    ghi_chu = []
    df = df.dropna(how="all").dropna(axis=1, how="all")
    # dòng tiêu đề có thể nằm dưới vài dòng trống / tiêu đề trường
    if not _tim_cot([str(c) for c in df.columns], ["hovaten", "hoten"]):
        for i in range(min(len(df), 15)):
            hang = [str(v) for v in df.iloc[i].tolist()]
            if _tim_cot(hang, ["hovaten", "hoten"]):
                df = df.iloc[i + 1:].copy()
                df.columns = [" ".join(h.split()) for h in hang]
                break
    cot = [str(c) for c in df.columns]
    c_mon = _tim_cot(cot, ["monthitn", "monthitotnghiep", "thitn", "thitotnghiep", "monthi", "monduthi"])
    c_lop = _tim_cot(cot, ["lop"], tranh=("tuchon",))
    c_ten = _tim_cot(cot, ["hovaten", "hoten", "tenhocsinh"])
    c_ma = _tim_cot(cot, ["mavnedu", "mahocsinh", "mahs", "madinhdanh", "sbd", "mshs", "ma"], tranh=("mon",))
    if not c_mon or not c_lop:
        raise ValueError("Không tìm thấy cột 'Lớp' và cột 'Môn thi TN' (VD: Lý - Anh) trong file.")
    ra = pd.DataFrame({
        COT_MA: df[c_ma].map(lambda v: "" if _o_trong(v) else str(v).strip()) if c_ma else "",
        COT_TEN: df[c_ten].map(lambda v: "" if _o_trong(v) else " ".join(str(v).split())) if c_ten else "",
        COT_LOP: df[c_lop].map(lambda v: "" if _o_trong(v) else str(v).strip()),
        COT_MON: df[c_mon].map(lambda v: ", ".join(tach_mon(v))),
    })
    ra = ra[(ra[COT_LOP] != "") | (ra[COT_TEN] != "")].reset_index(drop=True)
    ghi_chu.append(f"Cột dùng: Lớp = '{c_lop}', Họ tên = '{c_ten}', Mã = '{c_ma}', Môn thi = '{c_mon}'.")
    thieu = int((ra[COT_MON] == "").sum())
    if thieu:
        ghi_chu.append(f"⚠️ {thieu} học sinh chưa có môn thi — sẽ không được xếp phòng.")
    return ra, ghi_chu


COT_TEN_PHONG, COT_SUC_CHUA = "Tên phòng", "Sức chứa"
COT_UU_TIEN = "Ưu tiên"   # Cao / Bình thường / Thấp: phòng ưu tiên cao dùng trước, xếp đông; thấp xếp ít / không dùng
MUC_UU_TIEN = ["Cao", "Bình thường", "Thấp"]


def muc_uu_tien(v) -> int:
    """'Cao'/1 -> 0, 'Thấp'/3 -> 2, còn lại (trống, 'Bình thường', 2) -> 1."""
    k = khoa(str(v)) if not _o_trong(v) else ""
    if k in ("cao", "1", "10", "uutien", "uutiencao") or k.startswith("cao"):
        return 0
    if k in ("thap", "3", "30") or k.startswith("thap"):
        return 2
    return 1


def chia_si_so(phong: list[tuple[int, int]], n: int) -> list[int]:
    """phong: [(sức chứa, mức ưu tiên 0/1/2)] -> sĩ số từng phòng. Mức ưu tiên cao xếp KÍN trước; trong cùng
    1 mức chia đều (phòng nhỏ tính trước, không vượt sức chứa); mức thấp chỉ nhận phần còn lại (có thể 0)."""
    si_so, con = [0] * len(phong), int(n)
    for muc in sorted({m for _, m in phong}):
        nhom = [j for j, (_, m) in enumerate(phong) if m == muc]
        if con >= sum(phong[j][0] for j in nhom):
            for j in nhom:
                si_so[j] = phong[j][0]
            con -= sum(phong[j][0] for j in nhom)
            continue
        for k, j in enumerate(sorted(nhom, key=lambda j: (phong[j][0], j))):
            si_so[j] = min(phong[j][0], -(-con // (len(nhom) - k)))
            con -= si_so[j]
        con = 0
    return si_so


def doc_danh_sach_phong(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """File danh sách phòng (tự tìm dòng tiêu đề) -> 2 cột: Tên phòng, Sức chứa."""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    mau_ten, mau_so = ["tenphong", "phongthi", "phong", "ten"], ["succhua", "soluong", "socho", "siso", "sl", "sohs"]
    if not (_tim_cot([str(c) for c in df.columns], mau_ten, tranh=("succhua",))
            and _tim_cot([str(c) for c in df.columns], mau_so)):
        for i in range(min(len(df), 15)):
            hang = [str(v) for v in df.iloc[i].tolist()]
            if _tim_cot(hang, mau_so) and _tim_cot(hang, mau_ten, tranh=("succhua",)):
                df = df.iloc[i + 1:].copy()
                df.columns = [" ".join(h.split()) for h in hang]
                break
    cot = [str(c) for c in df.columns]
    c_so = _tim_cot(cot, mau_so)
    c_ten = _tim_cot([c for c in cot if c != c_so], mau_ten)
    if not c_ten or not c_so:
        raise ValueError("Không tìm thấy cột 'Tên phòng' và cột 'Sức chứa' (hoặc 'Số lượng') trong file.")
    c_ut = _tim_cot([c for c in cot if c not in (c_so, c_ten)], ["uutien", "mucuutien", "thutu"])
    ra = pd.DataFrame({
        COT_TEN_PHONG: df[c_ten].map(lambda v: "" if _o_trong(v) else " ".join(str(v).split())),
        COT_SUC_CHUA: pd.to_numeric(df[c_so], errors="coerce"),
        COT_UU_TIEN: (df[c_ut].map(lambda v: MUC_UU_TIEN[muc_uu_tien(v)]) if c_ut else MUC_UU_TIEN[1]),
    })
    ra = ra[ra[COT_TEN_PHONG] != ""]
    loi = ra[ra[COT_SUC_CHUA].isna() | (ra[COT_SUC_CHUA] <= 0)]
    ra = ra.drop(loi.index)
    ra[COT_SUC_CHUA] = ra[COT_SUC_CHUA].astype(int)
    ghi_chu = [f"Cột dùng: Tên phòng = '{c_ten}', Sức chứa = '{c_so}'."]
    if len(loi):
        ghi_chu.append(f"⚠️ Bỏ {len(loi)} phòng không có sức chứa hợp lệ: {', '.join(loi[COT_TEN_PHONG])}.")
    return ra.reset_index(drop=True), ghi_chu


def uu_tien_tu_bang(df: pd.DataFrame | None) -> dict:
    """Bảng phòng -> {tên phòng: mức ưu tiên 0/1/2} (thiếu cột -> rỗng = mọi phòng bình thường)."""
    if df is None or df.empty or COT_UU_TIEN not in df.columns:
        return {}
    return {" ".join(str(r[COT_TEN_PHONG]).split()): muc_uu_tien(r[COT_UU_TIEN])
            for _, r in df.iterrows() if not _o_trong(r.get(COT_TEN_PHONG))}


def _sap_uu_tien(phong_thi, uu_tien_phong):
    """Danh sách phòng xếp lại: ưu tiên cao trước (giữ thứ tự trong cùng mức)."""
    if not phong_thi or not uu_tien_phong:
        return list(phong_thi or [])
    return sorted(phong_thi, key=lambda p: uu_tien_phong.get(p[0], 1))


def phong_tu_bang(df: pd.DataFrame | None) -> list[tuple[str, int]]:
    """Bảng phòng (đã sửa trên app) -> [(tên, sức chứa)] hợp lệ, giữ thứ tự."""
    if df is None or df.empty:
        return []
    ra = []
    for _, r in df.iterrows():
        ten, so = r.get(COT_TEN_PHONG), pd.to_numeric(r.get(COT_SUC_CHUA), errors="coerce")
        if not _o_trong(ten) and pd.notna(so) and so > 0:
            ra.append((" ".join(str(ten).split()), int(so)))
    return ra


def _xep_vao_phong(nhom_le: list[list], cho: list[int]) -> list[list]:
    """Xếp các nhóm (mỗi nhóm cùng cặp môn) vào các phòng có sức chứa `cho`: nhóm lớn vào trước, nhóm vừa
    chỗ trống thì đặt NGUYÊN vào phòng vừa khít nhất; nhóm không vừa chỗ nào mới bị tách, phần tách vào
    phòng còn trống nhiều nhất -> mỗi phòng ít cặp môn nhất có thể."""
    phong = [[] for _ in cho]
    for g in sorted(nhom_le, key=lambda g: -len(g)):
        vua = [i for i in range(len(cho)) if cho[i] - len(phong[i]) >= len(g)]
        if vua:
            phong[min(vua, key=lambda i: cho[i] - len(phong[i]) - len(g))].extend(g)
            continue
        con = list(g)
        while con:
            i = max(range(len(cho)), key=lambda i: cho[i] - len(phong[i]))
            trong = cho[i] - len(phong[i])
            phong[i].extend(con[:trong]); con = con[trong:]
    return phong


UU_TIEN_MON, UU_TIEN_PHONG = "mon", "phong"
KHONG_KHA_THI = "INFEASIBLE"   # bộ giải chứng minh không có lời giải (khác với hết giờ)


def _toi_uu_theo_phong(hs: list[dict], hang: dict, phong_ds: list[tuple], suc_chua: int, co_ds_phong: bool,
                       gioi_han_giay: float = 10.0, uu_tien: str = UU_TIEN_PHONG, max_mon2: int = 2,
                       max_mon1: int = 1, huong: dict | None = None, khong_tach_cap: bool = False,
                       max_mon_ca: int = 0, max_cung_lop: int = 0, si_so_min: int = 0,
                       uu_tien_phong: dict | None = None):
    """Xếp đến TỪNG PHÒNG bằng OR-Tools CP-SAT. Mỗi phòng thuộc 1 "mẫu" (môn thi số 1 ⊆ A, môn thi số 2 ⊆ S):
    |A| <= max_mon1, |S| <= max_mon2. Chọn môn thi số 1 của từng em (hoặc theo `huong` = {frozenset(cặp): môn 1}
    cố định) và số phòng mỗi mẫu/sức chứa, ưu tiên (giảm dần):
      "phong": [tự thêm phòng] → ít phòng → ít môn thi cả 2 lần → ít môn ở ca đông môn hơn → trộn lớp
               → ít phòng ghép 2 môn 1 → ít HS lệch → ít chỗ trống
      "mon":   [tự thêm phòng] → ít môn thi cả 2 lần → ít môn ở ca đông môn hơn → ít HS lệch → ít phòng
               → ít phòng ghép → ít chỗ trống
    khong_tach_cap=True: cả cặp môn cùng 1 hướng (để điền được vào bảng tự chọn).
    Trộn lớp: cực tiểu số em CÙNG LỚP nhiều nhất trong 1 phòng (sau số phòng / số môn mỗi ca);
    max_cung_lop > 0: thêm ràng buộc cứng mỗi phòng tối đa chừng ấy em cùng lớp.
    -> ([(tên | None, sức chứa, [hs])], phòng danh sách không dùng, số phòng tự thêm) | None. Gán h["mon1"], h["mon2"]."""
    from itertools import combinations
    from ortools.sat.python import cp_model

    def _k(h):
        return tuple(sorted(h["mon"], key=lambda m: hang[m])[:2])
    nhom = defaultdict(list)
    for h in hs:
        nhom[_k(h)].append(h)
    # theo vần ABC (không theo lớp) -> khi 1 cặp môn chia 2 hướng / nhiều mẫu phòng, các lớp được trộn đều
    cap = {k: sorted(v, key=lambda h: (khoa_ten_vn(h["ten"]), h["lop"])) for k, v in nhom.items() if len(k) == 2}
    don = {k[0]: v for k, v in nhom.items() if len(k) == 1}
    mon = sorted({m for h in hs for m in h["mon"]}, key=lambda m: hang[m])
    huong = huong or {}
    cho_phep = {}   # (cặp, môn thi số 1) có được không
    for p in cap:
        chon = huong.get(frozenset(p))
        for x in p:
            cho_phep[(p, x)] = chon is None or chon == x
    ban = defaultdict(set)   # môn thi số 1 -> các môn thi số 2 có thể
    for p in cap:
        for x in p:
            if cho_phep[(p, x)]:
                ban[x].add(p[1] if x == p[0] else p[0])
    mau = []
    nhom_A = [(a,) for a in mon] + (list(combinations(mon, 2)) if max_mon1 >= 2 else [])
    for A in nhom_A:
        if not all(ban[a] or a in don for a in A):
            continue
        doi = sorted(set().union(*(ban[a] for a in A)), key=lambda m: hang[m])
        # chỉ giữ mẫu có ĐỦ max_mon2 môn 2 (mẫu ít môn hơn bị mẫu chứa nó bao trùm -> thừa)
        for S in combinations(doi, min(max_mon2, len(doi))):
            if len(A) == 2 and not all(a in don or ban[a] & set(S) for a in A):
                continue
            mau.append((A, S))
    n = len(hs)
    them = -(-n // suc_chua) + len(mon)
    kho = list(phong_ds) + [(None, suc_chua)] * them
    loai = defaultdict(list)   # (sức chứa, tự thêm?, mức ưu tiên) -> chỉ số phòng
    uu = uu_tien_phong or {}
    for r, (t, c) in enumerate(kho):
        loai[(c, t is None, 2 if t is None else uu.get(t, 1))].append(r)

    m = cp_model.CpModel()
    y = {}
    for p, ds in cap.items():
        if not cho_phep[(p, p[1])]:
            y[p] = len(ds)
        elif not cho_phep[(p, p[0])]:
            y[p] = 0
        elif khong_tach_cap:
            t = m.NewBoolVar("")
            y[p] = len(ds) * t
        else:
            y[p] = m.NewIntVar(0, len(ds), "")
    f = defaultdict(list)   # (cặp, môn 1) -> [(mẫu, biến)]
    g = defaultdict(list)   # môn (HS 1 môn) -> [(mẫu, biến)]
    vao = defaultdict(list)   # mẫu -> biến số HS
    for i, (A, S) in enumerate(mau):
        for p, ds in cap.items():
            for x in p:
                khac = p[1] if x == p[0] else p[0]
                if cho_phep[(p, x)] and x in A and khac in S:
                    v = m.NewIntVar(0, len(ds), "")
                    f[(p, x)].append((i, v)); vao[i].append(v)
        for a in A:
            if a in don:
                v = m.NewIntVar(0, len(don[a]), "")
                g[a].append((i, v)); vao[i].append(v)
    for p, ds in cap.items():
        m.Add(sum(v for _, v in f[(p, p[0])]) == y[p])
        m.Add(sum(v for _, v in f[(p, p[1])]) == len(ds) - y[p])
    for a, ds in don.items():
        m.Add(sum(v for _, v in g[a]) == len(ds))
    r = {(i, k): m.NewIntVar(0, len(rs), "") for i in range(len(mau)) for k, rs in loai.items()}
    fc = {}   # (cặp, môn 1, lớp, mẫu) -> số HS
    cung_lop = 0   # số em cùng lớp nhiều nhất trong 1 phòng (cực tiểu sau các mục tiêu chính)
    if True:
        L = int(max_cung_lop) if max_cung_lop and int(max_cung_lop) > 0 else max(k[0] for k in loai)
        lop_cap = {p: Counter(h["lop"] for h in ds) for p, ds in cap.items()}
        lop_don = {a: Counter(h["lop"] for h in ds) for a, ds in don.items()}
        theo_lop = defaultdict(list)   # (mẫu, lớp) -> biến
        for p in cap:
            for x in p:
                for i, v in f[(p, x)]:
                    vs = []
                    for c, sl in lop_cap[p].items():
                        fc[(p, x, c, i)] = w = m.NewIntVar(0, sl, "")
                        vs.append(w); theo_lop[(i, c)].append(w)
                    m.Add(sum(vs) == v)
            for c, sl in lop_cap[p].items():
                m.Add(sum(w for (pp, _, cc, _), w in fc.items() if pp == p and cc == c) == sl)
        for a in don:
            for i, v in g[a]:
                vs = []
                for c, sl in lop_don[a].items():
                    fc[(a, a, c, i)] = w = m.NewIntVar(0, sl, "")
                    vs.append(w); theo_lop[(i, c)].append(w)
                m.Add(sum(vs) == v)
            for c, sl in lop_don[a].items():
                m.Add(sum(w for (pp, _, cc, _), w in fc.items() if pp == a and cc == c) == sl)
        # mỗi phòng của mẫu i có tối đa cung_lop em lớp c:  Σ(lớp c vào mẫu i) <= cung_lop × số phòng mẫu i
        cung_lop = m.NewIntVar(1, L, "")
        tong_phong = sum(len(rs) for rs in loai.values())
        for i in sorted({i for (i, _) in theo_lop}):
            so_i = m.NewIntVar(0, tong_phong, "")
            m.Add(so_i == sum(r[(i, k)] for k in loai))
            tran = m.NewIntVar(0, L * tong_phong, "")
            m.AddMultiplicationEquality(tran, [cung_lop, so_i])
            for c in sorted({c for (ii, c) in theo_lop if ii == i}):
                m.Add(sum(theo_lop[(i, c)]) <= tran)
    for i in range(len(mau)):
        m.Add(sum(vao[i]) <= sum(k[0] * r[(i, k)] for k in loai))
        if si_so_min and int(si_so_min) > 0:   # không có phòng quá ít học sinh (chia đều trong các phòng cùng mẫu)
            m.Add(sum(vao[i]) >= int(si_so_min) * sum(r[(i, k)] for k in loai))
    for k, rs in loai.items():
        m.Add(sum(r[(i, k)] for i in range(len(mau))) <= len(rs))
    tong = Counter(x for h in hs for x in _k(h))
    co, lech, co1, co2 = [], [], [], []
    for a in mon:
        n1 = sum(y[p] for p in cap if p[0] == a) + sum(len(cap[p]) - y[p] for p in cap if p[1] == a) \
            + len(don.get(a, []))
        c1, c2, tren = m.NewBoolVar(""), m.NewBoolVar(""), m.NewBoolVar("")
        m.Add(n1 <= tong[a] * c1)
        m.Add(tong[a] - n1 <= tong[a] * c2)
        l = m.NewIntVar(0, tong[a], "")
        m.Add(l >= n1 - tong[a] * tren)
        m.Add(l >= tong[a] - n1 - tong[a] * (1 - tren))
        co += [c1, c2]; co1.append(c1); co2.append(c2); lech.append(l)
    so_phong = sum(r.values())
    tu_them = sum(v for (i, k), v in r.items() if k[1])
    ghep = sum(v for (i, k), v in r.items() if len(mau[i][0]) > 1)
    cho = sum(k[0] * v for (i, k), v in r.items())
    tach, hs_lech = sum(co), sum(lech)
    # số môn của ca đông môn hơn (càng nhỏ càng cân bằng 2 ca: VD ca 1 có 5 môn, ca 2 có 5 môn)
    mon_ca_max = m.NewIntVar(0, len(mon), "")
    m.Add(mon_ca_max >= sum(co1))
    m.Add(mon_ca_max >= sum(co2))
    if max_mon_ca and int(max_mon_ca) > 0:   # ràng buộc cứng: mỗi ca tối đa N môn
        m.Add(mon_ca_max <= int(max_mon_ca))
    phong_uu = sum(k[2] * v for (i, k), v in r.items())   # dùng phòng ưu tiên cao trước
    bac = ([so_phong, tach, mon_ca_max, cung_lop, ghep, hs_lech, phong_uu, cho] if uu_tien == UU_TIEN_PHONG
           else [tach, mon_ca_max, hs_lech, so_phong, cung_lop, ghep, phong_uu, cho])
    if co_ds_phong:
        bac.insert(0, tu_them)
    bien = [v for v in y.values() if not isinstance(v, int) and hasattr(v, "Index")] + list(r.values())
    giai = None
    het_gio = time.monotonic() + max(float(gioi_han_giay), 2.0)   # giới hạn THỜI GIAN THỰC cho cả lần giải
    for so_bac, muc_tieu in enumerate(bac):   # giải lần lượt từng bậc ưu tiên; seed cố định -> kết quả tất định
        m.Minimize(muc_tieu)
        sv = cp_model.CpSolver()
        # 1 luồng: máy chủ Streamlit miễn phí chỉ ~2 nhân CPU, nhiều luồng sẽ bị giới hạn CPU (throttle);
        # thử nghiệm: kết quả gần như nhau mà tốn CPU ít hơn 3–4 lần
        sv.parameters.num_workers = 1
        sv.parameters.random_seed = 2026
        sv.parameters.max_deterministic_time = max(1.0, gioi_han_giay / len(bac))
        con_lai = het_gio - time.monotonic()
        if giai is not None and con_lai <= 0.2:
            break   # hết giờ: giữ kết quả các bậc đã giải
        # bậc đầu (tìm phương án khả thi) được nhiều thời gian hơn; máy chậm vẫn không treo lâu
        sv.parameters.max_time_in_seconds = max(0.5, con_lai * (0.4 if so_bac == 0 else 1 / (len(bac) - so_bac)))
        st = sv.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if giai is None:
                return KHONG_KHA_THI if st == cp_model.INFEASIBLE else None
            break
        giai = sv
        m.ClearHints()
        for v in bien:
            m.AddHint(v, sv.Value(v))
        m.Add(muc_tieu <= int(round(sv.ObjectiveValue())))
    gt = lambda v: v if isinstance(v, int) else giai.Value(v)   # noqa: E731

    # gán môn thi số 1 và mẫu phòng cho từng học sinh
    hs_mau = defaultdict(list)
    if fc:   # có giới hạn số em cùng lớp: chia theo từng lớp
        for p, ds in list(cap.items()) + [((a,), ds) for a, ds in don.items()]:
            khoa_p = p if len(p) == 2 else p[0]
            for c in sorted({h["lop"] for h in ds}):
                con = [h for h in ds if h["lop"] == c]
                for x in (p if len(p) == 2 else (p[0],)):
                    for (pp, xx, cc, i), w in fc.items():
                        if pp == khoa_p and xx == x and cc == c:
                            so = giai.Value(w)
                            for h in con[:so]:
                                h["mon1"] = x
                                h["mon2"] = " + ".join(t for t in sorted(h["mon"], key=lambda t: hang[t]) if t != x)
                            hs_mau[i] += con[:so]; con = con[so:]
    for p, ds in ([] if fc else cap.items()):
        k1 = gt(y[p])
        for x, phan in ((p[0], ds[:k1]), (p[1], ds[k1:])):
            vt = 0
            for i, v in f[(p, x)]:
                so = giai.Value(v)
                hs_mau[i] += phan[vt:vt + so]; vt += so
            for h in phan:
                h["mon1"] = x
                h["mon2"] = " + ".join(t for t in sorted(h["mon"], key=lambda t: hang[t]) if t != x)
    for a, ds in ([] if fc else don.items()):
        vt = 0
        for i, v in g[a]:
            so = giai.Value(v)
            hs_mau[i] += ds[vt:vt + so]; vt += so
    # cấp phòng thật: mẫu có môn 1 đông trước lấy phòng đầu danh sách
    con = {k: list(rs) for k, rs in loai.items()}
    phong_mau = []
    for i in sorted(range(len(mau)), key=lambda i: (tuple(hang[a] for a in mau[i][0]), -len(hs_mau[i]), i)):
        rs = []
        for k in loai:
            so = giai.Value(r[(i, k)])
            rs += con[k][:so]; con[k] = con[k][so:]
        if rs and hs_mau[i]:
            phong_mau.append((i, sorted(rs)))
    phong, dung, mau_phong = [], set(), []
    for i, rs in phong_mau:
        ds = sorted(hs_mau[i], key=lambda h: (h["lop"], khoa_ten_vn(h["ten"])))
        # chia đều trong cùng mức ưu tiên; phòng ưu tiên cao xếp kín trước
        si_so = dict(zip(rs, chia_si_so([(kho[rr][1], 2 if kho[rr][0] is None else uu.get(kho[rr][0], 1))
                                          for rr in rs], len(ds))))
        # XÁO TRỘN LỚP: chia lần lượt (vòng tròn) từng em, đã sắp theo lớp, vào các phòng cùng mẫu
        # -> mỗi lớp rải đều ra các phòng, không dồn 1 lớp vào 1 phòng (mọi phòng cùng mẫu đều đúng ràng buộc môn)
        rs = [rr for rr in rs if si_so[rr]]
        noi = {rr: [] for rr in rs}
        j = 0
        for h in ds:
            while len(noi[rs[j % len(rs)]]) >= si_so[rs[j % len(rs)]]:
                j += 1
            noi[rs[j % len(rs)]].append(h); j += 1
        for rr in rs:
            phong.append((kho[rr][0], kho[rr][1], noi[rr])); dung.add(rr); mau_phong.append(mau[i])
    phong = _tron_lop(phong, mau_phong, _k)
    if uu:   # các phòng CÙNG sức chứa: phòng ưu tiên cao nhận nhóm đông hơn (chỉ đổi tên phòng, ràng buộc giữ nguyên)
        theo_cho = defaultdict(list)
        for j, (t, c, _) in enumerate(phong):
            if t is not None:
                theo_cho[c].append(j)
        for c, js in theo_cho.items():
            ten = sorted((phong[j][0] for j in js), key=lambda t: (uu.get(t, 1), [x for x, _ in phong_ds].index(t)))
            for t, j in zip(ten, sorted(js, key=lambda j: (-len(phong[j][2]), j))):
                phong[j] = (t, c, phong[j][2])
    phong_trong = [kho[i] for i in range(len(phong_ds)) if i not in dung]
    return phong, phong_trong, sum(1 for i in dung if kho[i][0] is None)


def _tron_lop(phong: list, mau_phong: list, _k) -> list:
    """Đổi chỗ học sinh giữa các phòng (giữ nguyên sĩ số và ràng buộc môn của từng phòng) để học sinh MỘT LỚP
    không dồn vào 1 phòng: cực tiểu số em cùng lớp nhiều nhất trong 1 phòng, rồi rải đều (tổng bình phương)."""
    from ortools.sat.python import cp_model

    nhom = defaultdict(list)   # (lớp, môn 1, môn còn lại) -> HS
    for _, _, ds in phong:
        for h in ds:
            khac = tuple(t for t in _k(h) if t != h["mon1"])
            nhom[(h["lop"], h["mon1"], khac)].append(h)
    m = cp_model.CpModel()
    x = {}
    for g, ds in nhom.items():
        for r, (A, S) in enumerate(mau_phong):
            if g[1] in A and all(t in S for t in g[2]):
                x[(g, r)] = m.NewIntVar(0, min(len(ds), phong[r][1]), "")
        m.Add(sum(v for (gg, _), v in x.items() if gg == g) == len(ds))
    for r, (_, _, ds) in enumerate(phong):
        m.Add(sum(v for (_, rr), v in x.items() if rr == r) == len(ds))
    lop = sorted({g[0] for g in nhom})
    dem = {}
    for c in lop:
        for r in range(len(phong)):
            vs = [v for (g, rr), v in x.items() if rr == r and g[0] == c]
            if vs:
                d = m.NewIntVar(0, len(phong[r][2]), "")
                m.Add(d == sum(vs)); dem[(c, r)] = d
    cao = m.NewIntVar(0, max(len(p[2]) for p in phong), "")
    for d in dem.values():
        m.Add(cao >= d)
    # rải đều: phạt phần vượt "mức chia đều" của mỗi lớp trong từng nhóm phòng cùng môn thi số 1
    vuot = []
    tong_lop = Counter((g[0], g[1]) for g, ds in nhom.items() for _ in ds)
    so_phong_mon1 = Counter(a for A, _ in mau_phong for a in A)
    for (c, r), d in dem.items():
        muc = max(-(-tong_lop[(c, a)] // so_phong_mon1[a]) for a in mau_phong[r][0] if (c, a) in tong_lop) \
            if any((c, a) in tong_lop for a in mau_phong[r][0]) else 0
        e = m.NewIntVar(0, len(phong[r][2]), "")
        m.Add(e >= d - muc); vuot.append(e)
    for (g, r), v in x.items():   # gợi ý: cách chia hiện tại
        m.AddHint(v, sum(1 for h in phong[r][2] if (h["lop"], h["mon1"], tuple(t for t in _k(h) if t != h["mon1"])) == g))
    giai = None
    for muc_tieu in (cao, sum(vuot)):
        m.Minimize(muc_tieu)
        sv = cp_model.CpSolver()
        sv.parameters.num_workers = 1
        sv.parameters.random_seed = 2026
        sv.parameters.max_deterministic_time = 2.0
        sv.parameters.max_time_in_seconds = 2.0
        if sv.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        giai = sv
        m.ClearHints()
        for v in x.values():
            m.AddHint(v, sv.Value(v))
        m.Add(muc_tieu <= int(round(sv.ObjectiveValue())))
    if giai is None:
        return phong
    moi = [[] for _ in phong]
    for g, ds in nhom.items():
        ds = sorted(ds, key=lambda h: khoa_ten_vn(h["ten"]))
        vt = 0
        for r in range(len(phong)):
            so = giai.Value(x[(g, r)]) if (g, r) in x else 0
            moi[r] += ds[vt:vt + so]; vt += so
    return [(t, c, moi[r]) for r, (t, c, _) in enumerate(phong)]


def xep_phong(df: pd.DataFrame, suc_chua: int = 24, si_so_toi_thieu: int = 0, tien_to_sbd: str = "",
              so_bat_dau: int = 1, phong_thi: list[tuple[str, int]] | None = None, toi_uu: bool = True,
              gioi_han_giay: float = 10.0, sbd_cho: dict | None = None, uu_tien: str = UU_TIEN_MON,
              mon1_theo_cap: dict | None = None, ghep_mon1: bool = False, max_mon2: int = 2,
              khong_tach_cap: bool = False, max_mon_ca: int = 0, max_cung_lop: int = 0,
              uu_tien_phong: dict | None = None) -> dict:
    """uu_tien (khi tối ưu): "mon" = mỗi môn chỉ thi ở 1 lần (luôn là môn thi số 1 hoặc số 2) trước, rồi ít phòng;
    "phong" = ít phòng trước.
    mon1_theo_cap: {frozenset({môn a, môn b}): môn thi số 1} — phương án tự chọn (bỏ qua tối ưu tự động).
    ghep_mon1: cho phép 1 phòng có 2 môn thi số 1. max_mon2: tối đa số môn thi số 2 trong 1 phòng.
    khong_tach_cap: (tối ưu) mỗi cặp môn chỉ 1 hướng. phong_thi: [(tên phòng, sức chứa)] theo thứ tự dùng; None/rỗng -> tự tạo phòng 'Phòng 01'... sức chứa
    `suc_chua`. Thiếu chỗ thì tự thêm phòng. -> {"hoc_sinh", "phong", "thong_ke", "canh_bao", "phong_trong"}."""
    suc_chua = max(int(suc_chua), 1)
    phong_thi = _sap_uu_tien(phong_thi, uu_tien_phong)
    hs, canh_bao = [], []
    for idx, r in df.iterrows():
        mon = tach_mon(r.get(COT_MON))
        rec = {"ma": str(r.get(COT_MA) or "").strip(), "ten": str(r.get(COT_TEN) or "").strip(),
               "lop": str(r.get(COT_LOP) or "").strip(), "mon": mon, "idx": idx}
        if _o_trong(rec["lop"]) and _o_trong(rec["ten"]):
            continue
        if not mon:
            canh_bao.append(f"{rec['ten'] or rec['ma']} ({rec['lop']}): chưa có môn thi — không xếp.")
            continue
        if len(mon) > 2:
            canh_bao.append(f"{rec['ten'] or rec['ma']} ({rec['lop']}): có {len(mon)} môn ({', '.join(mon)}) "
                            "— môn thứ 3 trở đi ghi vào Môn 2.")
        hs.append(rec)

    dem = Counter(m for h in hs for m in h["mon"])
    hang = {m: i for i, (m, _) in enumerate(sorted(dem.items(), key=lambda x: (-x[1], x[0])), start=1)}
    for h in hs:
        ms = sorted(h["mon"], key=lambda m: hang[m])
        h["mon1"], h["mon2"], h["mon1_tu_nhien"] = ms[0], " + ".join(ms[1:]), ms[0]

    if mon1_theo_cap:
        for h in hs:
            chon = mon1_theo_cap.get(frozenset(h["mon"])) if len(h["mon"]) == 2 else None
            if chon in h["mon"]:
                h["mon1"] = chon
                h["mon2"] = " + ".join(m for m in sorted(h["mon"], key=lambda m: hang[m]) if m != chon)
    hang_doi = list(phong_thi or [])
    co_ds_phong, so_tu_dong = bool(hang_doi), [0]
    phong, da_toi_uu = None, False
    if hs:   # tắt tối ưu: môn đông hơn là môn thi số 1, nhưng vẫn xếp phòng theo đúng các ràng buộc
        huong = mon1_theo_cap or (None if toi_uu else
                                  {frozenset(h["mon"]): h["mon1"] for h in hs if len(h["mon"]) == 2})
        smin = [int(si_so_toi_thieu or 0)]

        def _giai(mmc, mcl):
            return _toi_uu_theo_phong(hs, hang, list(phong_thi or []), suc_chua, bool(phong_thi), gioi_han_giay,
                                      uu_tien, max(int(max_mon2), 1), 2 if ghep_mon1 else 1, huong,
                                      khong_tach_cap, mmc, mcl, smin[0], uu_tien_phong)
        kq_tu = _giai(max_mon_ca, max_cung_lop)
        if kq_tu in (None, KHONG_KHA_THI) and smin[0]:   # sĩ số tối thiểu quá chặt với các ràng buộc khác
            smin[0] = 0
            kq_tu = _giai(max_mon_ca, max_cung_lop)
            if kq_tu not in (None, KHONG_KHA_THI):
                canh_bao.append(f"Không xếp được để mọi phòng có từ {int(si_so_toi_thieu)} học sinh trở lên (cùng "
                                "các ràng buộc khác) — đã bỏ ràng buộc này. Thử bật “cho phép 1 phòng có 2 môn thi "
                                "số 1”, hoặc giảm sĩ số tối thiểu.")
        if kq_tu in (None, KHONG_KHA_THI) and max_cung_lop:   # giới hạn số em cùng lớp quá chặt
            kq_tu = _giai(max_mon_ca, 0)
            if kq_tu not in (None, KHONG_KHA_THI):
                canh_bao.append(f"Không xếp được với giới hạn tối đa {int(max_cung_lop)} em cùng lớp / phòng (cùng "
                                "các ràng buộc môn) — đã bỏ giới hạn này, app vẫn trộn lớp nhiều nhất có thể. "
                                "Hãy tăng giới hạn hoặc cho thêm phòng.")
        if kq_tu in (None, KHONG_KHA_THI) and max_mon_ca:   # giới hạn môn/ca quá chặt: giải lại không giới hạn
            kq_tu = _giai(0, 0)
            if kq_tu not in (None, KHONG_KHA_THI):
                canh_bao.append(f"Không xếp được với giới hạn mỗi ca tối đa {int(max_mon_ca)} môn — đã xếp với số "
                                "môn mỗi ca ít nhất có thể (xem dòng Ca 1 / Ca 2).")
        if kq_tu in (None, KHONG_KHA_THI):
            canh_bao.append(
                ("Không có cách xếp thoả mọi ràng buộc" if kq_tu == KHONG_KHA_THI else
                 "Không tìm được phương án trong thời gian cho phép")
                + " — dùng cách xếp thường (KHÔNG đảm bảo các ràng buộc). Hãy nới ràng buộc hoặc thêm phòng.")
            kq_tu = None
        else:
            phong, hang_doi, so_tu_dong[0] = kq_tu
            da_toi_uu = bool(toi_uu and not mon1_theo_cap)
    if phong is None:   # xếp thường (không tối ưu / bộ giải không ra kết quả)
        # nhóm theo môn 1 — BẮT BUỘC mỗi phòng 1 môn 1 (không ghép các môn 1 với nhau, kể cả nhóm nhỏ)
        theo_mon1 = defaultdict(list)
        for h in hs:
            theo_mon1[h["mon1"]].append(h)
        nhom = [(m1, theo_mon1[m1]) for m1 in sorted(theo_mon1, key=lambda m: (-len(theo_mon1[m]), hang[m]))]
        nhom_ghep = set()
        if ghep_mon1:   # gom từng đôi nhóm nhỏ (mỗi nhóm chưa đủ 1 phòng) vào 1 phòng vừa chỗ
            cho_max = max([c for _, c in (phong_thi or [])] or [suc_chua])
            lon = [g for g in nhom if len(g[1]) >= cho_max]
            nho = sorted([g for g in nhom if len(g[1]) < cho_max], key=lambda g: -len(g[1]))
            while nho:
                m1, ds = nho.pop(0)
                j = next((j for j, (_, d2) in enumerate(nho) if len(ds) + len(d2) <= cho_max), None)
                if j is not None:
                    m2, d2 = nho.pop(j)
                    m1, ds = f"{m1} + {m2}", ds + d2
                    nhom_ghep.add(m1)
                lon.append((m1, ds))
            nhom = lon

        def _sap(ds):
            return sorted(ds, key=lambda h: (h["lop"], khoa(h["ten"].split(" ")[-1] if h["ten"] else ""), khoa(h["ten"])))

        def _lay_phong():
            if hang_doi:
                return hang_doi.pop(0)
            so_tu_dong[0] += 1
            return (None, suc_chua)

        phong = []   # [(tên | None, sức chứa, [hs])]
        for m1, ds in nhom:
            lay = []
            vua = next((i for i, (_, c) in enumerate(hang_doi) if c >= len(ds)), None) if m1 in nhom_ghep else None
            if vua is not None:   # nhóm ghép: lấy 1 phòng đủ chỗ cho cả nhóm
                lay.append(hang_doi.pop(vua))
            while sum(c for _, c in lay) < len(ds):   # lấy ít phòng nhất (theo thứ tự danh sách) đủ chỗ cho nhóm
                lay.append(_lay_phong())
            cap = defaultdict(list)
            for h in ds:
                cap[(h["mon1"], h["mon2"])].append(h)
            nhom_cap = [_sap(cap[k]) for k in sorted(cap, key=lambda k: (-len(cap[k]), hang[k[0]], k[1]))]
            noi_dung = [None] * len(lay)
            for i, (_, c) in enumerate(lay):          # 1) phòng thuần 1 cặp môn: cặp đông đủ kín phòng
                lon = max(range(len(nhom_cap)), key=lambda j: len(nhom_cap[j]), default=None)
                if lon is not None and len(nhom_cap[lon]) >= c:
                    noi_dung[i], nhom_cap[lon] = nhom_cap[lon][:c], nhom_cap[lon][c:]
            con = [i for i in range(len(lay)) if noi_dung[i] is None]   # 2) phần lẻ
            for i, p in zip(con, _xep_vao_phong([g for g in nhom_cap if g], [lay[i][1] for i in con])):
                noi_dung[i] = p
            thua = []
            for i, (t, c) in enumerate(lay):
                if noi_dung[i]:
                    phong.append((t, c, noi_dung[i]))
                elif t is not None:
                    thua.append((t, c))
            hang_doi[:0] = thua   # phòng không dùng tới trả lại đầu hàng đợi (giữ thứ tự)

    if co_ds_phong and so_tu_dong[0]:
        canh_bao.insert(0, f"Tổng sức chứa các phòng đã nhập ÍT hơn số học sinh — đã tự thêm {so_tu_dong[0]} "
                           f"phòng ({suc_chua} chỗ/phòng). Bổ sung phòng vào danh sách.")
    dem_tu_dong = 0
    ds_phong = []
    for t, c, p in phong:
        if t is None:
            dem_tu_dong += 1
            t = f"Phòng thêm {dem_tu_dong:02d}" if co_ds_phong else f"Phòng {dem_tu_dong:02d}"
        ds_phong.append((t, c, p))

    so, dong_hs, dong_phong, sbd_theo_dong = int(so_bat_dau), [], [], {}
    rong = max(3, len(str(int(so_bat_dau) + len(hs))))
    for tp, suc, p in ds_phong:
        cap_p = Counter((h["mon1"], h["mon2"]) for h in p)
        m1s = {h["mon1"] for h in p}
        loai = ("Cùng môn 1 & môn 2" if len(cap_p) == 1 else "Cùng môn 1" if len(m1s) == 1 else "Ghép nhiều môn 1")
        dong_phong.append({
            "Phòng": tp, "Sức chứa": suc, "Sĩ số": len(p), "Còn trống": suc - len(p), "Môn 1": ", ".join(sorted(m1s, key=lambda m: hang[m])),
            "Môn 2": ", ".join(sorted({t for h in p for t in h["mon2"].split(" + ") if t}, key=lambda t: hang[t])),
            "Cặp môn (môn 1 – môn 2: số HS)": "; ".join(f"{a} – {b}: {n}" for (a, b), n in cap_p.most_common()),
            "Loại phòng": loai,
            "Số lớp": len({h["lop"] for h in p}),
            "Nhiều nhất 1 lớp": "{1} em ({0})".format(*Counter(h["lop"] for h in p).most_common(1)[0]) if p else "",
            "SBD": (f"{tien_to_sbd}{str(so).zfill(rong)} → {tien_to_sbd}{str(so + len(p) - 1).zfill(rong)}"
                    if not sbd_cho else "SBD chung (theo vần ABC)"),
        })
        if sbd_cho:   # SBD chung cả kỳ thi: trong phòng xếp theo SBD
            p = sorted(p, key=lambda h: sbd_cho.get(h["idx"], ""))
        else:   # trong phòng xếp theo vần ABC -> các lớp ngồi xen kẽ
            p = sorted(p, key=lambda h: (khoa_ten_vn(h["ten"]), h["lop"]))
        for stt, h in enumerate(p, start=1):
            sbd_theo_dong[h["idx"]] = sbd_cho.get(h["idx"], "") if sbd_cho else f"{tien_to_sbd}{str(so).zfill(rong)}"
            dong_hs.append({"SBD": sbd_theo_dong[h["idx"]],
                            "Phòng": tp, "STT trong phòng": stt,
                            "Họ và tên": h["ten"], "Lớp": h["lop"], "Mã HS": h["ma"],
                            "Môn 1": h["mon1"], "Môn 2": h["mon2"]})
            so += 1
    thong_ke = pd.DataFrame([
        {"Thứ hạng": hang[m], "Môn": m, "Số HS thi": n,
         "Là môn 1 của": sum(1 for h in hs if h["mon1"] == m), "Là môn 2 của": sum(1 for h in hs if m in h["mon2"])}
        for m, n in sorted(dem.items(), key=lambda x: hang[x[0]])
    ])
    so_doi = sum(1 for h in hs if h["mon1"] != h["mon1_tu_nhien"])
    mon_tach, hs_lech = [], 0
    lan = []
    for m, n in sorted(dem.items(), key=lambda x: hang[x[0]]):
        a = sum(1 for h in hs if h["mon1"] == m)
        if a and n - a:
            mon_tach.append(m); hs_lech += min(a, n - a)
        lan.append("Cả 2 lần" if a and n - a else ("Môn thi số 1" if a else "Môn thi số 2"))
    thong_ke.insert(2, "Thi ở", lan)
    mon_ca = {1: [m for m, l in zip(thong_ke["Môn"], lan) if l != "Môn thi số 2"],
              2: [m for m, l in zip(thong_ke["Môn"], lan) if l != "Môn thi số 1"]}
    return {"hoc_sinh": pd.DataFrame(dong_hs), "phong": pd.DataFrame(dong_phong), "thong_ke": thong_ke,
            "canh_bao": canh_bao, "phong_trong": list(hang_doi), "so_doi_mon1": so_doi, "sbd_theo_dong": sbd_theo_dong,
            "toi_uu": da_toi_uu, "mon_tach": mon_tach, "hs_lech": hs_lech,
            "mon_ca": mon_ca}


# ---------------------------------------------------------------------
# TOÁN – NGỮ VĂN: xếp phòng theo vần ABC (tên, rồi họ đệm) — đúng thứ tự chữ cái tiếng Việt
# ---------------------------------------------------------------------
_CHU_VN = "a ă â b c d đ e ê f g h i j k l m n o ô ơ p q r s t u ư v w x y z".split()
_HANG_CHU = {c: i for i, c in enumerate(_CHU_VN)}
_DAU_THANH = {"\u0300": 1, "\u0309": 2, "\u0303": 3, "\u0301": 4, "\u0323": 5}   # huyền hỏi ngã sắc nặng
_DAU_CHU = {"\u0306": "ă", "\u0302": "^", "\u031b": "+"}   # trăng (ă), mũ (â ê ô), móc (ơ ư)


def _khoa_chu_vn(chu: str) -> tuple:
    """Khoá so sánh 1 từ theo thứ tự chữ cái tiếng Việt: (thứ tự chữ..., dấu thanh...)."""
    chu_cai, thanh = [], []
    for c in unicodedata.normalize("NFD", chu.lower()):
        if c in _DAU_THANH:
            if thanh:
                thanh[-1] = _DAU_THANH[c]
            continue
        if c in _DAU_CHU and chu_cai:
            goc = _CHU_VN[chu_cai[-1]] if chu_cai[-1] < len(_CHU_VN) else ""
            moi = {"aă": "ă", "a^": "â", "e^": "ê", "o^": "ô", "o+": "ơ", "u+": "ư"}.get(goc + _DAU_CHU[c])
            if moi:
                chu_cai[-1] = _HANG_CHU[moi]
            continue
        if unicodedata.combining(c):
            continue
        chu_cai.append(_HANG_CHU.get(c, 100 + ord(c)))
        thanh.append(0)
    return tuple(chu_cai), tuple(thanh)


def khoa_ten_vn(ho_ten: str) -> tuple:
    """Sắp theo TÊN (từ cuối), rồi họ đệm — mỗi phần theo thứ tự chữ cái tiếng Việt."""
    tu = str(ho_ten or "").split()
    if not tu:
        return ((), ()), ((), ())
    ten, ho_dem = tu[-1], " ".join(tu[:-1])
    a, b = _khoa_chu_vn(ten), _khoa_chu_vn(ho_dem.replace(" ", "\u0000"))
    return (a[0], a[1], b[0], b[1])   # tên (chữ cái, rồi dấu) trước, sau đó họ đệm


def sap_abc(df: pd.DataFrame) -> list:
    """Chỉ số các dòng học sinh (có tên hoặc lớp) theo vần ABC; trùng họ tên thì theo lớp, mã."""
    dong = [(i, r) for i, r in df.iterrows() if not (_o_trong(r.get(COT_TEN)) and _o_trong(r.get(COT_LOP)))]
    dong.sort(key=lambda x: (khoa_ten_vn(x[1].get(COT_TEN)), str(x[1].get(COT_LOP) or ""), str(x[1].get(COT_MA) or "")))
    return [i for i, _ in dong]


def sbd_theo_abc(df: pd.DataFrame, tien_to_sbd: str = "", so_bat_dau: int = 1) -> dict:
    """{chỉ số dòng: SBD} đánh theo vần ABC — dùng chung cho cả kỳ thi."""
    thu_tu = sap_abc(df)
    rong = max(3, len(str(int(so_bat_dau) + len(thu_tu))))
    return {i: f"{tien_to_sbd}{str(int(so_bat_dau) + k).zfill(rong)}" for k, i in enumerate(thu_tu)}


def xep_phong_abc(df: pd.DataFrame, suc_chua: int = 24, tien_to_sbd: str = "", so_bat_dau: int = 1,
                  phong_thi: list[tuple[str, int]] | None = None, chia_deu: bool = False,
                  sbd_cho: dict | None = None, uu_tien_phong: dict | None = None) -> dict:
    """Toán – Ngữ văn: toàn bộ học sinh theo vần ABC, lần lượt kín từng phòng (theo thứ tự danh sách phòng).
    chia_deu=True: chia sĩ số đều nhau — có danh sách phòng thì dùng hết các phòng đã nhập (phòng thưa nhất),
    không có thì dùng ít phòng nhất. sbd_cho: dùng SBD của phòng môn tự chọn (xếp theo thứ tự SBD)."""
    suc_chua = max(int(suc_chua), 1)
    phong_thi = _sap_uu_tien(phong_thi, uu_tien_phong)
    uu = uu_tien_phong or {}
    thu_tu = sap_abc(df)
    sbd = sbd_theo_abc(df, tien_to_sbd, so_bat_dau)
    if sbd_cho:   # dùng SBD của phòng môn tự chọn, xếp theo thứ tự SBD
        sbd = {i: sbd_cho.get(i, sbd[i]) for i in thu_tu}
        thu_tu = sorted(thu_tu, key=lambda i: (i not in sbd_cho, str(sbd[i])))
    n, canh_bao = len(thu_tu), []
    ds = list(phong_thi or [])
    phong, tong = [], 0
    if chia_deu and ds and sum(c for _, c in ds) >= n:   # chia đều: dùng TẤT CẢ phòng đã nhập -> phòng thưa nhất
        phong, ds, tong = list(ds), [], sum(c for _, c in ds)
    while tong < n:   # ít phòng nhất theo thứ tự danh sách; thiếu thì tự thêm
        if ds:
            phong.append(ds.pop(0))
        else:
            phong.append((None, suc_chua))
        tong += phong[-1][1]
    so_them = sum(1 for t, _ in phong if t is None)
    if phong_thi and so_them:
        canh_bao.append(f"Tổng sức chứa các phòng đã nhập ÍT hơn số học sinh — đã tự thêm {so_them} phòng "
                        f"({suc_chua} chỗ/phòng). Bổ sung phòng vào danh sách.")
    if chia_deu and phong:   # chia đều trong cùng mức ưu tiên; phòng ưu tiên cao xếp kín trước
        si_so = chia_si_so([(c, 2 if t is None else uu.get(t, 1)) for t, c in phong], n)
    else:
        si_so, con = [], n
        for _, c in phong:
            si_so.append(min(c, con)); con -= si_so[-1]
    dong_hs, dong_phong, vt, dem = [], [], 0, 0
    for (t, c), k in zip(phong, si_so):
        if t is None:
            dem += 1
            t = f"Phòng thêm {dem:02d}" if phong_thi else f"Phòng {dem:02d}"
        nhom = thu_tu[vt:vt + k]; vt += k
        if not nhom:
            if t in {x for x, _ in (phong_thi or [])}:
                ds.append((t, c))   # phòng không dùng tới (VD ưu tiên thấp)
            continue
        ten_dau, ten_cuoi = (str(df.at[nhom[0], COT_TEN] or ""), str(df.at[nhom[-1], COT_TEN] or ""))
        dong_phong.append({"Phòng": t, "Sức chứa": c, "Sĩ số": len(nhom), "Còn trống": c - len(nhom),
                           "SBD": f"{sbd[nhom[0]]} → {sbd[nhom[-1]]}",
                           "Từ tên → đến tên": f"{ten_dau.split()[-1] if ten_dau.split() else ''} → "
                                               f"{ten_cuoi.split()[-1] if ten_cuoi.split() else ''}"})
        for stt, i in enumerate(nhom, start=1):
            r = df.loc[i]
            dong_hs.append({"SBD": sbd[i], "Phòng": t, "STT trong phòng": stt,
                            "Họ và tên": str(r.get(COT_TEN) or ""), "Lớp": str(r.get(COT_LOP) or ""),
                            "Mã HS": str(r.get(COT_MA) or ""), "Môn tự chọn": str(r.get(COT_MON) or "")})
    return {"hoc_sinh": pd.DataFrame(dong_hs), "phong": pd.DataFrame(dong_phong), "canh_bao": canh_bao,
            "phong_trong": ds, "theo_sbd_tu_chon": bool(sbd_cho)}


def xuat_excel(kq: dict) -> bytes:
    """Danh sách theo phòng (in được), tổng hợp phòng, thống kê môn."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        kq["hoc_sinh"].to_excel(w, sheet_name="Danh_sach_theo_phong", index=False)
        kq["phong"].to_excel(w, sheet_name="Tong_hop_phong", index=False)
        if "thong_ke" in kq:
            kq["thong_ke"].to_excel(w, sheet_name="Thong_ke_mon", index=False)
        hs = kq["hoc_sinh"]
        if not hs.empty:
            hs.sort_values(["Lớp", "Họ và tên"]).to_excel(w, sheet_name="Danh_sach_theo_lop", index=False)
        for ws in w.book.worksheets:
            for cot in ws.columns:
                ws.column_dimensions[cot[0].column_letter].width = min(
                    max(len(str(c.value or "")) for c in cot) + 2, 60)
            ws.freeze_panes = "A2"
    return buf.getvalue()



def cap_mon(df: pd.DataFrame, mon1_theo_cap: dict | None = None) -> pd.DataFrame:
    """Bảng cặp môn tự chọn: Cặp môn | Số HS | Môn thi số 1 (mặc định: môn đông hơn, hoặc theo phương án đã chọn)."""
    dem_cap, dem_mon = Counter(), Counter()
    for _, r in df.iterrows():
        ms = tach_mon(r.get(COT_MON))
        dem_mon.update(ms)
        if len(ms) == 2:
            dem_cap[frozenset(ms)] += 1
    dong = []
    for k, n in dem_cap.items():
        a, b = sorted(k, key=lambda m: (-dem_mon[m], m))
        chon = (mon1_theo_cap or {}).get(k)
        dong.append({"Cặp môn": f"{a} – {b}", "Số HS": n, "Môn thi số 1": chon if chon in k else a})
    return pd.DataFrame(dong, columns=["Cặp môn", "Số HS", "Môn thi số 1"]).sort_values(
        "Số HS", ascending=False, kind="stable").reset_index(drop=True)


def phuong_an_tu_bang(bang: pd.DataFrame | None) -> dict:
    """Bảng cặp môn (đã sửa) -> {frozenset(cặp): môn thi số 1}."""
    ra = {}
    if bang is None or bang.empty:
        return ra
    for _, r in bang.iterrows():
        cap = [chuan_mon(x) for x in str(r.get("Cặp môn") or "").split(" – ")]
        chon = chuan_mon(str(r.get("Môn thi số 1") or ""))
        if len(cap) == 2 and chon in cap:
            ra[frozenset(cap)] = chon
    return ra


def phuong_an_sang_chuoi(pa: dict) -> str:
    return "; ".join(f"{'|'.join(sorted(k))}>{v}" for k, v in sorted(pa.items(), key=lambda x: sorted(x[0])))


def phuong_an_tu_chuoi(chuoi: str) -> dict:
    ra = {}
    for muc in str(chuoi or "").split(";"):
        if ">" in muc:
            cap, chon = muc.strip().split(">", 1)
            cap = cap.split("|")
            if len(cap) == 2 and chon in cap:
                ra[frozenset(cap)] = chon
    return ra


# ---------------------------------------------------------------------
# XUẤT DANH SÁCH PHÒNG THI THEO MẪU IN (mỗi phòng 1 trang)
# ---------------------------------------------------------------------
_TEN_NGAN = {"Vật lí": "LÝ", "Hóa học": "HÓA", "Sinh học": "SINH", "Tiếng Anh": "ANH", "Địa lí": "ĐỊA",
             "Lịch sử": "SỬ", "GDKT&PL": "GDKT&PL", "Tin học": "TIN", "Toán": "TOÁN", "Ngữ văn": "VĂN"}


def trang_tu_chon(kq: dict) -> list[dict]:
    """Kết quả xep_phong -> các trang in: mỗi phòng các cột môn (môn thi số 1 trước, rồi môn thi số 2)."""
    hs = kq["hoc_sinh"]
    trang = []
    for _, p in kq["phong"].iterrows():
        mon = [m for m in str(p.get("Môn 1") or "").split(", ") if m]
        mon += [m for m in str(p.get("Môn 2") or "").split(", ") if m and m not in mon]
        dong = []
        for _, h in hs[hs["Phòng"] == p["Phòng"]].iterrows():
            thi = {h["Môn 1"]} | {m for m in str(h["Môn 2"] or "").split(" + ") if m}
            dong.append((h["SBD"], h["Họ và tên"], h["Lớp"], thi))
        trang.append({"phong": p["Phòng"], "mon": mon, "hs": dong})
    return trang


def trang_toan_van(kq: dict) -> list[dict]:
    hs = kq["hoc_sinh"]
    return [{"phong": p, "mon": ["Toán", "Ngữ văn"],
             "hs": [(h["SBD"], h["Họ và tên"], h["Lớp"], {"Toán", "Ngữ văn"}) for _, h in hs[hs["Phòng"] == p].iterrows()]}
            for p in kq["phong"]["Phòng"]]


QUOC_HIEU, TIEU_NGU = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "Độc lập - Tự do - Hạnh phúc"


# Thông số lấy NGUYÊN từ mẫu của trường (M_UA.xlsx): font mặc định Times New Roman 12, độ rộng cột, dòng 20,1,
# dòng tiêu ngữ 51, lề, tỉ lệ in 90 %, mỗi phòng 1 trang 39 dòng, 2 đường kẻ ngắn dưới tên trường / tiêu ngữ.
_RONG_COT_MAU = [4.796875, 11, 21.69921875, 9.3984375, 8.3984375]          # A..E
_RONG_MON_MAU = [(8.69921875, 14.796875), (11.19921875, 14.09765625)]      # (M.đề, Ký tên) môn 1, môn 2, …
_DUONG_KE_MAU = [   # (cột từ, lệch từ, cột đến, lệch đến, lệch dòng) — EMU, đúng như file mẫu
    (2, 504825, 2, 1533525, 514350),    # dưới "TRƯỜNG TH, THCS VÀ THPT TÂN PHÚ"
    (6, 314325, 8, 66675, 504825),      # dưới "Độc lập - Tự do - Hạnh phúc"
]
_DONG_MOI_TRANG = 39


def _ve_duong_ke(du_lieu: bytes, dong_dau: list[int]) -> bytes:
    """Chèn các đường kẻ (connector) của mẫu vào đầu mỗi trang (openpyxl không tự vẽ được hình)."""
    import zipfile

    neo, so = [], 2
    for r0 in dong_dau:
        for c1, o1, c2, o2, dy in _DUONG_KE_MAU:
            neo.append(
                f'<xdr:twoCellAnchor><xdr:from><xdr:col>{c1}</xdr:col><xdr:colOff>{o1}</xdr:colOff>'
                f'<xdr:row>{r0 - 1}</xdr:row><xdr:rowOff>{dy}</xdr:rowOff></xdr:from><xdr:to><xdr:col>{c2}</xdr:col>'
                f'<xdr:colOff>{o2}</xdr:colOff><xdr:row>{r0 - 1}</xdr:row><xdr:rowOff>{dy}</xdr:rowOff></xdr:to>'
                f'<xdr:cxnSp macro=""><xdr:nvCxnSpPr><xdr:cNvPr id="{so}" name="Straight Connector {so - 1}"/>'
                '<xdr:cNvCxnSpPr/></xdr:nvCxnSpPr><xdr:spPr><a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
                '<a:ln w="9525"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:ln></xdr:spPr>'
                '</xdr:cxnSp><xdr:clientData/></xdr:twoCellAnchor>')
            so += 1
    ve = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/'
          'drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
          + "".join(neo) + "</xdr:wsDr>")
    vao, ra = zipfile.ZipFile(io.BytesIO(du_lieu)), io.BytesIO()
    with zipfile.ZipFile(ra, "w", zipfile.ZIP_DEFLATED) as z:
        ten = vao.namelist()
        for n in ten:
            d = vao.read(n)
            if n == "[Content_Types].xml":
                d = d.decode().replace("</Types>", '<Override PartName="/xl/drawings/drawing1.xml" ContentType='
                                       '"application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>').encode()
            elif n == "xl/worksheets/sheet1.xml":
                the = ('<drawing xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                       'r:id="rIdKe1"/>')
                x = d.decode()
                vt = min([x.find(t) for t in ("<legacyDrawing", "<tableParts", "<extLst") if x.find(t) >= 0]
                         or [x.rfind("</worksheet>")])
                d = (x[:vt] + the + x[vt:]).encode()
            elif n == "xl/worksheets/_rels/sheet1.xml.rels":
                d = d.decode().replace("</Relationships>", '<Relationship Id="rIdKe1" Type="http://schemas.'
                                       'openxmlformats.org/officeDocument/2006/relationships/drawing" '
                                       'Target="../drawings/drawing1.xml"/></Relationships>').encode()
            z.writestr(n, d)
        if "xl/worksheets/_rels/sheet1.xml.rels" not in ten:
            z.writestr("xl/worksheets/_rels/sheet1.xml.rels",
                       '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.'
                       'openxmlformats.org/package/2006/relationships"><Relationship Id="rIdKe1" Type="http://schemas.'
                       'openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/>'
                       '</Relationships>')
        z.writestr("xl/drawings/drawing1.xml", ve)
    return ra.getvalue()


def xuat_mau_phong(trang: list[dict], ten_truong: str = "", ten_ky_thi: str = "", don_vi: str = "",
                   ghi_mon_tieu_de: bool = False) -> bytes:
    """Mẫu in danh sách phòng thi GIỐNG mẫu của trường: mỗi phòng 1 trang — tiêu ngữ (trái: đơn vị chủ quản +
    tên trường, phải: Quốc hiệu + "Độc lập - Tự do - Hạnh phúc", có đường kẻ ngắn bên dưới), tên kỳ thi
    (+ môn nếu ghi_mon_tieu_de), PHÒNG …; bảng STT | SBD | Họ và tên | tên | Lớp | mỗi môn 2 cột (M.đề, Ký tên),
    em không thi môn nào thì ô môn đó gạch chéo; cuối trang: số học sinh, dòng vắng, tổng bài/tờ, chữ ký giám thị."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter as cot
    from openpyxl.utils.indexed_list import IndexedList
    from openpyxl.worksheet.pagebreak import Break

    wb = Workbook()
    wb._fonts = IndexedList([Font(name="Times New Roman", size=12)])   # font mặc định như mẫu -> cột rộng như mẫu
    ws = wb.active
    ws.title = "Danh_sach_phong"
    ws.sheet_format.defaultRowHeight, ws.sheet_format.customHeight = 20.1, True
    mong, manh = Side(style="thin"), Side(style="hair")
    vien = Border(left=mong, right=mong, top=mong, bottom=mong)
    gach = PatternFill(fill_type="lightUp", fgColor="FF808080", bgColor="FFFFFFFF")
    tnr = lambda sz=12, b=False, i=False: Font(name="Times New Roman", size=sz, bold=b, italic=i)   # noqa: E731
    giua = Alignment(horizontal="center", vertical="center", wrap_text=True)
    trai = Alignment(horizontal="left", vertical="center")
    so_mon_max = max([len(t["mon"]) for t in trang] or [2])
    for j, w in enumerate(_RONG_COT_MAU, start=1):
        ws.column_dimensions[cot(j)].width = w
    for k in range(max(so_mon_max, 2)):
        w1, w2 = _RONG_MON_MAU[min(k, 1)]
        ws.column_dimensions[cot(6 + 2 * k)].width, ws.column_dimensions[cot(7 + 2 * k)].width = w1, w2

    def _o(rr, c, v=None, font=None, can=None, bien=None):
        x = ws.cell(rr, c) if v is None else ws.cell(rr, c, v)
        if font is not None:
            x.font = font
        if can is not None:
            x.alignment = can
        if bien is not None:
            x.border = bien
        return x

    r, dong_dau = 1, []
    for t in trang:
        so_mon = max(len(t["mon"]), 1)
        cuoi = 5 + 2 * so_mon            # cột cuối của bảng
        rong = max(cuoi, 9)              # tiêu đề trải tối thiểu A..I như mẫu
        dong_dau.append(r)
        # --- tiêu ngữ (dòng cao 51) ---
        ws.row_dimensions[r].height = 51
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        _o(r, 1, f"{don_vi}\n{ten_truong}", tnr(12, True), giua)
        ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=9)
        _o(r, 6, f"{QUOC_HIEU}\n{TIEU_NGU}", tnr(12, True), giua)
        tieu_de = ten_ky_thi + (" - MÔN " + " - ".join(_TEN_NGAN.get(m, m.upper()) for m in t["mon"])
                                if ghi_mon_tieu_de else "")
        phong_ten = str(t["phong"]).upper()
        for k, v in ((1, tieu_de), (2, phong_ten if phong_ten.startswith("PHÒNG") else f"PHÒNG {phong_ten}")):
            ws.merge_cells(start_row=r + k, start_column=1, end_row=r + k, end_column=rong)
            _o(r + k, 1, v, tnr(12, True), giua)
        # --- tiêu đề bảng ---
        h1, h2 = r + 4, r + 5
        for c1, c2, chu in ((1, 1, "STT"), (2, 2, "SBD"), (3, 4, "Họ và tên học sinh"), (5, 5, "Lớp")):
            ws.merge_cells(start_row=h1, start_column=c1, end_row=h2, end_column=c2)
            _o(h1, c1, chu)
        for k, m in enumerate(t["mon"]):
            c = 6 + 2 * k
            ws.merge_cells(start_row=h1, start_column=c, end_row=h1, end_column=c + 1)
            _o(h1, c, m)
            _o(h2, c, "M.đề"); _o(h2, c + 1, "Ký tên")
        for rr in (h1, h2):
            for c in range(1, cuoi + 1):
                _o(rr, c, None, tnr(10, True), giua, vien)
        # --- học sinh ---
        for stt, (sbd, ten, lop, thi) in enumerate(t["hs"], start=1):
            rr = h2 + stt
            sbd_o = int(sbd) if str(sbd).isdigit() and not str(sbd).startswith("0") else sbd
            tach = str(ten).split()
            for c, v in ((1, stt), (2, sbd_o), (3, ten), (4, tach[-1] if tach else ""), (5, lop)):
                _o(rr, c, v, tnr(12), trai if c in (3, 4) else giua, vien)
            _o(rr, 3, None, bien=Border(left=mong, top=mong, bottom=mong))
            _o(rr, 4, None, bien=Border(right=mong, top=mong, bottom=mong))
            for k, m in enumerate(t["mon"]):
                for c in (6 + 2 * k, 7 + 2 * k):
                    x = _o(rr, c, None, tnr(12), giua, vien)
                    if m not in thi:   # không thi môn này -> gạch chéo
                        x.fill = gach
        rr = h2 + len(t["hs"]) + 1      # 1 dòng trống có kẻ như mẫu
        for c in range(1, cuoi + 1):
            _o(rr, c, None, bien=Border(left=mong, right=mong, top=manh, bottom=mong))
        ws.merge_cells(start_row=rr, start_column=3, end_row=rr, end_column=4)
        # --- cuối trang ---
        f0 = rr + 1
        _o(f0, 1, f"Danh sách này có {len(t['hs'])} học sinh", tnr(11, i=True), Alignment(horizontal="left"))
        for k, v in ((1, "Trong đó: - Số học sinh dự thi:......; số học sinh vắng:.....; "
                         "SBD vắng:............................................"),
                     (2, "Tổng số bài:..............; Tổng số tờ:...............")):
            ws.merge_cells(start_row=f0 + k, start_column=1, end_row=f0 + k, end_column=rong)
            _o(f0 + k, 1, v, tnr(12), Alignment(horizontal="left"))
        gt2 = rong - 2
        ws.merge_cells(start_row=f0 + 4, start_column=1, end_row=f0 + 4, end_column=3)
        ws.merge_cells(start_row=f0 + 5, start_column=1, end_row=f0 + 5, end_column=3)
        giua_1_dong = Alignment(horizontal="center", vertical="center")   # không xuống dòng (tràn sang 2 bên như mẫu)
        _o(f0 + 4, 1, "GIÁM THỊ 1", tnr(12, True), giua_1_dong)
        _o(f0 + 5, 1, "( Ký và ghi rõ họ tên )", tnr(12), giua_1_dong)
        _o(f0 + 4, gt2, "GIÁM THỊ 2", tnr(12, True), giua_1_dong)
        _o(f0 + 5, gt2, "( Ký và ghi rõ họ tên )", tnr(12), giua_1_dong)
        het = max(r + _DONG_MOI_TRANG - 1, f0 + 8)   # mỗi phòng 1 trang (39 dòng như mẫu)
        ws.row_breaks.append(Break(id=het))
        r = het + 1
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    if so_mon_max <= 2:
        ws.page_setup.scale = 90
    else:   # nhiều môn hơn mẫu: thu vừa 1 trang ngang
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left, ws.page_margins.right = 0.2362204724409449, 0.17
    ws.page_margins.top, ws.page_margins.bottom = 0.5118110236220472, 0.2362204724409449
    buf = io.BytesIO()
    wb.save(buf)
    return _ve_duong_ke(buf.getvalue(), dong_dau)
