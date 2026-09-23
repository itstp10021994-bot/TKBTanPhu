"""
Đăng thời khoá biểu lên Microsoft Teams qua 1 flow Power Automate.

Tệp của mỗi kênh Teams nằm trong thư viện tài liệu SharePoint của nhóm
(Shared Documents/<Tên kênh>/...). App gửi các tệp (PDF/Excel, dạng base64) +
nội dung tin nhắn cho flow; flow lưu tệp vào thư mục chỉ định và đăng tin nhắn
thông báo vào kênh. Không cần quyền admin — flow chạy bằng tài khoản người tạo.

Cấu hình trong Secrets (xem TEAMS.md):

    [teams]
    flow_url = "<HTTP URL của flow TKB_DangTeams>"
    thu_muc  = "Thời khoá biểu"                     # thư mục con trong kênh
    app_url  = "https://tkbtanphu.streamlit.app/"   # (tuỳ chọn) link trong tin nhắn
"""

from __future__ import annotations

import base64
import html
from datetime import datetime

import requests

import storage

GIO_VN = storage.GIO_VN


def doc_cau_hinh(secrets) -> dict:
    """{} nếu chưa cấu hình mục [teams]."""
    try:
        muc = dict(secrets["teams"]) if "teams" in secrets else {}
    except Exception:
        muc = {}
    if not str(muc.get("flow_url") or "").strip():
        return {}
    return {
        "flow_url": str(muc["flow_url"]).strip(),
        "thu_muc": str(muc.get("thu_muc") or "Thời khoá biểu").strip().strip("/"),
        "app_url": str(muc.get("app_url") or "").strip(),
    }


def bay_gio_vn() -> datetime:
    return datetime.now(GIO_VN)


def tao_thong_diep(tieu_de: str, dong: list[str], ten_tep: list[str], thu_muc: str, app_url: str) -> str:
    """Tin nhắn HTML ngắn đăng vào kênh Teams."""
    phan = [f"<b>{html.escape(tieu_de)}</b>"] + [html.escape(d) for d in dong if d]
    if ten_tep:
        phan.append(f"📁 Đã lưu {len(ten_tep)} tệp vào thư mục <b>{html.escape(thu_muc)}</b>:")
        phan.append("<br>".join(f"• {html.escape(t)}" for t in ten_tep))
    if app_url:
        phan.append(f'👤 Giáo viên xem lịch cá nhân tại: <a href="{html.escape(app_url)}">{html.escape(app_url)}</a>')
    return "<br>".join(phan)


def gui(cfg: dict, tep: list[tuple[str, bytes]], thong_diep: str) -> None:
    """Gửi tệp + tin nhắn cho flow. Lỗi -> storage.LoiLuuTru (thông điệp tiếng Việt)."""
    body = {
        "thu_muc": cfg["thu_muc"],
        "thong_diep": thong_diep,
        "files": [{"ten": ten, "noi_dung_base64": base64.b64encode(noi_dung).decode("ascii")}
                  for ten, noi_dung in tep],
    }
    try:
        r = requests.post(cfg["flow_url"], json=body, timeout=230)
    except requests.Timeout:
        raise storage.LoiLuuTru("Flow đăng Teams chạy quá lâu — xem Run history của flow TKB_DangTeams.")
    except requests.RequestException as e:
        raise storage.LoiLuuTru(f"Không gọi được flow đăng Teams: {e}")
    if r.status_code in (401, 403):
        raise storage.LoiLuuTru(storage._giai_thich_loi_xac_thuc_flow(r, cfg["flow_url"]))
    if r.status_code in (502, 504):
        raise storage.LoiLuuTru(
            f"Flow đăng Teams không trả kết quả ({r.status_code}) — mở Run history của flow TKB_DangTeams để "
            "xem bước nào lỗi (thường do sai Site Address / thư mục chưa tạo / thiếu bước Response)."
        )
    if r.status_code >= 300:
        raise storage.LoiLuuTru(f"Flow đăng Teams trả lỗi {r.status_code}: {r.text[:300]}")
