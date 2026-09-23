"""
Đăng thời khoá biểu lên Microsoft Teams qua 1 flow Power Automate.

Tệp của mỗi kênh Teams nằm trong thư viện tài liệu SharePoint của nhóm
(Shared Documents/<Tên kênh>/...). App gửi các tệp (PDF/Excel, dạng base64) +
nội dung tin nhắn cho flow; flow lưu tệp vào thư mục chỉ định và đăng tin nhắn
thông báo vào kênh. Không cần quyền admin — flow chạy bằng tài khoản người tạo.

Cấu hình trong Secrets (xem TEAMS.md):

    [teams]
    flow_url  = "<HTTP URL của flow TKB_DangTeams>"
    thu_muc   = "Thời khoá biểu"                     # thư mục con trong kênh
    app_url   = "https://tkbtanphu.streamlit.app/"   # (tuỳ chọn) link trong tin nhắn
    # Đăng kiểu "bài viết" có ẢNH TKB + THẺ TỆP (giống đăng tay trên Teams):
    kenh_link = "<Lấy liên kết đến kênh (Get link to channel)>"
    site_url  = "https://truong.sharepoint.com/sites/TenNhom"
    thu_muc_kenh = "/Shared Documents/General"       # thư mục tệp của kênh

Có kenh_link + site_url thì dùng chế độ "graph" (2 lần gọi flow):
  1) thao_tac = "luu_tep": flow lưu tệp, trả về thông tin tệp (có ETag -> GUID);
  2) thao_tac = "dang_tin": flow gọi Graph POST /teams/{id}/channels/{id}/messages
     với ảnh nhúng (hostedContents) + thẻ tệp (attachments kiểu reference).
Không có thì dùng chế độ đơn giản: 1 lần gọi, flow tự đăng tin nhắn chữ.
"""

from __future__ import annotations

import base64
import html
import re
import uuid
from urllib.parse import parse_qs, quote, unquote, urlparse
from datetime import datetime

import requests

import storage

GIO_VN = storage.GIO_VN


def phan_tich_kenh(link: str) -> tuple[str, str] | None:
    """Link kênh Teams -> (team/group id, channel id)."""
    try:
        u = urlparse(str(link or "").strip())
        m = re.search(r"/channel/([^/]+)", u.path)
        group = (parse_qs(u.query).get("groupId") or [""])[0]
        if m and group:
            return group, unquote(m.group(1))
    except ValueError:
        pass
    return None


def doc_cau_hinh(secrets) -> dict:
    """{} nếu chưa cấu hình mục [teams]."""
    try:
        muc = dict(secrets["teams"]) if "teams" in secrets else {}
    except Exception:
        muc = {}
    if not str(muc.get("flow_url") or "").strip():
        return {}
    cfg = {
        "flow_url": str(muc["flow_url"]).strip(),
        "thu_muc": str(muc.get("thu_muc") or "Thời khoá biểu").strip().strip("/"),
        "app_url": str(muc.get("app_url") or "").strip(),
        "site_url": str(muc.get("site_url") or "").strip().rstrip("/"),
        "thu_muc_kenh": "/" + str(muc.get("thu_muc_kenh") or "/Shared Documents/General").strip().strip("/"),
        "che_do": "don_gian", "graph_uri": "", "loi_cau_hinh": "",
    }
    if muc.get("kenh_link"):
        kenh = phan_tich_kenh(muc["kenh_link"])
        if not kenh:
            cfg["loi_cau_hinh"] = "kenh_link không đúng dạng (cần có /channel/... và groupId=...)."
        elif not cfg["site_url"]:
            cfg["loi_cau_hinh"] = "thiếu site_url (địa chỉ site SharePoint của nhóm)."
        else:
            cfg["che_do"] = "graph"
            cfg["graph_uri"] = (f"https://graph.microsoft.com/v1.0/teams/{kenh[0]}/channels/"
                                f"{kenh[1]}/messages")
    return cfg


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


def _goi_flow(cfg: dict, body: dict) -> requests.Response:
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
    return r


def _tep_json(tep: list[tuple[str, bytes]]) -> list[dict]:
    return [{"ten": ten, "noi_dung_base64": base64.b64encode(noi_dung).decode("ascii")} for ten, noi_dung in tep]


def gui(cfg: dict, tep: list[tuple[str, bytes]], thong_diep: str) -> None:
    """Chế độ đơn giản: 1 lần gọi — flow lưu tệp + đăng tin nhắn chữ."""
    _goi_flow(cfg, {"thu_muc": cfg["thu_muc"], "thong_diep": thong_diep, "files": _tep_json(tep)})


# ---------------------------------------------------------------------
# Chế độ "graph": bài đăng có ảnh TKB + thẻ tệp
# ---------------------------------------------------------------------
def guid_tu_etag(etag) -> str | None:
    """ETag SharePoint dạng '"{2B1F...-...},1"' -> '2b1f...-...'."""
    m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", str(etag or ""))
    return m.group(1).lower() if m else None


def luu_tep(cfg: dict, tep: list[tuple[str, bytes]]) -> list[dict]:
    """Lần gọi 1: flow lưu tệp vào thư mục kênh -> [{"ten", "url", "guid"}]."""
    duong_dan = f"{cfg['thu_muc_kenh']}/{cfg['thu_muc']}"
    r = _goi_flow(cfg, {"thao_tac": "luu_tep", "duong_dan": duong_dan, "thu_muc": cfg["thu_muc"],
                        "files": _tep_json(tep)})
    try:
        tra_ve = r.json()
    except ValueError:
        tra_ve = []
    if isinstance(tra_ve, dict):
        tra_ve = tra_ve.get("value") or tra_ve.get("files") or []
    theo_ten = {str(x.get("Name") or x.get("name") or ""): x for x in tra_ve if isinstance(x, dict)}
    ket_qua = []
    for ten, _ in tep:
        x = theo_ten.get(ten, {})
        path = str(x.get("Path") or x.get("path") or f"{duong_dan}/{ten}")
        ket_qua.append({"ten": ten, "url": cfg["site_url"] + quote(path),
                        "guid": guid_tu_etag(x.get("ETag") or x.get("etag") or x.get("{ETag}"))})
    return ket_qua


def pdf_sang_png(pdf: bytes, zoom: float = 1.5) -> bytes | None:
    """Trang đầu của PDF -> ảnh PNG (cần thư viện pymupdf)."""
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return None
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        trang = doc[0]
        # cắt bỏ phần trắng phía dưới bảng cho gọn
        khung = trang.rect
        try:
            noi_dung = [b[:4] for b in trang.get_text("blocks")] + [d["rect"] for d in trang.get_drawings()]
            day = max((r[3] if isinstance(r, tuple) else r.y1) for r in noi_dung) + 12 if noi_dung else khung.y1
            khung = pymupdf.Rect(khung.x0, khung.y0, khung.x1, min(khung.y1, day))
        except Exception:
            pass
        return trang.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=khung).tobytes("png")


def tao_bai_dang(tieu_de: str, dong: list[str], anh: list[tuple[str, bytes]],
                 tep_da_luu: list[dict], app_url: str) -> dict:
    """Nội dung chatMessage cho Graph: chữ + ảnh nhúng (hostedContents) + thẻ tệp."""
    html_phan = [f"<p><b>{html.escape(tieu_de)}</b></p>"]
    html_phan += [f"<p>{html.escape(d)}</p>" for d in dong if d]
    hosted = []
    for i, (chu_thich, png) in enumerate(anh, start=1):
        html_phan.append(f"<p><b>{html.escape(chu_thich)}</b></p>"
                         f'<p><img src="../hostedContents/{i}/$value" style="max-width:100%"></p>')
        hosted.append({"@microsoft.graph.temporaryId": str(i), "contentType": "image/png",
                       "contentBytes": base64.b64encode(png).decode("ascii")})
    dinh_kem, khong_the = [], []
    for t in tep_da_luu:
        if t.get("guid"):
            dinh_kem.append({"id": t["guid"], "contentType": "reference", "contentUrl": t["url"], "name": t["ten"]})
        else:
            khong_the.append(t)
    if khong_the:  # không có GUID -> vẫn đưa đường link
        html_phan.append("<p>" + "<br>".join(
            f'📄 <a href="{html.escape(t["url"])}">{html.escape(t["ten"])}</a>' for t in khong_the) + "</p>")
    if app_url:
        html_phan.append(f'<p>👤 Giáo viên xem lịch cá nhân tại: <a href="{html.escape(app_url)}">'
                         f'{html.escape(app_url)}</a></p>')
    html_phan += [f'<attachment id="{a["id"]}"></attachment>' for a in dinh_kem]
    bai = {"body": {"contentType": "html", "content": "".join(html_phan)}}
    if hosted:
        bai["hostedContents"] = hosted
    if dinh_kem:
        bai["attachments"] = dinh_kem
    return bai


def dang_tin(cfg: dict, bai_dang: dict) -> None:
    """Lần gọi 2: flow đăng bài vào kênh qua Graph."""
    _goi_flow(cfg, {"thao_tac": "dang_tin", "graph_uri": cfg["graph_uri"], "graph_body": bai_dang})
