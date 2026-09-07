"""Canonical result labels; RGB references are legacy approximations, not calibrated."""
import math
import re

CYBOW_11M_STANDARDS = {
    "urobilinogen": [
        {"label": "0.1 (Normal)", "rgb": (251, 226, 212), "value": "0.1 Normal"},
        {"label": "1 (16)", "rgb": (250, 187, 186), "value": "1(16)"},
        {"label": "2 (33)", "rgb": (244, 151, 158), "value": "2(33)"},
        {"label": "4 (66)", "rgb": (233, 114, 137), "value": "4(66)"},
        {"label": "8 (131)", "rgb": (222, 77, 115), "value": "8(131)"}
    ],
    "glucose": [
        {"label": "neg", "rgb": (118, 194, 201), "value": "neg."},
        {"label": "± 100", "rgb": (148, 199, 126), "value": "±100(5.5)"},
        {"label": "+ 250", "rgb": (137, 168, 64), "value": "+250(14)"},
        {"label": "++ 500", "rgb": (120, 111, 48), "value": "++500(28)"},
        {"label": "+++ 1000", "rgb": (99, 61, 43), "value": "+++1000(55)"}
    ],
    "bilirubin": [
        {"label": "neg", "rgb": (242, 222, 210), "value": "neg."},
        {"label": "+", "rgb": (233, 190, 197), "value": "+"},
        {"label": "++", "rgb": (214, 145, 172), "value": "++"},
        {"label": "+++", "rgb": (163, 76, 122), "value": "+++"}
    ],
    "ketones": [
        {"label": "neg", "rgb": (242, 222, 210), "value": "neg."},
        {"label": "± 5", "rgb": (233, 190, 197), "value": "±5(0.5)"},
        {"label": "+ 15", "rgb": (214, 145, 172), "value": "+15(1.5)"},
        {"label": "++ 40", "rgb": (163, 76, 122), "value": "++40(3.9)"},
        {"label": "+++ 100", "rgb": (112, 43, 75), "value": "+++100(10)"}
    ],
    "ph": [
        {"label": "5.0", "rgb": (236, 136, 75), "value": "5"},
        {"label": "6.0", "rgb": (238, 179, 74), "value": "6"},
        {"label": "6.5", "rgb": (207, 189, 64), "value": "6.5"},
        {"label": "7.0", "rgb": (153, 173, 56), "value": "7"},
        {"label": "8.0", "rgb": (59, 131, 101), "value": "8"},
        {"label": "9.0", "rgb": (49, 102, 133), "value": "9"}
    ],
    "protein": [
        {"label": "neg", "rgb": (237, 227, 85), "value": "neg."},
        {"label": "trace", "rgb": (204, 216, 92), "value": "trace"},
        {"label": "+ 30", "rgb": (166, 198, 89), "value": "+30(0.3)"},
        {"label": "++ 100", "rgb": (123, 179, 90), "value": "++100(1.0)"},
        {"label": "+++ 300", "rgb": (85, 160, 93), "value": "+++300(3.0)"},
        {"label": "++++ 1000", "rgb": (70, 140, 115), "value": "++++1000(10)"}
    ],
    "blood": [
        {"label": "neg", "rgb": (245, 245, 245), "value": "neg."},
        {"label": "Hemolysis +10 Ery/µL", "rgb": (148, 199, 126), "value": "Hemolysis +10"},
        {"label": "Hemolysis ++50 Ery/µL", "rgb": (120, 111, 48), "value": "Hemolysis ++50"},
        {"label": "Hemolysis +++250 Ery/µL", "rgb": (99, 61, 43), "value": "Hemolysis +++250"},
        {"label": "Non-Hemolysis +10", "rgb": (148, 199, 126), "value": "Non Hemolysis +10"},
        {"label": "Non-Hemolysis ++50", "rgb": (120, 111, 48), "value": "Non Hemolysis ++50"}
    ],
    "nitrite": [
        {"label": "neg", "rgb": (245, 240, 235), "value": "neg."},
        {"label": "trace", "rgb": (234, 210, 215), "value": "trace"},
        {"label": "pos", "rgb": (220, 180, 195), "value": "pos."}
    ],
    "leukocytes": [
        {"label": "neg", "rgb": (240, 230, 235), "value": "neg."},
        {"label": "+25 Leu/µL", "rgb": (225, 205, 220), "value": "+25"},
        {"label": "++75 Leu/µL", "rgb": (200, 170, 200), "value": "++75"},
        {"label": "+++500 Leu/µL", "rgb": (175, 140, 180), "value": "+++500"}
    ],
    "ascorbic_acid": [
        {"label": "neg", "rgb": (230, 235, 210), "value": "neg."},
        {"label": "+20 mg/dL", "rgb": (210, 215, 185), "value": "+20(1.2)"},
        {"label": "++40 mg/dL", "rgb": (190, 195, 160), "value": "++40(2.4)"}
    ],
    "specific_gravity": [
        {"label": "1.000", "rgb": (180, 200, 180), "value": "1.000"},
        {"label": "1.005", "rgb": (175, 195, 175), "value": "1.005"},
        {"label": "1.010", "rgb": (170, 190, 170), "value": "1.010"},
        {"label": "1.015", "rgb": (165, 185, 165), "value": "1.015"},
        {"label": "1.020", "rgb": (160, 180, 160), "value": "1.020"},
        {"label": "1.025", "rgb": (155, 175, 155), "value": "1.025"},
        {"label": "1.030", "rgb": (150, 170, 150), "value": "1.030"}
    ]
}

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
# Conflicting legacy RGB references must not produce similarity scores.
UNVERIFIED_COLOR_PARAMETERS = {"blood", "ascorbic_acid", "specific_gravity"}

def valid_rgb(value):
    return (isinstance(value, (list, tuple)) and len(value) == 3
            and all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 255 for x in value))

def normalize_value(param, value):
    if param not in ALLOWED_VALUES or value is None or isinstance(value, bool):
        return None
    text = str(value).strip().lower()
    compact = re.sub(r"\s+", "", text)
    for standard in ALLOWED_VALUES[param]:
        if compact == re.sub(r"\s+", "", standard.lower()):
            return standard
    if text in ("neg", "negative", "0") and "neg." in ALLOWED_VALUES[param]:
        return "neg."
    if param == "urobilinogen" and text == "normal":
        return "0.1 Normal"
    if param == "nitrite" and text in ("pos", "positive"):
        return "pos."
    if text == "trace value" and "trace" in ALLOWED_VALUES[param]:
        return "trace"
    # Accept only an entire primary numeric value, optionally with its primary unit.
    # Do not interpret secondary SI units, prose or arbitrary substring matches.
    match = re.fullmatch(r"([±+]*)(\d+(?:\.\d+)?)(?:\s*(mg/dl|g/l|ery/µl|leu/µl))?", text)
    if not match:
        return None
    if match[3] and match[3] != {"protein":"mg/dl","glucose":"mg/dl","ketones":"mg/dl",
                               "urobilinogen":"mg/dl","ascorbic_acid":"mg/dl",
                               "blood":"ery/µl","leukocytes":"leu/µl"}.get(param):
        return None
    candidates = []
    for standard in ALLOWED_VALUES[param]:
        number = re.search(r"\d+(?:\.\d+)?", standard)
        if number and float(number[0]) == float(match[2]):
            sign = re.search(r"[±+]+", standard)
            if match[1] and (not sign or sign[0] != match[1]):
                continue
            candidates.append(standard)
    return candidates[0] if len(candidates) == 1 else None
