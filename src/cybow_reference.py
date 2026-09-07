# -*- coding: utf-8 -*-
"""
CYBOW 11M result classification
Legacy labels; color descriptions are not instrument calibration data.
แบ่งระดับความรุนแรงเพื่อให้ AI และ Dashboard ประเมินสถานะได้แม่นยำที่สุด
"""

# ---------------------------------------------------------
# CYBOW 11M legacy reference labels
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


from src.standards import ALLOWED_VALUES, CYBOW_11M_STANDARDS, UNVERIFIED_COLOR_PARAMETERS, normalize_value, valid_rgb
import math
import re

def get_severity_level(param_code, value):
    unknown = ("unknown", "-", "N/A")
    ref = CYBOW_11M_EXACT_REFERENCE.get(param_code)
    if not ref or value is None:
        return unknown
    val = re.sub(r"\s+", "", str(value).lower())
    if param_code in ("SG", "pH"):
        try:
            num = float(val)
            if not math.isfinite(num):
                return unknown
        except (TypeError, ValueError):
            return unknown
        color = ref["color"] if param_code == "SG" else ref[
            "color_acidic" if num < 7 else "color_alkaline" if num > 7 else "color_neutral"]
        normal = ref["min_normal"] <= num <= ref["max_normal"]
        return ("normal" if normal else "warning", color, "Normal" if normal else "Abnormal")
    for severity in ("normal", "critical", "warning", "high"):
        if any(val == re.sub(r"\s+", "", x.lower()) for x in ref.get(severity, [])):
            return (severity, ref.get("color_" + severity, "-"),
                    "Normal" if severity == "normal" else "Positive (High)" if severity == "critical" else "Positive")
    return unknown

def calculate_confidence_from_rgb(detected_rgb, param_code, selected_value):
    """Legacy API: uncalibrated color similarity, not probability of correctness."""
    if not valid_rgb(detected_rgb) or param_code in UNVERIFIED_COLOR_PARAMETERS:
        return None
    target = next((x["rgb"] for x in CYBOW_11M_STANDARDS.get(param_code, [])
                   if x["value"] == selected_value), None)
    if target is None:
        return None
    return round(max(0, min(100, 100 - math.dist(detected_rgb, target))), 1)

def enforce_strict_cybow_standards(ai_raw_data):
    if not isinstance(ai_raw_data, dict):
        raise ValueError("Analysis response must be a JSON object")
    data = {p: normalize_value(p, ai_raw_data.get(p)) for p in ALLOWED_VALUES}
    errors = [p for p, v in data.items() if v is None]
    data["validation_errors"] = errors
    data["is_valid"] = not errors
    data["clinical_summary"] = ai_raw_data.get("clinical_summary") if isinstance(ai_raw_data.get("clinical_summary"), str) else ""
    bullets = ai_raw_data.get("clinical_bullets")
    data["clinical_bullets"] = [x for x in bullets if isinstance(x, str)] if isinstance(bullets, list) else []
    rgb = ai_raw_data.get("detected_rgb")
    rgb = rgb if isinstance(rgb, dict) else {}
    data["detected_rgb"] = {p: list(v) for p, v in rgb.items() if p in ALLOWED_VALUES and valid_rgb(v)}
    data["rgb_source"] = "ai_estimate"
    data["confidence_scores"] = {p: None for p in ALLOWED_VALUES}
    data["overall_confidence"] = None
    return data
