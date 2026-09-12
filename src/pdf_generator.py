import os
from datetime import datetime
from fpdf import FPDF


class LHomePDFReport(FPDF):
    def header(self):
        # Compact A4 header: keep the report professional without consuming
        # space needed by the 11-result table.
        self.set_text_color(30, 58, 138)
        self.set_font("THSarabun", "B", 20)
        self.cell(
            0, 7,
            "รายงานผลวิเคราะห์แถบสีปัสสาวะ (อ้างอิง CYBOW 11M)",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        self.set_text_color(100, 116, 139)
        self.set_font("THSarabun", "", 12)
        self.cell(
            0, 4,
            "Urine Analysis Report • CYBOW 11M (REF 0974)",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.45)
        self.line(10, self.get_y() + 1.5, 200, self.get_y() + 1.5)
        self.ln(4)

    def footer(self):
        self.set_y(-10)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(1)
        self.set_font("THSarabun", "", 9)
        self.set_text_color(130, 130, 130)
        self.cell(
            0, 3.5,
            "เอกสารสร้างโดยระบบสำหรับการประเมินคัดกรองเบื้องต้น • ควรแปลผลร่วมกับข้อมูลทางคลินิก",
            align="C", new_x="LMARGIN", new_y="NEXT",
        )
        self.cell(0, 3, f"LHome Facility • หน้า {self.page_no()}", align="C")


def _compact_text(value, max_chars):
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"


def create_pdf(patient_name, case_id, date_str, table_data, summary_text, bullet_points):
    pdf = LHomePDFReport(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=13)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    font_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew.ttf")
    font_bold_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew-Bold.ttf")
    if not os.path.exists(font_path) or not os.path.exists(font_bold_path):
        raise FileNotFoundError("❌ ค้นหาฟอนต์ไม่พบ กรุณาตรวจสอบโฟลเดอร์ assets/fonts")

    pdf.add_font("THSarabun", "", font_path)
    pdf.add_font("THSarabun", "B", font_bold_path)
    pdf.add_page()

    try:
        pdf.set_text_shaping(True)
    except Exception:
        pass

    # Patient information: two compact rows.
    box_y = pdf.get_y()
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(148, 163, 184)
    pdf.set_line_width(0.35)
    pdf.rect(10, box_y, 190, 16, style="DF")
    pdf.set_xy(14, box_y + 2.2)
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("THSarabun", "B", 13)
    pdf.cell(20, 5, "ชื่อผู้ป่วย:")
    pdf.set_font("THSarabun", "", 13)
    pdf.cell(69, 5, _compact_text(patient_name, 42))
    pdf.set_font("THSarabun", "B", 13)
    pdf.cell(18, 5, "วันที่ตรวจ:")
    pdf.set_font("THSarabun", "", 12)
    display_date = str(date_str) if date_str else datetime.now().strftime("%d/%m/%Y")
    pdf.cell(0, 5, _compact_text(display_date, 30), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("THSarabun", "B", 12)
    pdf.cell(20, 5, "รหัสเคส:")
    pdf.set_font("THSarabun", "", 12)
    pdf.cell(69, 5, _compact_text(case_id, 30))
    pdf.set_font("THSarabun", "B", 12)
    pdf.cell(18, 5, "ชุดตรวจ:")
    pdf.set_font("THSarabun", "", 12)
    pdf.cell(0, 5, "CYBOW 11M (REF 0974)")
    pdf.set_y(box_y + 19)

    # Compact conclusion. The recorded lab values remain unchanged; only
    # narrative text is visually constrained so the result table stays on A4.
    summary = _compact_text(summary_text, 260)
    start_y = pdf.get_y()
    pdf.set_fill_color(254, 242, 242)
    pdf.set_draw_color(220, 38, 38)
    pdf.set_line_width(0.45)
    summary_h = 15 if len(summary) <= 125 else 20
    pdf.rect(10, start_y, 190, summary_h, style="DF")
    pdf.set_xy(14, start_y + 2)
    pdf.set_text_color(185, 28, 28)
    pdf.set_font("THSarabun", "B", 13)
    pdf.cell(0, 4.5, "สรุปผลการตรวจ (Clinical Conclusion)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_text_color(90, 29, 29)
    pdf.set_font("THSarabun", "", 11)
    pdf.multi_cell(182, 4, summary)
    pdf.set_y(start_y + summary_h + 3)

    # Result table: 11 rows fit comfortably on one A4 page.
    col_widths = [45, 40, 34, 43, 28]  # total 190 mm
    headers = ["พารามิเตอร์", "ค่าที่อ่านได้", "ค่ามาตรฐาน", "แถบสี", "สถานะ"]
    row_h = 7.2
    header_h = 7.5

    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("THSarabun", "B", 12)
    pdf.set_draw_color(30, 58, 138)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], header_h, header, border=1, align="C", fill=True)
    pdf.ln(header_h)

    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.25)
    for idx, row in enumerate(table_data):
        pdf.set_fill_color(248, 250, 252) if idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        status_text = str(row[4])
        is_normal = "Normal" in status_text
        for i in range(4):
            pdf.set_font("THSarabun", "B" if i == 0 else "", 10.5)
            if i == 2:
                pdf.set_text_color(100, 116, 139)
            elif not is_normal and status_text != "N/A":
                pdf.set_text_color(185, 28, 28)
            else:
                pdf.set_text_color(15, 23, 42)
            value = _compact_text(row[i], [31, 28, 23, 29][i])
            pdf.cell(col_widths[i], row_h, f" {value}", border="B", align="L", fill=True)

        if is_normal:
            pdf.set_text_color(22, 120, 60)
            badge_text = "Normal"
        elif status_text == "N/A":
            pdf.set_text_color(100, 116, 139)
            badge_text = "N/A"
        elif status_text in ("Positive", "Abnormal") or any(
            token in status_text for token in ("Trace", "Small", "Mod")
        ):
            pdf.set_text_color(194, 65, 12)
            badge_text = "Positive"
        else:
            pdf.set_text_color(185, 28, 28)
            badge_text = "High"
        pdf.set_font("THSarabun", "B", 10)
        pdf.cell(col_widths[4], row_h, badge_text, border="B", align="C", fill=True)
        pdf.ln(row_h)

    # Clinical notes: concise by design. Full lab values above are never
    # removed. If narrative notes are long, show the most actionable first
    # items and mark that additional narrative exists in the stored record.
    bullets = [str(x).strip() for x in (bullet_points or []) if str(x).strip()]
    remaining = max(0.0, 281 - pdf.get_y() - 13)
    if remaining >= 14:
        max_items = 3 if remaining >= 25 else 2
        selected = bullets[:max_items]
        notes = [_compact_text(x, 125) for x in selected]
        if len(bullets) > max_items:
            notes.append("มีคำแนะนำเพิ่มเติมในข้อมูลที่บันทึกในระบบ")
        box_h = min(remaining, 8 + 5 * max(1, len(notes)))
        start_y = pdf.get_y() + 2
        pdf.set_fill_color(239, 246, 255)
        pdf.set_draw_color(59, 130, 246)
        pdf.set_line_width(0.35)
        pdf.rect(10, start_y, 190, box_h, style="DF")
        pdf.set_xy(14, start_y + 1.5)
        pdf.set_text_color(29, 78, 216)
        pdf.set_font("THSarabun", "B", 12)
        pdf.cell(0, 4, "ข้อบ่งชี้ทางคลินิกและคำแนะนำ", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(30, 41, 59)
        pdf.set_font("THSarabun", "", 10.5)
        for idx, bullet in enumerate(notes):
            if pdf.get_y() + 4 > start_y + box_h - 1:
                break
            pdf.set_x(14)
            pdf.cell(182, 4, f"{idx + 1}. {bullet}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
