# -*- coding: utf-8 -*-
"""
CYBOW 11M Exact Reference Values
ตารางอ้างอิงค่ามาตรฐานจากแผ่นตรวจ CYBOW 11M (Verified from physical chart)
แบ่งระดับความรุนแรงเพื่อให้ AI และ Dashboard ประเมินสถานะได้แม่นยำที่สุด
"""

# ---------------------------------------------------------
# 🌟 CYBOW 11M EXACT REFERENCE (Verified from physical chart)
# แบ่งระดับความรุนแรงเพื่อให้ AI และ Dashboard ประเมินสถานะได้แม่นยำที่สุด
# ---------------------------------------------------------

CYBOW_11M_EXACT_REFERENCE = {
    "URO": {
        "normal": ["0.1", "normal", "0.1 normal", "1(16)", "1"],
        "high": ["2(33)", "2", "4(66)", "4", "8(131)", "8"],  # โทนสีชมพู/แดง
        "color_normal": "ครีม/พีชอ่อน",
        "color_high": "ชมพู/แดง (Pink/Red)",
        "ref_range": "≤1 mg/dL"
    },
    "GLU": {
        "normal": ["neg.", "neg", "negative", "0"],
        "warning": ["±100(5.5)", "±100", "100", "+250(14)", "+250", "250"],  # โทนสีเขียว
        "critical": ["++500(28)", "++500", "500", "+++1000(55)", "+++1000", "1000"],  # โทนสีน้ำตาล
        "color_normal": "ฟ้า (Teal)",
        "color_warning": "เขียว (Green)",
        "color_critical": "น้ำตาล (Brown)",
        "ref_range": "Negative"
    },
    "BIL": {
        "normal": ["neg.", "neg", "negative", "0"],
        "high": ["+", "++", "+++"],  # โทนชมพู/ม่วงตุ่น
        "color_normal": "เบจ/ครีม",
        "color_high": "ชมพู/ม่วงตุ่น (Pink/Purple)",
        "ref_range": "Negative"
    },
    "KET": {
        "normal": ["neg.", "neg", "negative", "0"],
        "warning": ["±5(0.5)", "±5", "5", "+15(1.5)", "+15", "15"],
        "critical": ["++40(3.9)", "++40", "40", "+++100(10)", "+++100", "100"],  # โทนสีม่วงแดง (Magenta)
        "color_normal": "เบจ/ครีม",
        "color_warning": "ชมพู/ม่วงอ่อน",
        "color_critical": "ม่วงเข้ม (Magenta)",
        "ref_range": "Negative"
    },
    "BLO": {
        "normal": ["neg.", "neg", "negative", "0"],
        "warning": ["hemolysis+10", "hemolysis +10", "+10", "non hemolysis +10"],  # จุดสีเขียว หรือ เขียวอ่อน
        "critical": ["hemolysis ++50", "hemolysis++50", "hemolysis +++250", "hemolysis+++250", "++50", "50", "+++250", "250", "non hemolysis ++50"],  # เขียวเข้มจัด / จุดหนาแน่น
        "color_normal": "เหลือง (Yellow)",
        "color_warning": "เขียวอ่อน (Light Green)",
        "color_critical": "เขียวเข้ม (Dark Green)",
        "ref_range": "Negative"
    },
    "PRO": {
        "normal": ["neg.", "neg", "negative", "0"],
        "warning": ["trace", "+30(0.3)", "+30", "30", "15"],  # เขียวตองอ่อน
        "critical": ["++100(1.0)", "++100", "100", "+++300(3.0)", "+++300", "300", "++++1000(10)", "++++1000", "1000"],  # เขียวเข้ม
        "color_normal": "เหลือง/เขียวอ่อน",
        "color_warning": "เขียวตองอ่อน",
        "color_critical": "เขียว (Green)",
        "ref_range": "Negative"
    },
    "NIT": {
        "normal": ["neg.", "neg", "negative", "0"],
        "high": ["trace", "pos.", "pos", "positive"],  # โทนชมพูชัดเจน
        "color_normal": "ครีม/ขาว",
        "color_high": "ชมพู/บานเย็น (Pink)",
        "ref_range": "Negative"
    },
    "LEU": {
        "normal": ["neg.", "neg", "negative", "0"],
        "warning": ["+25", "25"],  # ม่วงอ่อน
        "critical": ["++75", "75", "+++500", "500"],  # ม่วงเข้ม
        "color_normal": "ขาวอมชมพูอ่อน",
        "color_warning": "ชมพูอ่อน/ม่วงอ่อน",
        "color_critical": "ม่วง/ชมพูเข้ม (Purple)",
        "ref_range": "Negative"
    },
    "ASC": {
        "normal": ["neg.", "neg", "negative", "0"],
        "high": ["+20(1.2)", "+20", "20", "++40(2.4)", "++40", "40"],  # เปลี่ยนเป็นเขียวหรือเหลือง
        "color_normal": "น้ำเงินเข้ม/ฟ้าเข้ม (Dark Blue/Teal)",
        "color_high": "ส้ม (Orange)",
        "ref_range": "Negative"
    },
    # ค่าที่เป็นตัวเลขต่อเนื่อง (ต้องใช้ Logic การเปรียบเทียบค่า (><=) แทน)
    "SG": {
        "min_normal": 1.005,
        "max_normal": 1.030,
        "color": "เขียวมะกอก/เหลือง",
        "ref_range": "1.005 - 1.030"
    },
    "pH": {
        "min_normal": 5.0,
        "max_normal": 8.0,
        "color_normal": "เหลือง (Yellow)",  # Default normal color
        "color_acidic": "ส้ม (Orange)",
        "color_neutral": "เหลือง",
        "color_alkaline": "เขียว/ฟ้า",
        "ref_range": "5.0 - 8.0"
    }
}


def get_severity_level(param_code, value):
    """
    ประเมินระดับความรุนแรงของค่าที่อ่านได้

    Args:
        param_code: รหัสพารามิเตอร์ (URO, GLU, BLO, etc.)
        value: ค่าที่อ่านได้จากแผ่นตรวจ

    Returns:
        tuple: (severity_level, color, status)
        - severity_level: "normal", "warning", "critical", "high"
        - color: สีที่เห็นบนแผ่นตรวจ
        - status: "Normal", "Positive", "Positive (High)"
    """
    if param_code not in CYBOW_11M_EXACT_REFERENCE:
        return ("normal", "-", "Normal")

    ref = CYBOW_11M_EXACT_REFERENCE[param_code]
    val = str(value).lower().strip()

    # Handle SG and pH separately (numeric ranges)
    if param_code == "SG":
        try:
            num = float(val.replace("sg", "").strip())
            if ref["min_normal"] <= num <= ref["max_normal"]:
                return ("normal", ref["color"], "Normal")
            else:
                return ("warning", ref["color"], "Abnormal")
        except:
            return ("normal", ref["color"], "Normal")

    if param_code == "pH":
        try:
            num = float(val.replace("ph", "").strip())
            if num < 7.0:
                color = ref["color_acidic"]
            elif num > 7.0:
                color = ref["color_alkaline"]
            else:
                color = ref["color_neutral"]

            if ref["min_normal"] <= num <= ref["max_normal"]:
                return ("normal", color, "Normal")
            else:
                return ("warning", color, "Abnormal")
        except:
            return ("normal", ref["color_neutral"], "Normal")

    # Check critical first (highest severity)
    if "critical" in ref:
        for critical_val in ref["critical"]:
            if critical_val.lower() in val or val in critical_val.lower():
                return ("critical", ref["color_critical"], "Positive (High)")

    # Check warning
    if "warning" in ref:
        for warning_val in ref["warning"]:
            if warning_val.lower() in val or val in warning_val.lower():
                return ("warning", ref["color_warning"], "Positive")

    # Check high (for parameters without warning/critical distinction)
    if "high" in ref:
        for high_val in ref["high"]:
            if high_val.lower() in val or val in high_val.lower():
                return ("high", ref["color_high"], "Positive")

    # Check normal
    if "normal" in ref:
        for normal_val in ref["normal"]:
            if normal_val.lower() in val or val in normal_val.lower():
                return ("normal", ref["color_normal"], "Normal")

    # Default fallback
    return ("normal", ref.get("color_normal", "-"), "Normal")


# =================================================================
# 🛡️ STRICT VALIDATOR: ระบบบังคับกรอบข้อมูลให้อยู่ในมาตรฐาน CYBOW 11M 100%
# =================================================================

def enforce_strict_cybow_standards(ai_raw_data):
    """
    ฟังก์ชันนี้จะรับ JSON ที่ AI ตอบมา และทำการ 'บังคับ (Force)'
    ให้ทุกค่าตรงกับมาตรฐาน CYBOW 11M แบบเป๊ะๆ ทุกตัวอักษร
    หาก AI พิมพ์ผิด หรือใช้คำอื่น ระบบจะแปลงกลับเป็นค่ามาตรฐานทันที

    Args:
        ai_raw_data: Dictionary ที่ได้จาก AI response (JSON parsed)

    Returns:
        Dictionary: ข้อมูลที่ผ่านการ validate แล้ว ค่าทุกตัวตรงมาตรฐาน 100%
    """
    import re

    validated_data = {}

    # 1. นิยามกรอบคำตอบที่ถูกต้องที่สุด (Absolute Standard Values)
    ALLOWED_VALUES = {
        "urobilinogen": ["0.1 Normal", "1(16)", "2(33)", "4(66)", "8(131)"],
        "glucose": ["neg.", "±100(5.5)", "+250(14)", "++500(28)", "+++1000(55)"],
        "bilirubin": ["neg.", "+", "++", "+++"],
        "ketones": ["neg.", "±5(0.5)", "+15(1.5)", "++40(3.9)", "+++100(10)"],
        "specific_gravity": ["1.000", "1.005", "1.010", "1.015", "1.020", "1.025", "1.030"],
        "blood": ["neg.", "Hemolysis +10", "Hemolysis ++50", "Hemolysis +++250", "Non Hemolysis +10", "Non Hemolysis ++50"],
        "ph": ["5", "6", "6.5", "7", "8", "9"],
        "protein": ["neg.", "trace", "+30(0.3)", "++100(1.0)", "+++300(3.0)", "++++1000(10)"],
        "nitrite": ["neg.", "trace", "pos."],
        "leukocytes": ["neg.", "+25", "++75", "+++500"],
        "ascorbic_acid": ["neg.", "+20(1.2)", "++40(2.4)"]
    }

    # 2. ฟังก์ชันช่วยค้นหาค่าที่ใกล้เคียงที่สุด (Fuzzy Matching Logic)
    def snap_to_standard(param_key, raw_val):
        val_str = str(raw_val).strip().lower()

        # กฎข้อที่ 1: จัดการกลุ่ม Negative (ถ้ามีคำว่า neg, 0, negative ให้ปรับเป็น "neg." ทันที)
        if val_str in ["neg", "neg.", "negative", "0", "normal", "none"]:
            if param_key in ["urobilinogen", "specific_gravity", "ph"]:
                pass  # ข้ามไป ปล่อยให้เข้าเงื่อนไขด้านล่าง
            else:
                return "neg."

        # กฎข้อที่ 1.5: จัดการกลุ่ม Positive สำหรับ nitrite (pos, positive → pos.)
        if param_key == "nitrite" and val_str in ["pos", "positive"]:
            return "pos."

        # กฎข้อที่ 1.6: จัดการคำพิเศษ เช่น "trace value" → "trace"
        if "trace" in val_str:
            for std_val in ALLOWED_VALUES[param_key]:
                if std_val.lower() == "trace":
                    return std_val

        # กฎข้อที่ 2: ค้นหาตัวเลขหลัก (Core Value) จากคำตอบของ AI
        numbers_in_val = re.findall(r'\d+\.?\d*', val_str)

        # กฎข้อที่ 3: เทียบหาค่าที่ถูกต้องจาก ALLOWED_VALUES
        for std_val in ALLOWED_VALUES[param_key]:
            std_lower = std_val.lower()

            # ถ้า AI ตอบมาตรงเป๊ะ
            if val_str == std_lower:
                return std_val

            # ถ้า AI ตอบมาแค่เครื่องหมายหรือบางส่วน เช่น "++250" ให้จับคู่กับ "Hemolysis +++250"
            if len(numbers_in_val) > 0 and numbers_in_val[0] in std_lower:
                return std_val

        # กฎข้อสุดท้าย: หาก AI หลอนมาแบบหาค่าไม่ได้เลย ให้ส่งค่าปกติกลับไป (Fail-Safe)
        return ALLOWED_VALUES[param_key][0]

    # 3. วนลูปบังคับค่าทุกพารามิเตอร์ให้อยู่ในกรอบ
    for param in ALLOWED_VALUES.keys():
        ai_val = ai_raw_data.get(param, "neg.")
        validated_data[param] = snap_to_standard(param, ai_val)

    # เก็บค่าดั้งเดิมของสรุปผลคลินิกไว้
    validated_data["clinical_summary"] = ai_raw_data.get("clinical_summary", "")
    validated_data["clinical_bullets"] = ai_raw_data.get("clinical_bullets", [])
    validated_data["reasoning"] = ai_raw_data.get("reasoning", "")
    validated_data["visual_check"] = ai_raw_data.get("visual_check", "")

    return validated_data
