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

   (Cần App Registration trên Microsoft Entra — nếu không tạo được, dùng cách 3.)

3. Mã đăng nhập gửi qua email trường (KHÔNG cần App Registration / admin):
   giáo viên nhập email trường -> 1 flow Power Automate gửi mã 6 số vào hộp thư
   Outlook -> nhập mã để đăng nhập. Vai trò theo cùng quy tắc [phan_quyen]:

    [phan_quyen]
    otp_url      = "<HTTP URL của flow gửi mã>"
    admin_emails = ["it.stp@truong.edu.vn"]
    domains      = ["truong.edu.vn"]

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

    return {"admin_emails": _ds("admin_emails"), "user_emails": _ds("user_emails"), "domains": _ds("domains"),
            "otp_url": str(muc.get("otp_url") or "").strip()}


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


# ---------------------------------------------------------------------
# Mã đăng nhập 1 lần (OTP) gửi qua email
# ---------------------------------------------------------------------
class KhoMaOTP:
    """Lưu mã OTP đang chờ (chỉ lưu mã băm) — dùng chung mọi phiên qua
    st.cache_resource. Giới hạn: mã hết hạn sau HAN_PHUT phút, nhập sai tối đa
    SO_LAN_THU lần/mã, gửi mã cách nhau ít nhất CACH_GUI_GIAY giây và tối đa
    GUI_TOI_DA_GIO mã/giờ cho mỗi email."""
    HAN_PHUT = 10
    SO_LAN_THU = 5
    CACH_GUI_GIAY = 60
    GUI_TOI_DA_GIO = 5

    def __init__(self):
        self._ma: dict[str, dict] = {}
        self._lich_su_gui: dict[str, list[float]] = {}
        self._khoa = _secrets.token_bytes(32)

    def _bam(self, email: str, ma: str) -> str:
        return hmac.new(self._khoa, f"{email}|{ma}".encode("utf-8"), hashlib.sha256).hexdigest()

    def tao_ma(self, email: str, bay_gio: float) -> tuple[str | None, str]:
        """-> (mã 6 số, "") hoặc (None, lý do bị từ chối)."""
        lich_su = [t for t in self._lich_su_gui.get(email, []) if bay_gio - t < 3600]
        if lich_su and bay_gio - lich_su[-1] < self.CACH_GUI_GIAY:
            return None, f"Vừa gửi mã — chờ {int(self.CACH_GUI_GIAY - (bay_gio - lich_su[-1])) + 1} giây rồi gửi lại."
        if len(lich_su) >= self.GUI_TOI_DA_GIO:
            return None, "Đã gửi quá nhiều mã trong 1 giờ — thử lại sau."
        ma = f"{_secrets.randbelow(10**6):06d}"
        self._ma[email] = {"bam": self._bam(email, ma), "het_han": bay_gio + self.HAN_PHUT * 60, "da_thu": 0}
        self._lich_su_gui[email] = lich_su + [bay_gio]
        return ma, ""

    def huy_ma(self, email: str):
        self._ma.pop(email, None)

    def kiem_tra(self, email: str, ma: str, bay_gio: float) -> tuple[bool, str]:
        ban_ghi = self._ma.get(email)
        if not ban_ghi:
            return False, "Chưa có mã cho email này (hoặc mã đã dùng) — bấm Gửi mã."
        if bay_gio > ban_ghi["het_han"]:
            self._ma.pop(email, None)
            return False, "Mã đã hết hạn — bấm Gửi lại mã."
        if ban_ghi["da_thu"] >= self.SO_LAN_THU:
            self._ma.pop(email, None)
            return False, "Nhập sai quá nhiều lần — bấm Gửi lại mã."
        ban_ghi["da_thu"] += 1
        if hmac.compare_digest(ban_ghi["bam"], self._bam(email, (ma or "").strip())):
            self._ma.pop(email, None)
            return True, ""
        con = self.SO_LAN_THU - ban_ghi["da_thu"]
        return False, f"Mã không đúng — còn {con} lần thử." if con else "Nhập sai quá nhiều lần — bấm Gửi lại mã."


# ---------------------------------------------------------------------
# Ghi nhớ đăng nhập: token có chữ ký HMAC lưu trong cookie trình duyệt
# ---------------------------------------------------------------------
TEN_COOKIE = "tkb_dang_nhap"


def khoa_ky_token(secrets) -> bytes | None:
    """Khoá ký token. Ưu tiên [phan_quyen] cookie_secret, rồi [auth] cookie_secret;
    nếu không có thì suy ra từ otp_url / mã băm mật khẩu (đều là bí mật chỉ có
    trong Secrets). None = không bật được ghi nhớ đăng nhập."""
    pq, au = _muc(secrets, "phan_quyen"), _muc(secrets, "auth")
    nguon = pq.get("cookie_secret") or au.get("cookie_secret") or pq.get("otp_url")
    if not nguon:
        bam = sorted(str(tk.get("password_hash") or tk.get("password") or "")
                     for tk in doc_tai_khoan(secrets).values())
        nguon = "|".join(b for b in bam if b)
    if not nguon:
        return None
    return hashlib.sha256(f"tkb-dang-nhap|{nguon}".encode("utf-8")).digest()


def tao_token(khoa: bytes, nguon: str, dinh_danh: str, so_ngay: int, bay_gio: float) -> str:
    """Token dạng '<nguồn>|<định danh>|<hết hạn>' + chữ ký HMAC-SHA256 (base64url)."""
    import base64
    than = f"{nguon}|{dinh_danh}|{int(bay_gio + so_ngay * 86400)}".encode("utf-8")
    ky = hmac.new(khoa, than, hashlib.sha256).digest()
    ma_hoa = lambda b: base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")
    return f"{ma_hoa(than)}.{ma_hoa(ky)}"


def doc_token(khoa: bytes | None, token: str | None, bay_gio: float) -> tuple[str, str] | None:
    """-> (nguồn, định danh) nếu token hợp lệ và chưa hết hạn, ngược lại None."""
    import base64
    if not khoa or not token or "." not in token:
        return None
    try:
        giai = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        phan_than, phan_ky = token.strip().split(".", 1)
        than = giai(phan_than)
        if not hmac.compare_digest(giai(phan_ky), hmac.new(khoa, than, hashlib.sha256).digest()):
            return None
        nguon, dinh_danh, het_han = than.decode("utf-8").rsplit("|", 2)
        if bay_gio > int(het_han):
            return None
        return nguon, dinh_danh
    except (ValueError, UnicodeDecodeError):
        return None
