# -*- coding: utf-8 -*-
"""
Test PDF generation with improved layout and fonts
"""
import sys
import io
import os

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pdf_generator import create_pdf
from datetime import datetime

# Sample test data
test_patient_name = "ทดสอบ ระบบใหม่"
test_case_id = "CYBOW-20260814-TEST"
test_date = "2026-08-14"

# Sample table data (Parameter, Result, Reference, Color, Status)
test_table_data = [
    ["Urobilinogen (URO)", "0.2 mg/dL", "≤1 mg/dL", "สีเหลืองอ่อน", "Normal"],
    ["Glucose (GLU)", "neg.", "Negative", "สีฟ้าอ่อน", "Normal"],
    ["Bilirubin (BIL)", "neg.", "Negative", "สีครีม", "Normal"],
    ["Ketones (KET)", "neg.", "Negative", "สีครีม", "Normal"],
    ["Specific Gravity (SG)", "1.020", "1.005-1.030", "สีเขียวเข้ม", "Normal"],
    ["Blood (BLO)", "Hemolysis +++250", "Negative", "สีเขียวเข้มมาก", "Positive (High)"],
    ["pH", "6.0", "5.0-8.0", "สีเหลือง", "Normal"],
    ["Protein (PRO)", "Trace 15 mg/dL", "Negative", "สีเขียวอ่อน", "Positive (Trace)"],
    ["Nitrite (NIT)", "pos.", "Negative", "สีชมพู", "Positive"],
    ["Leukocytes (LEU)", "+++500", "Negative", "สีม่วงเข้ม", "Positive (High)"],
    ["Ascorbic Acid (ASC)", "neg.", "Negative", "สีขาว", "Normal"],
]

test_summary = """พบความผิดปกติที่สำคัญ 4 รายการ ได้แก่ พบเลือดในปัสสาวะระดับสูง (Hemolysis +++250)
พบโปรตีนเล็กน้อย (Trace 15 mg/dL) พบไนไตรท์บวก และพบเม็ดเลือดขาวระดับสูง (+++500)
ซึ่งบ่งชี้ว่าอาจมีการติดเชื้อในระบบทางเดินปัสสาวะ (UTI) และอาจมีการอักเสบหรือบาดเจ็บในไต"""

test_bullets = [
    "พบเลือดในปัสสาวะระดับสูงมาก (Hemolysis +++250) บ่งชี้ว่าอาจมีภาวะไตอักเสบ นิ่วในไต หรือบาดแผลในทางเดินปัสสาวะ",
    "พบไนไตรท์บวก (Positive) ร่วมกับเม็ดเลือดขาวสูง (+++500) บ่งชี้ชัดเจนว่ามีการติดเชื้อแบคทีเรียในระบบทางเดินปัสสาวะ (UTI)",
    "พบโปรตีนในปัสสาวะ (Trace 15 mg/dL) อาจบ่งชี้การทำงานของไตผิดปกติเล็กน้อย หรืออาจเกิดจากการอักเสบ",
    "ควรพบแพทย์โดยเร็วเพื่อรับการรักษาด้วยยาปฏิชีวนะ และตรวจเพิ่มเติมเพื่อหาสาเหตุของเลือดในปัสสาวะ",
]

print("=" * 70)
print("Testing Enhanced PDF Generator")
print("=" * 70)

try:
    pdf_bytes = create_pdf(
        patient_name=test_patient_name,
        case_id=test_case_id,
        date_str=test_date,
        table_data=test_table_data,
        summary_text=test_summary,
        bullet_points=test_bullets
    )

    # Save to file
    output_path = "test_output_improved.pdf"
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"\n✅ PDF สร้างสำเร็จ!")
    print(f"   ขนาดไฟล์: {len(pdf_bytes) / 1024:.1f} KB")
    print(f"   บันทึกที่: {output_path}")
    print(f"\n📋 การปรับปรุง:")
    print(f"   ✓ ขนาดฟอนต์ใหญ่ขึ้นและอ่านง่ายขึ้น")
    print(f"   ✓ กล่องข้อมูลผู้ป่วยมีพื้นหลังสี")
    print(f"   ✓ หัวข้อและหัวตารางเด่นชัดขึ้น")
    print(f"   ✓ ตารางมี spacing ที่ดีขึ้น")
    print(f"   ✓ Status badges ชัดเจนขึ้น")
    print(f"   ✓ ข้อบ่งชี้ทางคลินิกใช้ตัวเลขแทนจุดกลม")

except Exception as e:
    print(f"\n❌ เกิดข้อผิดพลาด: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
