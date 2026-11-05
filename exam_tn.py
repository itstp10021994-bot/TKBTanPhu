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
  3. Nhóm môn 1 quá ít học sinh (dưới sĩ số tối thiểu) được ghép chung vào
     các phòng "ghép" cuối cùng, xếp liền theo cặp môn.
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


def xep_phong(df: pd.DataFrame, suc_chua: int = 24, si_so_toi_thieu: int = 12, tien_to_sbd: str = "",
              so_bat_dau: int = 1, phong_thi: list[tuple[str, int]] | None = None) -> dict:
    """phong_thi: [(tên phòng, sức chứa)] theo thứ tự dùng; None/rỗng -> tự tạo phòng 'Phòng 01'... sức chứa
    `suc_chua`. Thiếu chỗ thì tự thêm phòng. -> {"hoc_sinh", "phong", "thong_ke", "canh_bao", "phong_trong"}."""
    suc_chua = max(int(suc_chua), 1)
    hs, canh_bao = [], []
    for _, r in df.iterrows():
        mon = tach_mon(r.get(COT_MON))
        rec = {"ma": str(r.get(COT_MA) or "").strip(), "ten": str(r.get(COT_TEN) or "").strip(),
               "lop": str(r.get(COT_LOP) or "").strip(), "mon": mon}
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
        h["mon1"], h["mon2"] = ms[0], " + ".join(ms[1:])

    # nhóm theo môn 1; nhóm quá nhỏ -> ghép chung
    theo_mon1 = defaultdict(list)
    for h in hs:
        theo_mon1[h["mon1"]].append(h)
    nhom, ghep = [], []
    for m1 in sorted(theo_mon1, key=lambda m: hang[m]):
        (nhom.append((m1, theo_mon1[m1])) if len(theo_mon1[m1]) >= si_so_toi_thieu else ghep.extend(theo_mon1[m1]))
    if ghep:
        nhom.append(("(ghép)", ghep))

    def _sap(ds):
        return sorted(ds, key=lambda h: (h["lop"], khoa(h["ten"].split(" ")[-1] if h["ten"] else ""), khoa(h["ten"])))

    hang_doi = list(phong_thi or [])
    co_ds_phong, so_tu_dong = bool(hang_doi), [0]

    def _lay_phong():
        if hang_doi:
            return hang_doi.pop(0)
        so_tu_dong[0] += 1
        return (None, suc_chua)

    phong = []   # [(tên | None, sức chứa, [hs])]
    for m1, ds in nhom:
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
            "SBD": f"{tien_to_sbd}{str(so).zfill(rong)} → {tien_to_sbd}{str(so + len(p) - 1).zfill(rong)}",
        })
        for stt, h in enumerate(p, start=1):
            dong_hs.append({"SBD": f"{tien_to_sbd}{str(so).zfill(rong)}", "Phòng": tp, "STT trong phòng": stt,
                            "Họ và tên": h["ten"], "Lớp": h["lop"], "Mã HS": h["ma"],
                            "Môn 1": h["mon1"], "Môn 2": h["mon2"]})
            so += 1
    thong_ke = pd.DataFrame([
        {"Thứ hạng": hang[m], "Môn": m, "Số HS thi": n,
         "Là môn 1 của": sum(1 for h in hs if h["mon1"] == m), "Là môn 2 của": sum(1 for h in hs if m in h["mon2"])}
        for m, n in sorted(dem.items(), key=lambda x: hang[x[0]])
    ])
    return {"hoc_sinh": pd.DataFrame(dong_hs), "phong": pd.DataFrame(dong_phong), "thong_ke": thong_ke,
            "canh_bao": canh_bao, "phong_trong": list(hang_doi)}


def xuat_excel(kq: dict) -> bytes:
    """Danh sách theo phòng (in được), tổng hợp phòng, thống kê môn."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        kq["hoc_sinh"].to_excel(w, sheet_name="Danh_sach_theo_phong", index=False)
        kq["phong"].to_excel(w, sheet_name="Tong_hop_phong", index=False)
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
