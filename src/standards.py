"""Canonical result labels; RGB references are legacy approximations, not calibrated."""
import math
import re

CYBOW_11M_STANDARDS = {
    "urobilinogen": [
        {"label": "0.1 (Normal)", "rgb": (195, 185, 158), "value": "0.1 Normal"},
        {"label": "1 (16)", "rgb": (187, 172, 167), "value": "1(16)"},
        {"label": "2 (33)", "rgb": (191, 161, 153), "value": "2(33)"},
        {"label": "4 (66)", "rgb": (194, 138, 139), "value": "4(66)"},
        {"label": "8 (131)", "rgb": (188, 105, 120), "value": "8(131)"}
    ],
    "glucose": [
        {"label": "neg", "rgb": (92, 151, 185), "value": "neg."},
        {"label": "± 100", "rgb": (119, 163, 112), "value": "±100(5.5)"},
        {"label": "+ 250", "rgb": (127, 124, 57), "value": "+250(14)"},
        {"label": "++ 500", "rgb": (121, 94, 65), "value": "++500(28)"},
        {"label": "+++ 1000", "rgb": (95, 55, 47), "value": "+++1000(55)"}
    ],
    "bilirubin": [
        {"label": "neg", "rgb": (193, 177, 151), "value": "neg."},
        {"label": "+", "rgb": (188, 161, 141), "value": "+"},
        {"label": "++", "rgb": (177, 156, 140), "value": "++"},
        {"label": "+++", "rgb": (171, 137, 136), "value": "+++"}
    ],
    "ketones": [
        {"label": "neg", "rgb": (185, 168, 156), "value": "neg."},
        {"label": "± 5", "rgb": (177, 155, 152), "value": "±5(0.5)"},
        {"label": "+ 15", "rgb": (177, 144, 151), "value": "+15(1.5)"},
        {"label": "++ 40", "rgb": (147, 90, 122), "value": "++40(3.9)"},
        {"label": "+++ 100", "rgb": (103, 54, 73), "value": "+++100(10)"}
    ],
    "ph": [
        {"label": "5.0", "rgb": (183, 122, 77), "value": "5"},
        {"label": "6.0", "rgb": (188, 146, 65), "value": "6"},
        {"label": "6.5", "rgb": (168, 144, 75), "value": "6.5"},
        {"label": "7.0", "rgb": (141, 149, 63), "value": "7"},
        {"label": "8.0", "rgb": (52, 102, 65), "value": "8"},
        {"label": "9.0", "rgb": (50, 90, 115), "value": "9"}
    ],
    "protein": [
        {"label": "neg", "rgb": (179, 172, 81), "value": "neg."},
        {"label": "trace", "rgb": (166, 167, 108), "value": "trace"},
        {"label": "+ 30", "rgb": (161, 168, 88), "value": "+30(0.3)"},
        {"label": "++ 100", "rgb": (138, 160, 81), "value": "++100(1.0)"},
        {"label": "+++ 300", "rgb": (120, 148, 97), "value": "+++300(3.0)"},
        {"label": "++++ 1000", "rgb": (103, 139, 111), "value": "++++1000(10)"}
    ],
    "blood": [
        {"label": "neg", "rgb": (190, 179, 38), "value": "neg."},
        {"label": "Hemolysis +10 Ery/µL", "rgb": (141, 166, 74), "value": "Hemolysis +10"},
        {"label": "Hemolysis ++50 Ery/µL", "rgb": (80, 133, 74), "value": "Hemolysis ++50"},
        {"label": "Hemolysis +++250 Ery/µL", "rgb": (34, 74, 100), "value": "Hemolysis +++250"},
        {"label": "Non-Hemolysis +10", "rgb": (191, 177, 123), "value": "Non Hemolysis +10"},
        {"label": "Non-Hemolysis ++50", "rgb": (171, 169, 113), "value": "Non Hemolysis ++50"}
    ],
    "nitrite": [
        {"label": "neg", "rgb": (190, 182, 159), "value": "neg."},
        {"label": "trace", "rgb": (180, 156, 170), "value": "trace"},
        {"label": "pos", "rgb": (155, 59, 113), "value": "pos."}
    ],
    "leukocytes": [
        {"label": "neg", "rgb": (185, 169, 155), "value": "neg."},
        {"label": "+25 Leu/µL", "rgb": (184, 158, 143), "value": "+25"},
        {"label": "++75 Leu/µL", "rgb": (180, 154, 165), "value": "++75"},
        {"label": "+++500 Leu/µL", "rgb": (142, 103, 140), "value": "+++500"}
    ],
    "ascorbic_acid": [
        {"label": "neg", "rgb": (29, 97, 102), "value": "neg."},
        {"label": "+20 mg/dL", "rgb": (90, 142, 62), "value": "+20(1.2)"},
        {"label": "++40 mg/dL", "rgb": (173, 167, 30), "value": "++40(2.4)"}
    ],
    "specific_gravity": [
        {"label": "1.000", "rgb": (16, 53, 79), "value": "1.000"},
        {"label": "1.005", "rgb": (40, 66, 67), "value": "1.005"},
        {"label": "1.010", "rgb": (75, 88, 68), "value": "1.010"},
        {"label": "1.015", "rgb": (93, 102, 57), "value": "1.015"},
        {"label": "1.020", "rgb": (120, 116, 52), "value": "1.020"},
        {"label": "1.025", "rgb": (144, 123, 56), "value": "1.025"},
        {"label": "1.030", "rgb": (169, 130, 52), "value": "1.030"}
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
# Reference colors measured from the user-supplied CYBOW 11M REF 0974 chart photo (2026-09-08).
# These are photo-specific RGB values, not instrument-certified absolute color coordinates.
CALIBRATION_SOURCE = "CYBOW 11M REF 0974 reference-chart photo, measured center patches"
UNVERIFIED_COLOR_PARAMETERS = {"blood"}  # Non-hemolysis blood uses a spotted pattern, not a single flat color.

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
