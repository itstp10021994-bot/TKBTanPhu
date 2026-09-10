"""
Xếp phòng thi: chia học sinh đăng ký thi 1 môn vào các phòng thi theo sức
chứa, sinh số báo danh (SBD) nếu chưa có sẵn.

Độc lập hoàn toàn với bộ xếp thời khoá biểu (scheduler.py) — đây chỉ là
thuật toán chia đơn giản + round-robin để trộn lớp, không dùng CP-SAT.
"""

from __future__ import annotations


def sinh_sbd_tu_dong(danh_sach_hs: list[dict], khoi: int) -> list[dict]:
    """Với mỗi học sinh chưa có 'ma_hs' (rỗng/None), sinh SBD dạng
    {khoi:02d}{stt:04d} — VD khối 10, học sinh thứ 7 -> '100007'.
    Học sinh đã có sẵn 'ma_hs' thì dùng luôn mã đó làm SBD.
    Trả về list mới (không sửa list gốc), mỗi phần tử có thêm khoá 'sbd'.
    """
    ket_qua = []
    stt = 0
    for hs in danh_sach_hs:
        ma_hs = (hs.get("ma_hs") or "").strip()
        if ma_hs:
            sbd = ma_hs
        else:
            stt += 1
            sbd = f"{khoi:02d}{stt:04d}"
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


def xep_phong_thi(
    danh_sach_hs: list[dict], danh_sach_phong: list[dict], khoi: int, che_do: str
):
    """Hàm tổng hợp: sinh SBD -> sắp thứ tự theo chế độ -> chia vào phòng.

    danh_sach_hs: list[dict] mỗi phần tử {"ma_hs": str|"", "ho_ten": str, "lop": str}
    danh_sach_phong: list[dict] {"ten_phong": str, "suc_chua": int}
    che_do: "theo_lop" | "tron_khoi"

    Trả về (ket_qua, con_thieu) — xem chia_vao_phong().
    Mỗi học sinh trong kết quả có thêm 'sbd' và giữ nguyên 'lop'.
    """
    co_sbd = sinh_sbd_tu_dong(danh_sach_hs, khoi)
    da_sap = sap_xep_thu_tu_hoc_sinh(co_sbd, che_do)
    return chia_vao_phong(da_sap, danh_sach_phong)
