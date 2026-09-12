"""
Tiện ích xuất/nhập dữ liệu:
  - Excel (.xlsx) cho từng bảng nhập liệu (đọc/ghi qua pandas + openpyxl).
  - PDF cho thời khoá biểu kết quả (qua reportlab, font DejaVu Sans hỗ trợ
    đầy đủ dấu tiếng Việt, nhúng sẵn trong assets/ để chạy được cả khi
    deploy lên Streamlit Cloud).
"""

from __future__ import annotations

import io
import os

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Tông màu chủ đạo: xanh đậm (navy) + xám — dùng chung cho Excel lẫn PDF.
NAVY = "12294B"
NAVY_HEX = colors.HexColor(f"#{NAVY}")
ACCENT_HEX = colors.HexColor("#2C5282")
LIGHT_GRAY_HEX = colors.HexColor("#F2F4F7")
MID_GRAY_HEX = colors.HexColor("#D9DEE4")
TEXT_GRAY_HEX = colors.HexColor("#33404F")

_FONTS_READY = False


def _ensure_fonts():
    global _FONTS_READY
    if _FONTS_READY:
        return
    pdfmetrics.registerFont(TTFont("VN", os.path.join(ASSETS_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("VN-Bold", os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf")))
    _FONTS_READY = True


# ---------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------
def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    """Xuất 1 DataFrame ra bytes .xlsx, có style header xanh đậm/chữ trắng."""
    safe_sheet = (sheet_name or "Data")[:31]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=safe_sheet)
        ws = writer.sheets[safe_sheet]
        header_fill = PatternFill("solid", fgColor=NAVY)
        header_font = Font(color="FFFFFF", bold=True)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.freeze_panes = "A2"
        for col_cells in ws.columns:
            length = max(
                (len(str(c.value)) if c.value is not None else 0 for c in col_cells),
                default=8,
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(max(length + 3, 12), 48)
    return buf.getvalue()


# ---------------------------------------------------------------------
# PDF — thời khoá biểu kết quả
# ---------------------------------------------------------------------
def timetable_to_pdf_bytes(
    classes, config, lessons, day_names, teacher_id_to_name,
    dept_free_sessions=None, school_name: str = "",
    period_labels_by_class: dict | None = None,
) -> bytes:
    _ensure_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=1.1 * cm, rightMargin=1.1 * cm, topMargin=1.1 * cm, bottomMargin=1.1 * cm,
    )
    usable_width = doc.width

    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleVN", parent=base_styles["Title"], fontName="VN-Bold",
        fontSize=18, textColor=NAVY_HEX, spaceAfter=4, alignment=0,
    )
    sub_style = ParagraphStyle(
        "SubVN", parent=base_styles["Normal"], fontName="VN",
        fontSize=10, textColor=TEXT_GRAY_HEX, spaceAfter=10,
    )
    class_title_style = ParagraphStyle(
        "ClassVN", parent=base_styles["Heading2"], fontName="VN-Bold",
        fontSize=13, textColor=colors.white, backColor=NAVY_HEX,
        spaceAfter=8, spaceBefore=2, leftIndent=6, borderPadding=(6, 6, 6, 6),
    )
    cell_style = ParagraphStyle(
        "CellVN", parent=base_styles["Normal"], fontName="VN",
        fontSize=8, leading=10, textColor=TEXT_GRAY_HEX, alignment=1,
    )
    period_style = ParagraphStyle(
        "PeriodVN", parent=cell_style, fontName="VN-Bold", textColor=NAVY_HEX,
    )
    header_cell_style = ParagraphStyle(
        "HeadCellVN", parent=base_styles["Normal"], fontName="VN-Bold",
        fontSize=9, leading=11, textColor=colors.white, alignment=1,
    )

    divider_style = ParagraphStyle(
        "DividerVN", parent=base_styles["Normal"], fontName="VN-Bold",
        fontSize=8.5, leading=11, textColor=NAVY_HEX, alignment=1,
    )
    DIVIDER_BG_HEX = colors.HexColor("#E7ECF3")

    elements = []
    periods = list(range(1, config.periods_per_day + 1))
    days = config.days

    def _rows_with_session_dividers():
        morning = [p for p in periods if p in config.morning_periods]
        afternoon = [p for p in periods if p in config.afternoon_periods]
        other = [p for p in periods if p not in config.morning_periods and p not in config.afternoon_periods]
        rows = []
        if morning:
            rows.append(("divider", "BUỔI SÁNG"))
            rows.extend(("period", p) for p in morning)
        if afternoon:
            rows.append(("divider", "BUỔI CHIỀU"))
            rows.extend(("period", p) for p in afternoon)
        for p in other:
            rows.append(("period", p))
        return rows

    header_title = (f"{school_name} — " if school_name else "") + "Thời Khoá Biểu"
    elements.append(Paragraph(header_title, title_style))
    if dept_free_sessions:
        free_txt = " · ".join(f"{k}: {v}" for k, v in dept_free_sessions.items())
        elements.append(Paragraph(f"Buổi trống chung theo tổ chuyên môn: {free_txt}", sub_style))
    else:
        elements.append(Spacer(1, 6))

    for idx, c in enumerate(classes):
        elements.append(Paragraph(f"Lớp {c.name}", class_title_style))

        labels_for_c = (period_labels_by_class or {}).get(c.id, {})

        grid = {p: {d: "" for d in days} for p in periods}
        for lesson in lessons:
            if c.id in lesson.class_ids and lesson.period in grid and lesson.day in grid[lesson.period]:
                t_names = ", ".join(teacher_id_to_name.get(tid, tid) for tid in lesson.teacher_ids)
                text = lesson.activity_name
                if t_names:
                    text += f"<br/><font size=7 color='#5A6B80'>{t_names}</font>"
                grid[lesson.period][lesson.day] = text

        header_row = [Paragraph("Tiết", header_cell_style)] + [
            Paragraph(day_names.get(d, str(d)), header_cell_style) for d in days
        ]
        data_rows = [header_row]
        divider_row_indices = []
        for item_type, val in _rows_with_session_dividers():
            if item_type == "divider":
                data_rows.append([Paragraph(val, divider_style)] + [""] * len(days))
                divider_row_indices.append(len(data_rows) - 1)
                continue
            p = val
            p_label = labels_for_c.get(p, f"Tiết {p}")
            row = [Paragraph(p_label, period_style)]
            for d in days:
                text = grid[p][d]
                row.append(Paragraph(text, cell_style) if text else Paragraph("—", cell_style))
            data_rows.append(row)

        has_time_labels = any(
            "(" in (labels_for_c.get(p, "")) for p in periods
        )
        period_col_w = (3.1 if has_time_labels else 1.8) * cm
        day_col_w = (usable_width - period_col_w) / max(len(days), 1)
        col_widths = [period_col_w] + [day_col_w] * len(days)

        table_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEX),
            ("GRID", (0, 0), (-1, -1), 0.6, MID_GRAY_HEX),
            ("BOX", (0, 0), (-1, -1), 1.0, NAVY_HEX),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY_HEX]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for r in divider_row_indices:
            table_style_cmds.append(("SPAN", (0, r), (-1, r)))
            table_style_cmds.append(("BACKGROUND", (0, r), (-1, r), DIVIDER_BG_HEX))

        table = Table(data_rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle(table_style_cmds))
        elements.append(table)
        if idx < len(classes) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    return buf.getvalue()


# ---------------------------------------------------------------------
# Excel — kết quả xếp phòng thi
# ---------------------------------------------------------------------
def exam_rooms_to_excel_bytes(mon_thi: str, ngay_thi: str, ca_thi: str, ket_qua: list[dict]) -> bytes:
    """ket_qua: list[dict] {"ten_phong", "hoc_sinh": [{"sbd","ho_ten","lop"}, ...]}
    Mỗi phòng 1 sheet, cộng thêm 1 sheet 'Tong_hop' gộp toàn bộ."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        header_fill = PatternFill("solid", fgColor=NAVY)
        header_font = Font(color="FFFFFF", bold=True)

        tong_hop_rows = []
        for phong in ket_qua:
            df = pd.DataFrame([
                {"SBD": hs["sbd"], "Họ và tên": hs["ho_ten"], "Lớp": hs["lop"], "Môn thi": mon_thi}
                for hs in phong["hoc_sinh"]
            ])
            sheet_name = str(phong["ten_phong"])[:31]
            df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=2)
            ws = writer.sheets[sheet_name]
            ws["A1"] = f"Môn thi: {mon_thi}    Ngày thi: {ngay_thi}    Ca thi: {ca_thi}    Phòng: {phong['ten_phong']}"
            ws["A1"].font = Font(bold=True, color=NAVY)
            for cell in ws[3]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions["A"].width = 14
            ws.column_dimensions["B"].width = 28
            ws.column_dimensions["C"].width = 14
            ws.column_dimensions["D"].width = 18
            for hs in phong["hoc_sinh"]:
                tong_hop_rows.append({
                    "Phòng thi": phong["ten_phong"], "SBD": hs["sbd"],
                    "Họ và tên": hs["ho_ten"], "Lớp": hs["lop"], "Môn thi": mon_thi,
                })

        if tong_hop_rows:
            df_tong = pd.DataFrame(tong_hop_rows)
            df_tong.to_excel(writer, index=False, sheet_name="Tong_hop")
            ws2 = writer.sheets["Tong_hop"]
            for cell in ws2[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            for col, w in zip("ABCDE", [16, 14, 28, 14, 18]):
                ws2.column_dimensions[col].width = w
    return buf.getvalue()


# ---------------------------------------------------------------------
# PDF — danh sách theo phòng thi + thẻ báo danh
# ---------------------------------------------------------------------
def _sap_xep_luoi(hoc_sinh_trong_phong: list[dict], so_cot: int) -> list[list]:
    """Bản sao nhỏ gọn của exam_rooms.sap_xep_so_do_cho_ngoi — tách riêng ở
    đây để exports.py không cần phụ thuộc chéo vào module exam_rooms."""
    so_cot = max(int(so_cot), 1)
    hang_ghe = []
    for i in range(0, len(hoc_sinh_trong_phong), so_cot):
        nhom = list(hoc_sinh_trong_phong[i:i + so_cot])
        while len(nhom) < so_cot:
            nhom.append(None)
        hang_ghe.append(nhom)
    return hang_ghe


def exam_rooms_to_pdf_bytes(
    mon_thi: str, ngay_thi: str, ca_thi: str, ket_qua: list[dict], school_name: str = "",
) -> bytes:
    _ensure_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm,
    )
    usable_width = doc.width

    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleVN2", parent=base_styles["Title"], fontName="VN-Bold",
        fontSize=17, textColor=NAVY_HEX, spaceAfter=2, alignment=1,
    )
    sub_style = ParagraphStyle(
        "SubVN2", parent=base_styles["Normal"], fontName="VN",
        fontSize=10.5, textColor=TEXT_GRAY_HEX, spaceAfter=4, alignment=1,
    )
    room_title_style = ParagraphStyle(
        "RoomVN", parent=base_styles["Heading2"], fontName="VN-Bold",
        fontSize=13, textColor=colors.white, backColor=NAVY_HEX,
        spaceAfter=8, spaceBefore=2, leftIndent=6, borderPadding=(6, 6, 6, 6),
    )
    cell_style = ParagraphStyle(
        "CellVN2", parent=base_styles["Normal"], fontName="VN",
        fontSize=9.5, leading=12, textColor=TEXT_GRAY_HEX,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCellVN2", parent=cell_style, fontName="VN-Bold",
        textColor=colors.white, alignment=1,
    )
    card_style = ParagraphStyle(
        "CardVN", parent=base_styles["Normal"], fontName="VN",
        fontSize=9, leading=13, textColor=TEXT_GRAY_HEX,
    )
    card_sbd_style = ParagraphStyle(
        "CardSbdVN", parent=card_style, fontName="VN-Bold", fontSize=15, textColor=NAVY_HEX,
    )

    elements = []
    header_title = (f"{school_name}" if school_name else "") 
    if header_title:
        elements.append(Paragraph(header_title, sub_style))
    elements.append(Paragraph(f"DANH SÁCH PHÒNG THI — {mon_thi}", title_style))
    elements.append(Paragraph(f"Ngày thi: {ngay_thi}  ·  Ca thi: {ca_thi}", sub_style))
    elements.append(Spacer(1, 10))

    # ---------------- Trang 1..N: danh sách theo từng phòng ----------------
    for idx, phong in enumerate(ket_qua):
        elements.append(Paragraph(f"Phòng thi: {phong['ten_phong']}  (Sĩ số: {len(phong['hoc_sinh'])})", room_title_style))
        header_row = [
            Paragraph("SBD", header_cell_style),
            Paragraph("Họ và tên", header_cell_style),
            Paragraph("Lớp", header_cell_style),
            Paragraph("Ký tên", header_cell_style),
        ]
        data_rows = [header_row]
        for hs in phong["hoc_sinh"]:
            data_rows.append([
                Paragraph(hs["sbd"], cell_style),
                Paragraph(hs["ho_ten"], cell_style),
                Paragraph(hs["lop"], cell_style),
                Paragraph("", cell_style),
            ])
        col_widths = [usable_width * 0.18, usable_width * 0.42, usable_width * 0.18, usable_width * 0.22]
        table = Table(data_rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEX),
            ("GRID", (0, 0), (-1, -1), 0.6, MID_GRAY_HEX),
            ("BOX", (0, 0), (-1, -1), 1.0, NAVY_HEX),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY_HEX]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)

        # ---------------- Sơ đồ chỗ ngồi ----------------
        so_cot = int(phong.get("so_cot") or 4)
        hs_cho_so_do = phong.get("hoc_sinh_cho_ngoi") or phong["hoc_sinh"]
        hang_ghe = _sap_xep_luoi(hs_cho_so_do, so_cot)
        if hang_ghe:
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("Sơ đồ chỗ ngồi (xếp ngẫu nhiên theo SBD)", room_title_style))

            board_style = ParagraphStyle(
                "BoardVN", parent=base_styles["Normal"], fontName="VN-Bold",
                fontSize=10, textColor=colors.white, alignment=1,
            )
            seat_sbd_style = ParagraphStyle(
                "SeatSbdVN", parent=base_styles["Normal"], fontName="VN-Bold",
                fontSize=10.5, textColor=NAVY_HEX, alignment=1,
            )
            seat_name_style = ParagraphStyle(
                "SeatNameVN", parent=base_styles["Normal"], fontName="VN",
                fontSize=7.5, textColor=TEXT_GRAY_HEX, alignment=1, leading=9,
            )

            board_row = [Paragraph("BẢNG / BỤC GIẢNG", board_style)]
            seat_rows = [board_row]
            for hang in hang_ghe:
                row_cells = []
                for o in hang:
                    if o is None:
                        row_cells.append(Paragraph("", seat_name_style))
                    else:
                        noi_dung = f'<b>{o["sbd"]}</b><br/><font size=7.5>{o["ho_ten"]}</font>'
                        row_cells.append(Paragraph(noi_dung, seat_sbd_style))
                seat_rows.append(row_cells)

            seat_col_w = usable_width / so_cot
            seat_table = Table(
                seat_rows, colWidths=[seat_col_w] * so_cot,
                rowHeights=[0.8 * cm] + [1.35 * cm] * len(hang_ghe),
            )
            seat_style_cmds = [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEX),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 1), (-1, -1), 1.0, NAVY_HEX),
                ("INNERGRID", (0, 1), (-1, -1), 0.75, MID_GRAY_HEX),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            seat_table.setStyle(TableStyle(seat_style_cmds))
            elements.append(seat_table)

        if idx < len(ket_qua) - 1:
            elements.append(PageBreak())

    # ---------------- Trang thẻ báo danh (lưới 2x4 mỗi trang) ----------------
    elements.append(PageBreak())
    elements.append(Paragraph("THẺ BÁO DANH", title_style))
    elements.append(Spacer(1, 8))

    the_bao_danh = []
    for phong in ket_qua:
        for hs in phong["hoc_sinh"]:
            noi_dung = (
                f'<font name="VN-Bold" size=8 color="#69758A">SỐ BÁO DANH</font><br/>'
                f'<font name="VN-Bold" size=17 color="#12294B">{hs["sbd"]}</font><br/>'
                f'<font name="VN-Bold" size=10.5>{hs["ho_ten"]}</font><br/>'
                f'Lớp: {hs["lop"]}<br/>'
                f'Phòng thi: <b>{phong["ten_phong"]}</b><br/>'
                f'Môn: {mon_thi}<br/>'
                f'Ngày thi: {ngay_thi} — Ca {ca_thi}'
            )
            the_bao_danh.append(Paragraph(noi_dung, card_style))

    SO_COT = 2
    hang = []
    card_w = usable_width / SO_COT
    for i in range(0, len(the_bao_danh), SO_COT):
        hang_hien_tai = the_bao_danh[i:i + SO_COT]
        while len(hang_hien_tai) < SO_COT:
            hang_hien_tai.append(Paragraph("", card_style))
        hang.append(hang_hien_tai)

    if hang:
        card_table = Table(hang, colWidths=[card_w] * SO_COT)
        card_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, MID_GRAY_HEX),
            ("INNERGRID", (0, 0), (-1, -1), 0.8, MID_GRAY_HEX),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        elements.append(card_table)

    doc.build(elements)
    return buf.getvalue()


# ---------------------------------------------------------------------
# PDF — bảng phân công dạy thay
# ---------------------------------------------------------------------
def substitution_to_pdf_bytes(
    ngay_hien_thi: str, ds_phan_cong: list[dict], school_name: str = "",
) -> bytes:
    """ds_phan_cong: list[dict] {"tiet", "lop", "mon", "gv_nghi", "gv_thay"}"""
    _ensure_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm,
    )
    usable_width = doc.width
    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleVN3", parent=base_styles["Title"], fontName="VN-Bold",
        fontSize=17, textColor=NAVY_HEX, spaceAfter=2, alignment=1,
    )
    sub_style = ParagraphStyle(
        "SubVN3", parent=base_styles["Normal"], fontName="VN",
        fontSize=10.5, textColor=TEXT_GRAY_HEX, spaceAfter=10, alignment=1,
    )
    cell_style = ParagraphStyle(
        "CellVN3", parent=base_styles["Normal"], fontName="VN",
        fontSize=9.5, leading=12, textColor=TEXT_GRAY_HEX,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCellVN3", parent=cell_style, fontName="VN-Bold",
        textColor=colors.white, alignment=1,
    )

    elements = []
    if school_name:
        elements.append(Paragraph(school_name, sub_style))
    elements.append(Paragraph("BẢNG PHÂN CÔNG DẠY THAY", title_style))
    elements.append(Paragraph(f"Ngày: {ngay_hien_thi}", sub_style))

    header_row = [
        Paragraph("Tiết", header_cell_style),
        Paragraph("Lớp", header_cell_style),
        Paragraph("Môn", header_cell_style),
        Paragraph("GV nghỉ", header_cell_style),
        Paragraph("GV dạy thay", header_cell_style),
    ]
    data_rows = [header_row]
    for pc in ds_phan_cong:
        data_rows.append([
            Paragraph(str(pc["tiet"]), cell_style),
            Paragraph(pc["lop"], cell_style),
            Paragraph(pc["mon"], cell_style),
            Paragraph(pc["gv_nghi"], cell_style),
            Paragraph(pc.get("gv_thay") or "— (chưa phân công) —", cell_style),
        ])

    col_widths = [
        usable_width * 0.10, usable_width * 0.16, usable_width * 0.20,
        usable_width * 0.27, usable_width * 0.27,
    ]
    table = Table(data_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEX),
        ("GRID", (0, 0), (-1, -1), 0.6, MID_GRAY_HEX),
        ("BOX", (0, 0), (-1, -1), 1.0, NAVY_HEX),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY_HEX]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    return buf.getvalue()
