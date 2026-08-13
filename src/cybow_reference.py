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
        "critical": ["++50", "50", "+++250", "250", "non hemolysis ++50", "hemolysis"],  # เขียวเข้มจัด / จุดหนาแน่น
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
