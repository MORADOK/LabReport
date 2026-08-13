import os
from fpdf import FPDF
from datetime import datetime

class LHomePDFReport(FPDF):
    def header(self):
        # 🔵 หัวกระดาษสีน้ำเงินเข้ม (Navy Blue) - ขนาดใหญ่ขึ้นและเด่นชัดขึ้น
        self.set_text_color(30, 58, 138)
        self.set_font("THSarabun", "B", 26)
        self.cell(0, 12, "รายงานผลวิเคราะห์แถบสีปัสสาวะ (อ้างอิง CYBOW 11M)", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(100, 116, 139)
        self.set_font("THSarabun", "", 17)
        self.cell(0, 9, "Quantitative Urine Analysis Report (Calibrated to Standard)", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.8)
        self.line(10, self.get_y() + 3, 200, self.get_y() + 3)
        self.ln(10)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.5)

        self.set_font("THSarabun", "", 12)
        self.set_text_color(150, 150, 150)
        # ✅ แก้ไข: ใช้คำว่า "สำหรับ" ที่ถูกต้อง (ไม่ใช่ "สำnหรับ")
        self.cell(0, 6, "เอกสารฉบับนี้สร้างโดยระบบ AI สำหรับการประเมินคัดกรองเบื้องต้นเท่านั้น", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "Generated automatically by AI Analysis System • LHome Facility", align="C")

def create_pdf(patient_name, case_id, date_str, table_data, summary_text, bullet_points):
    pdf = LHomePDFReport(orientation="P", unit="mm", format="A4")
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    root_dir = os.path.dirname(current_dir) 
    
    font_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew.ttf")
    font_bold_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew-Bold.ttf")
    
    if not os.path.exists(font_path) or not os.path.exists(font_bold_path):
        raise FileNotFoundError("❌ ค้นหาฟอนต์ไม่พบ กรุณาตรวจสอบโฟลเดอร์ assets/fonts")

    pdf.add_font("THSarabun", "", font_path)
    pdf.add_font("THSarabun", "B", font_bold_path)
    pdf.add_page()

    # 🌟 เปิดใช้งาน Text Shaping เพื่อจัดการวรรณยุกต์ภาษาไทยให้ดีขึ้น
    # (ต้องลง uharfbuzz และ fpdf2>=2.8.8 ก่อน)
    try:
        pdf.set_text_shaping(True)
    except (AttributeError, ImportError, Exception):
        # ถ้า uharfbuzz ไม่ได้ลงหรือเวอร์ชันไม่รองรับ ก็ข้ามไป
        # PDF จะยังสร้างได้ แต่อาจมีปัญหาวรรณยุกต์บางตัว
        pass
    
    # ==========================================
    # 1. กล่องข้อมูลผู้ป่วย (Patient Information Box)
    # ==========================================
    pdf.set_fill_color(241, 245, 249)  # สีฟ้าอ่อนมาก (Slate 100)
    pdf.set_draw_color(148, 163, 184)  # ขอบสีเทา (Slate 400)
    pdf.set_line_width(0.5)

    box_y = pdf.get_y()
    pdf.rect(10, box_y, 190, 30, style="DF")

    pdf.set_y(box_y + 5)
    pdf.set_x(15)
    pdf.set_text_color(30, 41, 59)  # Slate 800
    pdf.set_font("THSarabun", "B", 18)

    # แถวที่ 1
    pdf.cell(35, 8, "ชื่อผู้ป่วย:")
    pdf.set_font("THSarabun", "", 18)
    pdf.set_text_color(15, 23, 42)  # Slate 900
    pdf.cell(60, 8, str(patient_name))

    pdf.set_font("THSarabun", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(32, 8, "วันที่ตรวจ:")
    pdf.set_font("THSarabun", "", 18)
    pdf.set_text_color(15, 23, 42)
    display_date = str(date_str) if date_str else datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 8, display_date, new_x="LMARGIN", new_y="NEXT")

    # แถวที่ 2
    pdf.set_x(15)
    pdf.set_font("THSarabun", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(35, 8, "สถานที่:")
    pdf.set_font("THSarabun", "", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(60, 8, "LHome (Hospital Home)")

    pdf.set_font("THSarabun", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(32, 8, "ชุดตรวจ:")
    pdf.set_font("THSarabun", "", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "CYBOW 11M", new_x="LMARGIN", new_y="NEXT")

    # แถวที่ 3 (Case ID)
    pdf.set_x(15)
    pdf.set_font("THSarabun", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(35, 8, "รหัสเคส:")
    pdf.set_font("THSarabun", "", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, str(case_id), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    
    # ==========================================
    # 2. กล่องสรุปผล (Conclusion Box) - ปรับปรุงให้โดดเด่นขึ้น
    # ==========================================
    pdf.set_fill_color(254, 242, 242) # สีแดงอ่อน (Red 50)
    pdf.set_draw_color(220, 38, 38) # ขอบสีแดงเข้มขึ้น (Red 600)
    pdf.set_line_width(1.0)

    start_y = pdf.get_y()
    # คำนวณความสูงอัตโนมัติตามความยาวของข้อความ
    summary_lines = len(str(summary_text)) // 90 + 1  # ประมาณการจำนวนบรรทัด
    box_height = 16 + (summary_lines * 8)

    pdf.rect(10, start_y, 190, box_height, style="DF")

    pdf.set_y(start_y + 4)
    pdf.set_x(15)
    pdf.set_text_color(185, 28, 28) # สีแดงเข้ม (Red 700)
    pdf.set_font("THSarabun", "B", 20)
    pdf.cell(0, 9, "🚨 สรุปผลการตรวจ (Clinical Conclusion)", new_x="LMARGIN", new_y="NEXT", align="L")

    pdf.set_x(15)
    pdf.set_text_color(127, 29, 29)  # Red 900
    pdf.set_font("THSarabun", "", 18)
    pdf.multi_cell(180, 8, str(summary_text), align="L")
    pdf.ln(10)

    # ==========================================
    # 3. หัวตาราง (Navy Blue Header) - ปรับขนาดและสีให้โดดเด่น
    # ==========================================
    pdf.set_fill_color(30, 58, 138) # Blue 900 - เข้มขึ้น
    pdf.set_text_color(255, 255, 255) # White
    pdf.set_font("THSarabun", "B", 18)  # ฟอนต์ใหญ่ขึ้น
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(0.5)

    col_widths = [48, 42, 35, 38, 27]
    headers = ["พารามิเตอร์", "ค่าที่อ่านได้", "ค่ามาตรฐาน", "แถบสี", "สถานะ"]

    for i, header in enumerate(headers):
        align = "C" if i == 4 else "L"
        pdf.cell(col_widths[i], 13, f"  {header}", border=1, align=align, fill=True)
    pdf.ln(13)

    # ==========================================
    # 4. ข้อมูลตาราง และ Status Badges - ปรับให้อ่านง่ายขึ้น
    # ==========================================
    pdf.set_font("THSarabun", "", 17)  # ฟอนต์ใหญ่ขึ้น
    pdf.set_draw_color(203, 213, 225) # ขอบตารางสีเทาอ่อน (Slate 300)
    pdf.set_line_width(0.3)

    for idx, row in enumerate(table_data):
        if idx % 2 == 0:
            pdf.set_fill_color(248, 250, 252) # Slate 50
        else:
            pdf.set_fill_color(255, 255, 255) # White

        status_text = str(row[4])

        for i in range(4):
            if i == 2:
                pdf.set_font("THSarabun", "", 16)
                pdf.set_text_color(100, 116, 139)
            else:
                pdf.set_font("THSarabun", "B" if i == 0 else "", 17)
                if "Normal" not in status_text:
                    pdf.set_text_color(185, 28, 28) # แดง
                else:
                    pdf.set_text_color(15, 23, 42) # ดำเข้ม (Slate 900)

            pdf.cell(col_widths[i], 13, f"  {str(row[i])}", border="B", align="L", fill=True)
        
        # 🌟 คอลัมน์ 5: Status Badges (ป้ายกำกับสถานะแบบ Flat UI) - ปรับให้ชัดเจนขึ้น
        current_x = pdf.get_x()
        current_y = pdf.get_y()

        pdf.cell(col_widths[4], 13, "", border="B", align="C", fill=True)

        if "Normal" in status_text:
            pdf.set_fill_color(22, 163, 74)  # เขียวเข้มขึ้น (Green 600)
            badge_text = "Normal"
        elif "Trace" in status_text or "Small" in status_text or "Mod" in status_text:
            pdf.set_fill_color(234, 88, 12) # ส้มเข้มขึ้น (Orange 600)
            badge_text = "Positive"
        else:
            pdf.set_fill_color(220, 38, 38)  # แดงเข้มขึ้น (Red 600)
            badge_text = "High"

        pdf.set_font("THSarabun", "B", 15)
        badge_w = pdf.get_string_width(badge_text) + 10
        badge_h = 8
        badge_x = current_x + ((col_widths[4] - badge_w) / 2)
        badge_y = current_y + ((13 - badge_h) / 2)

        pdf.rect(badge_x, badge_y, badge_w, badge_h, style="F")

        pdf.set_xy(badge_x, badge_y + 0.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(badge_w, badge_h - 1, badge_text, align="C")

        pdf.set_xy(10, current_y + 13)

    pdf.ln(10)

    # ==========================================
    # 5. กล่องข้อบ่งชี้ทางคลินิก (Clinical Notes) - ปรับให้อ่านง่ายขึ้น
    # ==========================================
    pdf.set_fill_color(239, 246, 255) # สีฟ้าอ่อน (Blue 50)
    pdf.set_draw_color(59, 130, 246) # ขอบสีฟ้าเข้ม (Blue 500)
    pdf.set_line_width(0.8)

    # คำนวณความสูงอัตโนมัติ
    box_height = 18 + (len(bullet_points) * 10)
    start_y = pdf.get_y()

    pdf.rect(10, start_y, 190, box_height, style="DF")

    pdf.set_y(start_y + 5)
    pdf.set_x(15)
    pdf.set_text_color(29, 78, 216) # สีน้ำเงินเข้ม (Blue 700)
    pdf.set_font("THSarabun", "B", 20)
    pdf.cell(0, 9, "📋 ข้อบ่งชี้ทางคลินิกและคำแนะนำ (Clinical Indications)", new_x="LMARGIN", new_y="NEXT", align="L")

    pdf.set_text_color(30, 41, 59) # Slate 800
    pdf.set_font("THSarabun", "", 18)
    for idx, bullet in enumerate(bullet_points):
        pdf.set_x(18)
        pdf.multi_cell(177, 9, f"{idx+1}. {bullet}")

    return bytes(pdf.output())