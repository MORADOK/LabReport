import os
from fpdf import FPDF
from datetime import datetime

class LHomePDFReport(FPDF):
    def header(self):
        self.set_font("THSarabun", "B", 20)
        self.cell(0, 10, "รายงานผลวิเคราะห์แถบสีปัสสาวะ (อ้างอิง CYBOW 11M)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("THSarabun", "", 16)
        self.cell(0, 8, "Quantitative Urine Analysis Report (Calibrated to Standard)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font("THSarabun", "", 12)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "เอกสารฉบับนี้สร้างโดยระบบ AI สำหรับการประเมินคัดกรองเบื้องต้นเท่านั้น", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "Generated automatically by AI Analysis System LHome Facility", align="C")

def create_pdf(patient_name, date_str, table_data, summary_text, bullet_points):
    """ฟังก์ชันสร้าง PDF และคืนค่าเป็น Byte สำหรับให้ Streamlit นำไปดาวน์โหลด"""
    pdf = LHomePDFReport(orientation="P", unit="mm", format="A4")
    
    # อ้างอิง Path ของฟอนต์ให้ทำงานได้ทั้งบน Local และ Cloud
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    font_path = os.path.join(base_dir, "assets", "fonts", "THSarabunNew.ttf")
    font_bold_path = os.path.join(base_dir, "assets", "fonts", "THSarabunNew Bold.ttf")
    
    pdf.add_font("THSarabun", "", font_path, uni=True)
    pdf.add_font("THSarabun", "B", font_bold_path, uni=True)
    
    pdf.add_page()
    
    # 1. ข้อมูลผู้ป่วย
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Patient Name:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, str(patient_name), new_x="LMARGIN", new_y="NEXT")
    # ... (ส่วน Facility, Test Date, Test Kit เหมือนโค้ดก่อนหน้า) ...
    
    # 2. สรุปผล
    pdf.set_fill_color(240, 248, 255)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(0, 8, " ✓ สรุปผลการตรวจ (Conclusion)", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("THSarabun", "", 16)
    pdf.multi_cell(0, 8, str(summary_text))
    pdf.ln(5)

    # 3. ตารางข้อมูล
    pdf.set_font("THSarabun", "B", 14)
    headers = ["พารามิเตอร์", "ค่าที่อ่านได้ (Result)"] # ย่อคอลัมน์ลงเพื่อความกระชับ
    col_widths = [60, 130]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align="C")
    pdf.ln(10)

    pdf.set_font("THSarabun", "", 14)
    for key, val in table_data.items():
        pdf.set_text_color(200, 0, 0) if "Abnormal" in str(val) or "+" in str(val) else pdf.set_text_color(0, 0, 0)
        pdf.cell(col_widths[0], 10, str(key).upper(), border=1, align="C")
        pdf.cell(col_widths[1], 10, str(val), border=1, align="C")
        pdf.ln(10)
    pdf.ln(5)

    # 4. ข้อบ่งชี้
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(0, 8, "ข้อบ่งชี้ทางคลินิกและวิเคราะห์ผล:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("THSarabun", "", 16)
    for bullet in bullet_points:
        pdf.multi_cell(0, 8, f"• {bullet}")
        pdf.ln(2)

    return pdf.output(dest="S") # คืนค่าเป็น String/Bytes แทนการเซฟลงเครื่องโดยตรง