"""
Đăng nhập & phân quyền (admin / user).

Tài khoản khai báo trong Secrets của ứng dụng (không lưu trong code/GitHub):

    [auth.users.admin]
    name          = "Quản trị viên"
    role          = "admin"
    password_hash = "pbkdf2_sha256$200000$...$..."   # tạo bằng công cụ trong app

    [auth.users.giaovien]
    name     = "Giáo viên"
    role     = "user"
    password = "matkhau"      # (được phép, nhưng nên dùng password_hash)

Chưa khai báo mục [auth] thì ứng dụng chạy như cũ: không cần đăng nhập, ai
mở cũng có quyền admin.
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


def doc_tai_khoan(secrets) -> dict[str, dict]:
    """Đọc [auth.users] trong st.secrets -> {tên đăng nhập (chữ thường): {...}}.
    Trả về {} nếu chưa cấu hình đăng nhập."""
    try:
        if "auth" not in secrets:
            return {}
        users = secrets["auth"].get("users", {})
    except Exception:
        return {}
    tai_khoan = {}
    for ten_dn, tk in dict(users).items():
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
