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
    pdf = LHomePDFReport(orientation="P", unit="mm", format="A4")
    
    # 🌟 1. คำนวณหา Path ที่แม่นยำที่สุด
    current_dir = os.path.dirname(os.path.abspath(__file__)) # ตำแหน่งโฟลเดอร์ /src/
    root_dir = os.path.dirname(current_dir) # ถอยกลับมา 1 ชั้น จะเจอโฟลเดอร์หลัก
    
    # ประกอบร่าง Path ไปหาฟอนต์
    font_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew.ttf")
    font_bold_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew-Bold.ttf")
    
    # 🌟 2. ดักจับ Error ก่อนพัง 
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"❌ ค้นหาฟอนต์ไม่พบที่ตำแหน่ง: {font_path} กรุณาเช็คชื่อไฟล์บน GitHub")
    if not os.path.exists(font_bold_path):
        raise FileNotFoundError(f"❌ ค้นหาฟอนต์ไม่พบที่ตำแหน่ง: {font_bold_path}")

    # 3. โหลดฟอนต์เข้า PDF (เอา uni=True ออกตามมาตรฐาน fpdf2)
    pdf.add_font("THSarabun", "", font_path)
    pdf.add_font("THSarabun", "B", font_bold_path)
    
    pdf.add_page()
    
    # 1. ข้อมูลผู้ป่วย (เติมส่วนที่ขาดให้ครบ)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Patient Name:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, str(patient_name), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Facility:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, "LHome (Hospital Home)", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Test Date:")
    pdf.set_font("THSarabun", "", 16)
    # แสดงวันที่จาก Database หรือถ้าไม่มีให้ใช้วันที่ปัจจุบัน
    display_date = str(date_str) if date_str else datetime.now().strftime("%Y-%m-%d")
    pdf.cell(0, 8, display_date, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Test Kit:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, "CYBOW 11M", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # 2. สรุปผล
    pdf.set_fill_color(240, 248, 255)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(0, 8, "- สรุปผลการตรวจ (Conclusion)", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("THSarabun", "", 16)
    pdf.multi_cell(0, 8, str(summary_text))
    pdf.ln(5)

    # 3. ตารางข้อมูล
    pdf.set_font("THSarabun", "B", 14)
    headers = ["พารามิเตอร์", "ค่าที่อ่านได้ (Result)"]
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

    # 🌟 คืนค่าเป็น bytearray สำหรับ Streamlit download_button
    return bytes(pdf.output())