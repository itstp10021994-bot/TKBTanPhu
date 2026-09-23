"""
Lưu / tải dữ liệu của ứng dụng lên SharePoint.

Hỗ trợ 2 cách kết nối (cấu hình trong .streamlit/secrets.toml hoặc mục
Secrets của Streamlit Cloud — xem HUONG_DAN_SHAREPOINT.md):

  1. [sharepoint]      — gọi thẳng Microsoft Graph API bằng 1 App
                          Registration (Azure AD / Entra ID).
  2. [power_automate]  — gửi dữ liệu tới các flow Power Automate có trigger
                          "When a HTTP request is received"; flow tự ghi/đọc
                          file trong thư viện SharePoint.

Mỗi lần lưu tạo 2 file cùng tên trong thư mục SharePoint:
  - <tên>.json : bản sao lưu ĐẦY ĐỦ (dùng để tải lại vào ứng dụng).
  - <tên>.xlsx : bản Excel dễ đọc (mỗi bảng 1 sheet) cho người dùng mở
                 trực tiếp trên SharePoint.
"""

from __future__ import annotations

import base64
import io
import json
import re
from datetime import date, datetime
from urllib.parse import quote, urlparse

import pandas as pd
import requests

PHIEN_BAN_DINH_DANG = 1
TIMEOUT = 60

# Các bảng nhập liệu (DataFrame trong st.session_state) được sao lưu
BANG_DU_LIEU = {
    "departments": "To_chuyen_mon",
    "teachers": "Giao_vien",
    "classes": "Lop_hoc",
    "rooms": "Phong_dac_biet",
    "activities": "Mon_hoc_phan_cong",
    "grade_times": "Thoi_gian_bieu",
    "exam_students": "HS_du_thi",
    "exam_rooms": "Phong_thi",
    "exam_subjects": "Mon_thi",
}
# Các giá trị đơn / cấu hình
GIA_TRI_CAU_HINH = [
    "cfg_num_days", "cfg_periods_per_day", "cfg_morning_count", "cfg_max_seconds",
    "cfg_school_name", "free_depts",
    "ct_period_spread", "ct_room_capacity", "ct_order_group", "ct_dept_free_session", "ct_no_gap",
]


class LoiLuuTru(Exception):
    """Lỗi khi lưu/tải dữ liệu — thông điệp đã viết sẵn cho người dùng."""


# ---------------------------------------------------------------------
# Đóng gói / giải nén dữ liệu phiên làm việc
# ---------------------------------------------------------------------
def _df_sang_json(df: pd.DataFrame) -> dict:
    df = df.astype(object).where(pd.notna(df), None)
    return {"columns": [str(c) for c in df.columns], "data": df.values.tolist()}


def _json_sang_df(obj: dict) -> pd.DataFrame:
    return pd.DataFrame(obj.get("data", []), columns=obj.get("columns", []))


def _mac_dinh_json(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if hasattr(o, "model_dump"):
        return o.model_dump()
    if hasattr(o, "item"):  # numpy scalar
        return o.item()
    return str(o)


def dong_goi(ss) -> dict:
    """Gom toàn bộ dữ liệu cần lưu từ st.session_state thành 1 dict JSON."""
    goi = {
        "phien_ban": PHIEN_BAN_DINH_DANG,
        "thoi_gian_luu": datetime.now().isoformat(timespec="seconds"),
        "bang": {k: _df_sang_json(ss[k]) for k in BANG_DU_LIEU if k in ss},
        "cau_hinh": {k: ss[k] for k in GIA_TRI_CAU_HINH if k in ss},
        "tuan_bat_dau": ss["tuan_bat_dau"].isoformat() if "tuan_bat_dau" in ss else None,
        "ket_qua": {},
    }
    kq = ss.get("result")
    if kq is not None and kq.status not in ("INFEASIBLE", "ERROR"):
        goi["ket_qua"]["tkb"] = {
            "result": kq.model_dump(),
            "classes": [c.model_dump() for c in ss.get("result_classes", [])],
            "config": ss["result_config"].model_dump() if ss.get("result_config") else None,
        }
    if ss.get("exam_results"):
        goi["ket_qua"]["phong_thi"] = ss["exam_results"]
        goi["ket_qua"]["hoc_sinh_thi"] = ss.get("exam_all_students", [])
    if ss.get("substitutions"):
        goi["ket_qua"]["day_thay"] = ss["substitutions"]
    # đi qua json 1 lần để chắc chắn mọi giá trị đều tuần tự hoá được
    return json.loads(json.dumps(goi, default=_mac_dinh_json, ensure_ascii=False))


def giai_nen(goi: dict, ss, TimetableResult, SchoolClass, ScheduleConfig) -> list[str]:
    """Nạp dict đã lưu vào st.session_state. Truyền các class pydantic vào
    để module này không phụ thuộc vòng vào models. Trả về các ghi chú."""
    if not isinstance(goi, dict) or "bang" not in goi:
        raise LoiLuuTru("File không đúng định dạng sao lưu của ứng dụng.")
    ghi_chu = []
    for k, obj in goi.get("bang", {}).items():
        if k in BANG_DU_LIEU:
            ss[k] = _json_sang_df(obj)
            ss.pop(f"editor_{k}", None)
    for k, v in goi.get("cau_hinh", {}).items():
        if k in GIA_TRI_CAU_HINH:
            ss[k] = v
    if goi.get("tuan_bat_dau"):
        ss["tuan_bat_dau"] = date.fromisoformat(goi["tuan_bat_dau"])

    kq = goi.get("ket_qua", {})
    ss["result"], ss["solutions_history"], ss["selected_solution_idx"] = None, [], 0
    if kq.get("tkb"):
        tkb = kq["tkb"]
        result = TimetableResult.model_validate(tkb["result"])
        classes = [SchoolClass.model_validate(c) for c in tkb.get("classes", [])]
        config = ScheduleConfig.model_validate(tkb["config"]) if tkb.get("config") else ScheduleConfig()
        ss["result"], ss["result_classes"], ss["result_config"] = result, classes, config
        ss["solutions_history"] = [{"result": result, "classes": classes, "config": config}]
        ghi_chu.append("Đã nạp kết quả thời khoá biểu.")
    ss["exam_results"] = kq.get("phong_thi", {})
    ss["exam_all_students"] = kq.get("hoc_sinh_thi", [])
    ss["substitutions"] = kq.get("day_thay", {})
    if ss["exam_results"]:
        ghi_chu.append(f"Đã nạp kết quả xếp phòng thi ({len(ss['exam_results'])} môn).")
    return ghi_chu


def sang_excel(goi: dict) -> bytes:
    """Bản Excel dễ đọc: mỗi bảng nhập liệu 1 sheet, cộng các sheet kết quả."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            [{"Mục": "Thời gian lưu", "Giá trị": goi.get("thoi_gian_luu")},
             {"Mục": "Tuần bắt đầu", "Giá trị": goi.get("tuan_bat_dau")}]
            + [{"Mục": k, "Giá trị": json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v}
               for k, v in goi.get("cau_hinh", {}).items()]
        ).to_excel(writer, index=False, sheet_name="Thong_tin")
        for k, obj in goi.get("bang", {}).items():
            _json_sang_df(obj).to_excel(writer, index=False, sheet_name=BANG_DU_LIEU.get(k, k)[:31])

        kq = goi.get("ket_qua", {})
        if kq.get("tkb"):
            ten_lop = {c["id"]: c["name"] for c in kq["tkb"].get("classes", [])}
            pd.DataFrame([
                {"Lớp": ", ".join(ten_lop.get(c, c) for c in l["class_ids"]), "Thứ": l["day"] + 1,
                 "Tiết": l["period"], "Hoạt động": l["activity_name"], "GV": ", ".join(l["teacher_ids"])}
                for l in kq["tkb"]["result"].get("lessons", [])
            ]).sort_values(["Lớp", "Thứ", "Tiết"]).to_excel(writer, index=False, sheet_name="KQ_Thoi_khoa_bieu")
        if kq.get("phong_thi"):
            pd.DataFrame([
                {"Môn thi": mon, "Ngày thi": e.get("ngay"), "Ca thi": e.get("ca"),
                 "Phòng thi": p["ten_phong"], "SBD": hs["sbd"], "Lớp": hs["lop"]}
                for mon, e in kq["phong_thi"].items() for p in e.get("rooms", []) for hs in p["hoc_sinh"]
            ]).to_excel(writer, index=False, sheet_name="KQ_Phong_thi")
    return buf.getvalue()


def ten_file_an_toan(ten: str) -> str:
    """Bỏ các ký tự SharePoint không cho phép trong tên file."""
    ten = re.sub(r'[\\/:*?"<>|#%~&{}]+', "_", (ten or "").strip()).strip(". _")
    return ten[:100] or datetime.now().strftime("TKB_%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------
# Cách 1: Microsoft Graph API (gọi thẳng SharePoint)
# ---------------------------------------------------------------------
class GraphSharePoint:
    ten_hien_thi = "SharePoint (Microsoft Graph)"

    def __init__(self, cfg: dict):
        thieu = [k for k in ("tenant_id", "client_id", "client_secret", "site_url") if not cfg.get(k)]
        if thieu:
            raise LoiLuuTru(f"Mục [sharepoint] trong Secrets còn thiếu: {', '.join(thieu)}.")
        self.cfg = cfg
        self.thu_muc = str(cfg.get("folder") or "TKB_TanPhu").strip("/")
        self._token = None
        self._drive_id = None

    def _lay_token(self) -> str:
        if self._token:
            return self._token
        r = requests.post(
            f"https://login.microsoftonline.com/{self.cfg['tenant_id']}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.cfg["client_id"],
                "client_secret": self.cfg["client_secret"],
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            raise LoiLuuTru(
                "Đăng nhập Microsoft thất bại — kiểm tra tenant_id / client_id / client_secret "
                f"(chi tiết: {r.text[:300]})"
            )
        self._token = r.json()["access_token"]
        return self._token

    def _goi(self, method: str, url: str, **kw) -> requests.Response:
        headers = kw.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._lay_token()}"
        r = requests.request(method, f"https://graph.microsoft.com/v1.0{url}", headers=headers,
                             timeout=TIMEOUT, **kw)
        if r.status_code == 403:
            raise LoiLuuTru(
                "Ứng dụng chưa được cấp quyền ghi vào site SharePoint này (403). Xem bước cấp "
                "quyền Sites.ReadWrite.All / Sites.Selected trong HUONG_DAN_SHAREPOINT.md."
            )
        return r

    def _drive(self) -> str:
        if self._drive_id:
            return self._drive_id
        u = urlparse(self.cfg["site_url"])
        duong_dan = u.path.rstrip("/")
        r = self._goi("GET", f"/sites/{u.hostname}:{duong_dan}" if duong_dan else f"/sites/{u.hostname}")
        if r.status_code != 200:
            raise LoiLuuTru(f"Không tìm thấy site SharePoint '{self.cfg['site_url']}' ({r.status_code}).")
        site_id = r.json()["id"]
        ten_thu_vien = self.cfg.get("library")
        if ten_thu_vien:
            r = self._goi("GET", f"/sites/{site_id}/drives")
            drives = [d for d in r.json().get("value", []) if d.get("name") == ten_thu_vien]
            if not drives:
                raise LoiLuuTru(f"Site không có thư viện tài liệu tên '{ten_thu_vien}'.")
            self._drive_id = drives[0]["id"]
        else:
            r = self._goi("GET", f"/sites/{site_id}/drive")
            self._drive_id = r.json()["id"]
        return self._drive_id

    def _duong_dan(self, ten_file: str) -> str:
        return quote(f"{self.thu_muc}/{ten_file}")

    def luu(self, ten: str, goi: dict) -> str:
        ten = ten_file_an_toan(ten)
        drive = self._drive()
        for duoi, noi_dung, loai in (
            ("json", json.dumps(goi, ensure_ascii=False, indent=1).encode("utf-8"), "application/json"),
            ("xlsx", sang_excel(goi),
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ):
            r = self._goi("PUT", f"/drives/{drive}/root:/{self._duong_dan(f'{ten}.{duoi}')}:/content",
                          data=noi_dung, headers={"Content-Type": loai})
            if r.status_code not in (200, 201):
                raise LoiLuuTru(f"Lưu file {ten}.{duoi} thất bại ({r.status_code}): {r.text[:300]}")
        return f"{self.thu_muc}/{ten}.json"

    def danh_sach(self) -> list[dict]:
        r = self._goi("GET", f"/drives/{self._drive()}/root:/{quote(self.thu_muc)}:/children"
                             "?$select=name,lastModifiedDateTime&$top=200")
        if r.status_code == 404:
            return []  # thư mục chưa có -> chưa lưu lần nào
        if r.status_code != 200:
            raise LoiLuuTru(f"Không đọc được thư mục '{self.thu_muc}' ({r.status_code}).")
        return sorted(
            [{"ten": f["name"][:-5], "sua_luc": f.get("lastModifiedDateTime", "")}
             for f in r.json().get("value", []) if f["name"].lower().endswith(".json")],
            key=lambda x: x["sua_luc"], reverse=True,
        )

    def tai(self, ten: str) -> dict:
        r = self._goi("GET", f"/drives/{self._drive()}/root:/{self._duong_dan(f'{ten}.json')}:/content")
        if r.status_code != 200:
            raise LoiLuuTru(f"Không tải được '{ten}.json' ({r.status_code}).")
        return json.loads(r.content.decode("utf-8-sig"))


# ---------------------------------------------------------------------
# Cách 2: Power Automate (flow HTTP trigger ghi/đọc SharePoint)
# ---------------------------------------------------------------------
class PowerAutomate:
    ten_hien_thi = "SharePoint qua Power Automate"

    def __init__(self, cfg: dict):
        if not cfg.get("save_url"):
            raise LoiLuuTru("Mục [power_automate] trong Secrets còn thiếu save_url.")
        self.cfg = cfg

    def _post(self, khoa_url: str, body: dict) -> requests.Response:
        url = self.cfg.get(khoa_url)
        if not url:
            raise LoiLuuTru(f"Chưa cấu hình {khoa_url} trong mục [power_automate].")
        r = requests.post(url, json=body, timeout=TIMEOUT)
        if r.status_code >= 300:
            raise LoiLuuTru(f"Flow Power Automate trả lỗi {r.status_code}: {r.text[:300]}")
        return r

    def luu(self, ten: str, goi: dict) -> str:
        ten = ten_file_an_toan(ten)
        self._post("save_url", {
            "ten": ten,
            "thoi_gian": goi.get("thoi_gian_luu"),
            "json_text": json.dumps(goi, ensure_ascii=False),
            "excel_base64": base64.b64encode(sang_excel(goi)).decode("ascii"),
        })
        return f"{ten}.json"

    def co_the_tai(self) -> bool:
        return bool(self.cfg.get("list_url") and self.cfg.get("load_url"))

    def danh_sach(self) -> list[dict]:
        data = self._post("list_url", {}).json()
        if isinstance(data, dict):
            data = data.get("value") or data.get("files") or []
        ket_qua = []
        for f in data:
            ten = f.get("ten") or f.get("name") or f.get("Name") or ""
            if ten.lower().endswith(".json"):
                ten = ten[:-5]
            elif "." in ten:
                continue  # bỏ qua file .xlsx
            if ten:
                ket_qua.append({"ten": ten, "sua_luc": f.get("sua_luc") or f.get("LastModified") or ""})
        return sorted(ket_qua, key=lambda x: x["sua_luc"], reverse=True)

    def tai(self, ten: str) -> dict:
        r = self._post("load_url", {"ten": ten})
        data = r.json()
        if isinstance(data, str):  # flow trả về nội dung file dạng chuỗi
            data = json.loads(data)
        if isinstance(data, dict) and "$content" in data:  # nội dung nhị phân base64 của SharePoint
            data = json.loads(base64.b64decode(data["$content"]).decode("utf-8-sig"))
        return data


def tao_ket_noi(secrets) -> list:
    """Đọc st.secrets, trả về danh sách các kết nối đã cấu hình (có thể rỗng)."""
    ket_noi = []
    for khoa, lop in (("sharepoint", GraphSharePoint), ("power_automate", PowerAutomate)):
        try:
            cfg = dict(secrets[khoa]) if khoa in secrets else None
        except Exception:
            cfg = None
        if cfg:
            ket_noi.append((khoa, cfg, lop))
    return ket_noi
