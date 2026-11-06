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
    ra = pd.DataFrame({
        COT_TEN_PHONG: df[c_ten].map(lambda v: "" if _o_trong(v) else " ".join(str(v).split())),
        COT_SUC_CHUA: pd.to_numeric(df[c_so], errors="coerce"),
    })
    ra = ra[ra[COT_TEN_PHONG] != ""]
    loi = ra[ra[COT_SUC_CHUA].isna() | (ra[COT_SUC_CHUA] <= 0)]
    ra = ra.drop(loi.index)
    ra[COT_SUC_CHUA] = ra[COT_SUC_CHUA].astype(int)
    ghi_chu = [f"Cột dùng: Tên phòng = '{c_ten}', Sức chứa = '{c_so}'."]
    if len(loi):
        ghi_chu.append(f"⚠️ Bỏ {len(loi)} phòng không có sức chứa hợp lệ: {', '.join(loi[COT_TEN_PHONG])}.")
    return ra.reset_index(drop=True), ghi_chu


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


def _toi_uu_mon1(hs: list[dict], hang: dict, phong_ds: list[tuple], suc_chua: int, co_ds_phong: bool,
                 gioi_han_giay: float = 10.0):
    """Chọn MÔN XẾP PHÒNG (môn 1) cho từng học sinh trong các môn của em, và số phòng mỗi loại sức chứa cho
    từng môn, sao cho (ưu tiên giảm dần): 1) chỉ tự thêm phòng khi danh sách phòng KHÔNG đủ chỗ,
    2) ÍT PHÒNG NHẤT, 3) nhiều học sinh giữ môn đông hơn làm môn 1, 4) ít chỗ trống.
    Mỗi phòng chỉ 1 môn 1. Phòng gom theo (sức chứa, phòng tự thêm hay không) để bộ giải không phải thử
    các cách hoán đổi phòng giống nhau. Dùng OR-Tools CP-SAT.
    -> ({id(hs): môn 1}, {môn: [chỉ số phòng]}, danh sách phòng (kể cả phòng tự thêm)) | None."""
    from ortools.sat.python import cp_model

    n = len(hs)
    if not n:
        return {}, {}, list(phong_ds)
    mon = sorted({m for h in hs for m in h["mon"]}, key=lambda m: hang[m])
    cap = defaultdict(list)                      # cặp môn (theo thứ hạng) -> học sinh
    for h in hs:
        cap[tuple(sorted(h["mon"], key=lambda m: hang[m]))].append(h)
    # phòng tự thêm: đủ để mỗi môn có thể lấy thêm phòng (luôn có lời giải)
    them = -(-n // suc_chua) + len(mon)
    phong = list(phong_ds) + [(None, suc_chua)] * them
    loai = defaultdict(list)                     # (sức chứa, tự thêm?) -> chỉ số phòng (theo thứ tự)
    for r, (t, c) in enumerate(phong):
        loai[(c, t is None)].append(r)
    m = cp_model.CpModel()
    x = {(p, s): m.NewIntVar(0, len(ds), "") for p, ds in cap.items() for s in p}
    for p, ds in cap.items():
        m.Add(sum(x[(p, s)] for s in p) == len(ds))
    z = {(k, s): m.NewIntVar(0, len(rs), "") for k, rs in loai.items() for s in mon}
    for k, rs in loai.items():
        m.Add(sum(z[(k, s)] for s in mon) <= len(rs))
    for s in mon:
        m.Add(sum(x[(p, s)] for p in cap if s in p) <= sum(k[0] * z[(k, s)] for k in loai))
    so_phong = sum(z.values())
    tu_them = sum(z[(k, s)] for k in loai if k[1] for s in mon)
    doi_mon = sum(len(ds) - x[(p, p[0])] for p, ds in cap.items())
    cho = sum(k[0] * z[(k, s)] for k in loai for s in mon)
    # Giải lần lượt từng bậc ưu tiên (mỗi bậc là 1 bài nhỏ -> nhanh), cố định kết quả bậc trước rồi giải bậc sau.
    # Giới hạn thời gian TẤT ĐỊNH (deterministic) + 1 luồng -> mỗi lần chạy ra CÙNG 1 kết quả.
    giai = None
    bac = ([tu_them] if co_ds_phong else []) + [so_phong, doi_mon, cho]
    for muc_tieu in bac:
        m.Minimize(muc_tieu)
        g = cp_model.CpSolver()
        g.parameters.num_workers = 1
        g.parameters.random_seed = 2026
        g.parameters.max_deterministic_time = max(1.0, gioi_han_giay / len(bac))
        st = g.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if giai is None:
                return None
            break
        giai = g
        m.ClearHints()
        for v in list(x.values()) + list(z.values()):
            m.AddHint(v, g.Value(v))
        m.Add(muc_tieu <= int(round(g.ObjectiveValue())))
    mon1 = {}
    for p, ds in cap.items():
        ds = sorted(ds, key=lambda h: (h["lop"], khoa(h["ten"])))
        i = 0
        for s in p:
            k = giai.Value(x[(p, s)])
            for h in ds[i:i + k]:
                mon1[id(h)] = s
            i += k
    phong_cua, da_lay = defaultdict(list), defaultdict(int)
    for s in sorted(mon, key=lambda s: -sum(len(ds) for p, ds in cap.items() if s in p)):
        for k, rs in loai.items():
            so = giai.Value(z[(k, s)])
            phong_cua[s] += rs[da_lay[k]:da_lay[k] + so]
            da_lay[k] += so
    return mon1, dict(phong_cua), phong


def xep_phong(df: pd.DataFrame, suc_chua: int = 24, si_so_toi_thieu: int = 0, tien_to_sbd: str = "",
              so_bat_dau: int = 1, phong_thi: list[tuple[str, int]] | None = None, toi_uu: bool = True,
              gioi_han_giay: float = 10.0, sbd_cho: dict | None = None) -> dict:
    """phong_thi: [(tên phòng, sức chứa)] theo thứ tự dùng; None/rỗng -> tự tạo phòng 'Phòng 01'... sức chứa
    `suc_chua`. Thiếu chỗ thì tự thêm phòng. -> {"hoc_sinh", "phong", "thong_ke", "canh_bao", "phong_trong"}."""
    suc_chua = max(int(suc_chua), 1)
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

    phong_cua, kho_phong = None, None   # phương án tối ưu: môn -> phòng (chỉ số trong kho_phong)
    if toi_uu and hs:
        kq_tu = _toi_uu_mon1(hs, hang, list(phong_thi or []), suc_chua, bool(phong_thi), gioi_han_giay)
        if kq_tu is not None:
            mon1_moi, phong_cua, kho_phong = kq_tu
            for h in hs:
                h["mon1"] = mon1_moi[id(h)]
                h["mon2"] = " + ".join(m for m in sorted(h["mon"], key=lambda m: hang[m]) if m != h["mon1"])
        else:
            canh_bao.append("Không tìm được phương án tối ưu trong thời gian cho phép — dùng cách xếp thường.")

    # nhóm theo môn 1 — BẮT BUỘC mỗi phòng 1 môn 1 (không ghép các môn 1 với nhau, kể cả nhóm nhỏ)
    theo_mon1 = defaultdict(list)
    for h in hs:
        theo_mon1[h["mon1"]].append(h)
    nhom = [(m1, theo_mon1[m1]) for m1 in sorted(theo_mon1, key=lambda m: (-len(theo_mon1[m]), hang[m]))]

    def _sap(ds):
        return sorted(ds, key=lambda h: (h["lop"], khoa(h["ten"].split(" ")[-1] if h["ten"] else ""), khoa(h["ten"])))

    hang_doi = list(phong_thi or [])
    co_ds_phong, so_tu_dong = bool(hang_doi), [0]

    def _lay_phong():
        if hang_doi:
            return hang_doi.pop(0)
        so_tu_dong[0] += 1
        return (None, suc_chua)

    if phong_cua is not None:   # phương án tối ưu: phòng (theo thứ tự danh sách) cấp lại cho từng môn
        chon = sorted(r for rs in phong_cua.values() for r in rs)
        hang_doi = [kho_phong[r] for r in range(len(phong_thi or [])) if r not in set(chon)]
        con_lai = list(chon)   # chỉ số phòng đã chọn, theo thứ tự danh sách
        lay_cua = {}
        for m1, _ in nhom:   # môn đông trước lấy các phòng đầu danh sách, đúng các sức chứa bộ giải đã chọn
            chi_so = []
            for c in sorted((kho_phong[r][1] for r in phong_cua.get(m1, [])), reverse=True):
                r = next(r for r in con_lai if kho_phong[r][1] == c)
                con_lai.remove(r)
                chi_so.append(r)
            lay_cua[m1] = [kho_phong[r] for r in sorted(chi_so)]
        so_tu_dong[0] = sum(1 for rs in phong_cua.values() for r in rs if kho_phong[r][0] is None)

    phong = []   # [(tên | None, sức chứa, [hs])]
    for m1, ds in nhom:
        if phong_cua is not None:
            lay = list(lay_cua[m1])
        else:
            lay = []
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
        if phong_cua is None:
            hang_doi[:0] = thua   # phòng không dùng tới trả lại đầu hàng đợi (giữ thứ tự)
        else:
            hang_doi.extend(thua)

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

    so, dong_hs, dong_phong = int(so_bat_dau), [], []
    rong = max(3, len(str(int(so_bat_dau) + len(hs))))
    for tp, suc, p in ds_phong:
        cap_p = Counter((h["mon1"], h["mon2"]) for h in p)
        m1s = {h["mon1"] for h in p}
        loai = ("Cùng môn 1 & môn 2" if len(cap_p) == 1 else "Cùng môn 1" if len(m1s) == 1 else "Ghép nhiều môn 1")
        dong_phong.append({
            "Phòng": tp, "Sức chứa": suc, "Sĩ số": len(p), "Còn trống": suc - len(p), "Môn 1": ", ".join(sorted(m1s, key=lambda m: hang[m])),
            "Cặp môn (môn 1 – môn 2: số HS)": "; ".join(f"{a} – {b}: {n}" for (a, b), n in cap_p.most_common()),
            "Loại phòng": loai,
            "SBD": (f"{tien_to_sbd}{str(so).zfill(rong)} → {tien_to_sbd}{str(so + len(p) - 1).zfill(rong)}"
                    if not sbd_cho else "SBD chung (theo vần ABC)"),
        })
        if sbd_cho:   # SBD chung cả kỳ thi: trong phòng xếp theo SBD
            p = sorted(p, key=lambda h: sbd_cho.get(h["idx"], ""))
        for stt, h in enumerate(p, start=1):
            dong_hs.append({"SBD": sbd_cho.get(h["idx"], "") if sbd_cho else f"{tien_to_sbd}{str(so).zfill(rong)}",
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
    return {"hoc_sinh": pd.DataFrame(dong_hs), "phong": pd.DataFrame(dong_phong), "thong_ke": thong_ke,
            "canh_bao": canh_bao, "phong_trong": list(hang_doi), "so_doi_mon1": so_doi,
            "toi_uu": phong_cua is not None}


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
                  phong_thi: list[tuple[str, int]] | None = None, chia_deu: bool = False) -> dict:
    """Toán – Ngữ văn: toàn bộ học sinh theo vần ABC, lần lượt kín từng phòng (theo thứ tự danh sách phòng).
    chia_deu=True: dùng ít phòng nhất nhưng chia sĩ số đều nhau giữa các phòng."""
    suc_chua = max(int(suc_chua), 1)
    thu_tu = sap_abc(df)
    sbd = sbd_theo_abc(df, tien_to_sbd, so_bat_dau)
    n, canh_bao = len(thu_tu), []
    ds = list(phong_thi or [])
    phong, tong = [], 0
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
    if chia_deu and phong:   # chia đều: mỗi phòng ~ n / số phòng, không vượt sức chứa
        con, si_so = n, []
        for k, (_, c) in enumerate(phong):
            con_phong = len(phong) - k
            si_so.append(min(c, -(-con // con_phong)))
            con -= si_so[-1]
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
            "phong_trong": ds}


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
