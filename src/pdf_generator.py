import os
from fpdf import FPDF
from datetime import datetime

class LHomePDFReport(FPDF):
    def header(self):
        self.set_font("THSarabun", "B", 20)
        self.cell(0, 10, "รายงานผลวิเคราะห์แถบสีปัสสาวะ", align="C", new_x="LMARGIN", new_y="NEXT") 
        self.set_font("THSarabun", "", 16)
        self.cell(0, 8, "Quantitative Urine Analysis Report (CYBOW 11M)", align="C", new_x="LMARGIN", new_y="NEXT") 
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font("THSarabun", "", 12)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "เอกสารฉบับนี้สร้างโดยระบบ AI สำหรับการประเมินคัดกรองเบื้องต้นเท่านั้น", align="C", new_x="LMARGIN", new_y="NEXT") 
        self.cell(0, 5, "Generated automatically by AI Analysis System LHome Facility", align="C") 

# 🌟 เพิ่มพารามิเตอร์ case_id เข้ามาตรงนี้
def create_pdf(patient_name, case_id, date_str, table_data, summary_text, bullet_points):
    pdf = LHomePDFReport(orientation="P", unit="mm", format="A4")
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    root_dir = os.path.dirname(current_dir) 
    
    # ดึงฟอนต์ (เช็คชื่อไฟล์ให้ตรงกับใน GitHub คือ THSarabunNew-Bold.ttf)
    font_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew.ttf")
    font_bold_path = os.path.join(root_dir, "assets", "fonts", "THSarabunNew-Bold.ttf")
    
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"❌ ค้นหาฟอนต์ไม่พบที่ตำแหน่ง: {font_path} กรุณาเช็คชื่อไฟล์บน GitHub")
    if not os.path.exists(font_bold_path):
        raise FileNotFoundError(f"❌ ค้นหาฟอนต์ไม่พบที่ตำแหน่ง: {font_bold_path}")

    pdf.add_font("THSarabun", "", font_path)
    pdf.add_font("THSarabun", "B", font_bold_path)
    
    pdf.add_page()
    
    # 1. ข้อมูลการตรวจ 
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Facility:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, "LHome (Hospital Home)", new_x="LMARGIN", new_y="NEXT") 
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Patient Name:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, str(patient_name), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Case ID:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, str(case_id), new_x="LMARGIN", new_y="NEXT") 
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Test Date:")
    pdf.set_font("THSarabun", "", 16)
    display_date = str(date_str) if date_str else datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 8, display_date, new_x="LMARGIN", new_y="NEXT") 
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(35, 8, "Test Kit:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, "CYBOW 11M (DFI Co.,Ltd.)", new_x="LMARGIN", new_y="NEXT") 
    pdf.ln(5)
    
    # 2. สรุปผล
    pdf.set_fill_color(240, 248, 255)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(0, 8, "สรุปผลการตรวจ (Conclusion)", new_x="LMARGIN", new_y="NEXT", fill=True) 
    pdf.set_font("THSarabun", "", 16)
    pdf.multi_cell(0, 8, str(summary_text))
    pdf.ln(5)

    # 3. ตารางข้อมูล (4 คอลัมน์)
    pdf.set_font("THSarabun", "B", 14)
    headers = ["พารามิเตอร์", "ค่าที่อ่านได้", "แถบสี (Color)", "สถานะ"] 
    col_widths = [45, 45, 50, 50] 
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align="C")
    pdf.ln(10)

    pdf.set_font("THSarabun", "", 14)
    for row in table_data:
        status_text = str(row[3])
        # ไฮไลท์สีแดงเมื่อพบความผิดปกติ
        if "Normal" not in status_text and status_text.strip() != "":
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 0, 0)
            
        for i, item in enumerate(row):
            pdf.cell(col_widths[i], 10, str(item), border=1, align="C")
        pdf.ln(10)
    pdf.ln(5)

    # 4. ข้อบ่งชี้ทางคลินิกเบื้องต้น
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(0, 8, "ข้อบ่งชี้ทางคลินิกเบื้องต้น (Clinical Notes):", new_x="LMARGIN", new_y="NEXT") 
    pdf.set_font("THSarabun", "", 16)
    for bullet in bullet_points:
        pdf.multi_cell(0, 8, f"• {bullet}") 
        pdf.ln(2)

    # ✅ ใช้ฟังก์ชัน bytes() ป้องกันการพังตอนดาวน์โหลด
    return bytes(pdf.output())