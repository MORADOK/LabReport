import os
from fpdf import FPDF
from datetime import datetime

class LHomePDFReport(FPDF):
    def header(self):
        # 🔵 หัวกระดาษสีน้ำเงินเข้ม (Navy Blue)
        self.set_text_color(30, 58, 138)
        self.set_font("THSarabun", "B", 24)
        self.cell(0, 10, "รายงานผลวิเคราะห์แถบสีปัสสาวะ (อ้างอิง CYBOW 11M)", align="C", new_x="LMARGIN", new_y="NEXT")
        
        self.set_text_color(100, 116, 139)
        self.set_font("THSarabun", "", 16)
        self.cell(0, 8, "Quantitative Urine Analysis Report (Calibrated to Standard)", align="C", new_x="LMARGIN", new_y="NEXT")
        
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.5)
        # self.line(10, self.get_y(), 200, self.get_y()) # Optional dashed line
        
        self.set_font("THSarabun", "", 12)
        self.set_text_color(150, 150, 150)
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
    
    # ==========================================
    # 1. ข้อมูลผู้ป่วย (Grid Layout ฝั่งซ้าย-ขวา)
    # ==========================================
    pdf.set_text_color(51, 65, 85) # Slate 700
    pdf.set_font("THSarabun", "B", 16)
    
    # แถวที่ 1
    pdf.cell(25, 8, "Patient Name:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(70, 8, str(patient_name))
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(25, 8, "Test Date:")
    pdf.set_font("THSarabun", "", 16)
    display_date = str(date_str) if date_str else datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 8, display_date, new_x="LMARGIN", new_y="NEXT")
    
    # แถวที่ 2
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(25, 8, "Facility:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(70, 8, "LHome (Hospital Home)")
    
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(25, 8, "Test Kit:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, "CYBOW 11M", new_x="LMARGIN", new_y="NEXT")
    
    # แถวที่ 3 (Case ID)
    pdf.set_font("THSarabun", "B", 16)
    pdf.cell(25, 8, "Case ID:")
    pdf.set_font("THSarabun", "", 16)
    pdf.cell(0, 8, str(case_id), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # ==========================================
    # 2. กล่องสรุปผล (Conclusion Box สีแดงอ่อน/ชมพู)
    # ==========================================
    pdf.set_fill_color(254, 242, 242) # สีแดงอ่อน (Red 50)
    pdf.set_draw_color(252, 165, 165) # ขอบสีแดง (Red 300)
    pdf.set_line_width(0.5)
    
    # วาดกรอบสี่เหลี่ยมรอบสรุปผล
    start_y = pdf.get_y()
    pdf.rect(10, start_y, 190, 22, style="DF")
    
    pdf.set_y(start_y + 2)
    pdf.set_x(12)
    pdf.set_text_color(185, 28, 28) # สีแดงเข้ม (Red 700)
    pdf.set_font("THSarabun", "B", 18)
    pdf.cell(0, 8, "🚨 สรุปผลการตรวจ (Conclusion)", new_x="LMARGIN", new_y="NEXT", align="L")
    
    pdf.set_x(12)
    pdf.set_font("THSarabun", "", 16)
    # ตัดข้อความให้พอดีกล่อง
    pdf.multi_cell(186, 7, str(summary_text), align="L")
    pdf.ln(8) # เว้นระยะให้ตาราง

    # ==========================================
    # 3. หัวตาราง (Navy Blue Header)
    # ==========================================
    pdf.set_fill_color(30, 64, 175) # Blue 800
    pdf.set_text_color(255, 255, 255) # White
    pdf.set_font("THSarabun", "B", 16)
    pdf.set_draw_color(255, 255, 255) # ซ่อนขอบด้วยสีขาว
    
    # 5 คอลัมน์ (รวมความกว้าง 190mm)
    col_widths = [45, 40, 35, 40, 30] 
    headers = ["พารามิเตอร์", "ค่าที่อ่านได้ (Result)", "ค่ามาตรฐาน (Ref.)", "แถบสี (Color)", "สถานะ"]
    
    for i, header in enumerate(headers):
        # จัดชิดซ้ายยกเว้นสถานะ
        align = "C" if i == 4 else "L" 
        # เติม padding ด้านหน้า
        pdf.cell(col_widths[i], 12, f"  {header}", border=1, align=align, fill=True)
    pdf.ln(12)

    # ==========================================
    # 4. ข้อมูลตาราง และ Status Badges
    # ==========================================
    pdf.set_font("THSarabun", "", 16)
    pdf.set_draw_color(226, 232, 240) # ขอบตารางสีเทาอ่อน
    
    for idx, row in enumerate(table_data):
        # สลับสีพื้นหลังตาราง (Zebra Striping) แบบบางๆ
        if idx % 2 == 0:
            pdf.set_fill_color(248, 250, 252) # Slate 50
        else:
            pdf.set_fill_color(255, 255, 255) # White
            
        status_text = str(row[4])
        
        # คอลัมน์ 1-4 (ตัวหนังสือปกติ)
        pdf.set_text_color(30, 41, 59) if "Normal" in status_text else pdf.set_text_color(185, 28, 28)
        
        for i in range(4):
            # คอลัมน์ Ref เป็นตัวเอียง (Italic) สีเทา เพื่อความโปรเฟสชันนอล
            if i == 2:
                pdf.set_font("THSarabun", "", 15)
                pdf.set_text_color(100, 116, 139)
            else:
                pdf.set_font("THSarabun", "B" if i == 0 else "", 16)
                if "Normal" not in status_text:
                    pdf.set_text_color(185, 28, 28) # แดง
                else:
                    pdf.set_text_color(30, 41, 59) # ดำเทา
            
            pdf.cell(col_widths[i], 12, f"  {str(row[i])}", border="B", align="L", fill=True)
        
        # 🌟 คอลัมน์ 5: Status Badges (ป้ายกำกับสถานะ)
        current_x = pdf.get_x()
        current_y = pdf.get_y()
        
        # วาดพื้นหลังกล่องให้เต็มเซลล์ก่อน
        pdf.cell(col_widths[4], 12, "", border="B", align="C", fill=True)
        
        # กำหนดสีป้ายกำกับ (Badge Colors)
        if "Normal" in status_text:
            pdf.set_fill_color(34, 197, 94)  # เขียว (Green 500)
            badge_text = "Normal"
        elif "Trace" in status_text or "Small" in status_text or "Mod" in status_text:
            pdf.set_fill_color(245, 158, 11) # ส้ม (Amber 500)
            badge_text = "Positive"
        else:
            pdf.set_fill_color(239, 68, 68)  # แดง (Red 500)
            badge_text = "Positive (High)"

        # คำนวณขนาดและตำแหน่งของป้าย (Pill shape)
        pdf.set_font("THSarabun", "B", 14)
        badge_w = pdf.get_string_width(badge_text) + 8 # เผื่อขอบซ้ายขวา
        badge_h = 7
        badge_x = current_x + ((col_widths[4] - badge_w) / 2)
        badge_y = current_y + ((12 - badge_h) / 2)
        
        # วาดสี่เหลี่ยมขอบมน (round_rect ของ fpdf2)
        pdf.round_rect(badge_x, badge_y, badge_w, badge_h, r=3.5, style="F")
        
        # วางข้อความสีขาวทับลงไป
        pdf.set_xy(badge_x, badge_y)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(badge_w, badge_h, badge_text, align="C")
        
        # รีเซ็ตตำแหน่ง Y ไปที่บรรทัดถัดไป
        pdf.set_xy(10, current_y + 12)
        
    pdf.ln(8)

    # ==========================================
    # 5. กล่องข้อบ่งชี้ทางคลินิก (Clinical Notes สีฟ้าอ่อน)
    # ==========================================
    pdf.set_fill_color(240, 249, 255) # สีฟ้าอ่อน (Sky 50)
    pdf.set_draw_color(186, 230, 253) # ขอบสีฟ้า (Sky 200)
    pdf.set_line_width(0.5)
    
    # คำนวณความสูงกล่องตามจำนวน bullet (ประมาณ 8mm ต่อบรรทัด)
    box_height = 12 + (len(bullet_points) * 9)
    start_y = pdf.get_y()
    
    # วาดพื้นหลังกล่องแบบขอบมน
    pdf.round_rect(10, start_y, 190, box_height, r=4, style="DF")
    
    pdf.set_y(start_y + 3)
    pdf.set_x(12)
    pdf.set_text_color(3, 105, 161) # สีน้ำเงินเข้ม (Sky 700)
    pdf.set_font("THSarabun", "B", 18)
    pdf.cell(0, 8, "📝 ข้อบ่งชี้ทางคลินิกและวิเคราะห์ผลอย่างละเอียด:", new_x="LMARGIN", new_y="NEXT", align="L")
    
    pdf.set_text_color(51, 65, 85) # Slate 700
    pdf.set_font("THSarabun", "", 16)
    for bullet in bullet_points:
        pdf.set_x(15)
        pdf.multi_cell(180, 8, f"• {bullet}")

    return bytes(pdf.output())