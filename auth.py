"""
Đăng nhập & phân quyền (admin / user). Có 2 cách đăng nhập, dùng 1 hoặc cả 2:

1. Tài khoản Microsoft 365 của trường (email Outlook) — qua st.login() của
   Streamlit (OpenID Connect với Microsoft Entra ID). Cấu hình trong Secrets:

    [auth]
    redirect_uri        = "https://<ten-app>.streamlit.app/oauth2callback"
    cookie_secret       = "<chuỗi ngẫu nhiên>"
    client_id           = "<Application (client) ID>"
    client_secret       = "<client secret>"
    server_metadata_url = "https://login.microsoftonline.com/<tenant_id>/v2.0/.well-known/openid-configuration"

    [phan_quyen]
    admin_emails = ["it.stp@truong.edu.vn"]   # các email có quyền admin
    domains      = ["truong.edu.vn"]          # email thuộc tên miền này = user
    user_emails  = []                         # (tuỳ chọn) thêm từng email user

2. Tài khoản nội bộ (tên đăng nhập + mật khẩu):

    [phan_quyen.users.admin]
    name          = "Quản trị viên"
    role          = "admin"
    password_hash = "pbkdf2_sha256$200000$...$..."   # tạo bằng công cụ trong app

    [phan_quyen.users.giaovien]
    name     = "Giáo viên"
    role     = "user"
    password = "matkhau"      # (được phép, nhưng nên dùng password_hash)

(Mục cũ [auth.users.<tên>] vẫn được đọc.) Chưa khai báo cách nào thì ứng dụng
chạy như cũ: không cần đăng nhập, ai mở cũng có quyền admin.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets as _secrets

VAI_TRO = ("admin", "user")
SO_VONG_LAP = 200_000


def bam_mat_khau(mat_khau: str, so_vong: int = SO_VONG_LAP) -> str:
    """Mã băm PBKDF2-SHA256 có salt ngẫu nhiên, dạng pbkdf2_sha256$vòng$salt$băm."""
    salt = _secrets.token_hex(16)
    bam = hashlib.pbkdf2_hmac("sha256", mat_khau.encode("utf-8"), bytes.fromhex(salt), so_vong)
    return f"pbkdf2_sha256${so_vong}${salt}${bam.hex()}"


def _dung_ma_bam(mat_khau: str, ma_bam: str) -> bool:
    try:
        thuat_toan, so_vong, salt, bam = ma_bam.strip().split("$")
        if thuat_toan != "pbkdf2_sha256":
            return False
        thu = hashlib.pbkdf2_hmac("sha256", mat_khau.encode("utf-8"), bytes.fromhex(salt), int(so_vong))
        return hmac.compare_digest(thu.hex(), bam)
    except (ValueError, TypeError):
        return False


def _muc(secrets, *duong_dan):
    """Đọc 1 mục lồng nhau trong st.secrets, không có thì trả {}."""
    try:
        muc = secrets
        for k in duong_dan:
            if k not in muc:
                return {}
            muc = muc[k]
        return dict(muc)
    except Exception:
        return {}


def doc_tai_khoan(secrets) -> dict[str, dict]:
    """Tài khoản nội bộ trong [phan_quyen.users] (và mục cũ [auth.users])
    -> {tên đăng nhập (chữ thường): {...}}. {} nếu chưa khai báo."""
    users = {**_muc(secrets, "auth", "users"), **_muc(secrets, "phan_quyen", "users")}
    tai_khoan = {}
    for ten_dn, tk in users.items():
        tk = dict(tk)
        vai_tro = str(tk.get("role", "user")).strip().lower()
        tai_khoan[str(ten_dn).strip().lower()] = {
            "ten_dn": str(ten_dn).strip().lower(),
            "ten": str(tk.get("name") or ten_dn),
            "vai_tro": vai_tro if vai_tro in VAI_TRO else "user",
            "password": tk.get("password"),
            "password_hash": tk.get("password_hash"),
        }
    return tai_khoan


def dang_nhap_microsoft_bat(secrets) -> bool:
    """Đã cấu hình đăng nhập Microsoft (mục [auth] của st.login) chưa."""
    muc = _muc(secrets, "auth")
    return all(muc.get(k) for k in ("client_id", "client_secret", "server_metadata_url",
                                     "redirect_uri", "cookie_secret"))


def doc_phan_quyen(secrets) -> dict:
    """Quy tắc gán vai trò cho email Microsoft từ mục [phan_quyen]."""
    muc = _muc(secrets, "phan_quyen")

    def _ds(k):
        v = muc.get(k) or []
        v = [v] if isinstance(v, str) else list(v)
        return {str(x).strip().lower().lstrip("@") for x in v if str(x).strip()}

    return {"admin_emails": _ds("admin_emails"), "user_emails": _ds("user_emails"), "domains": _ds("domains")}


def vai_tro_theo_email(email: str, pq: dict) -> str | None:
    """admin nếu email nằm trong admin_emails; user nếu nằm trong user_emails
    hoặc thuộc 1 tên miền trong domains (không khai báo domains/user_emails
    thì mọi tài khoản đăng nhập được đều là user); ngược lại None = không có quyền."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return None
    if email in pq["admin_emails"]:
        return "admin"
    if not pq["domains"] and not pq["user_emails"]:
        return "user"
    if email in pq["user_emails"] or email.rsplit("@", 1)[1] in pq["domains"]:
        return "user"
    return None


def xac_thuc(tai_khoan: dict[str, dict], ten_dn: str, mat_khau: str) -> dict | None:
    """-> {"ten_dn", "ten", "vai_tro"} nếu đúng, None nếu sai."""
    tk = tai_khoan.get((ten_dn or "").strip().lower())
    if not tk or not mat_khau:
        # vẫn tính băm 1 lần để thời gian phản hồi không lộ tài khoản có tồn tại hay không
        _dung_ma_bam(mat_khau or "x", "pbkdf2_sha256$1000$00$00")
        return None
    if tk.get("password_hash"):
        dung = _dung_ma_bam(mat_khau, str(tk["password_hash"]))
    elif tk.get("password") is not None:
        dung = hmac.compare_digest(str(tk["password"]).encode("utf-8"), mat_khau.encode("utf-8"))
    else:
        dung = False
    return {"ten_dn": tk["ten_dn"], "ten": tk["ten"], "vai_tro": tk["vai_tro"]} if dung else None
