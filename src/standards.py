"""Canonical CYBOW 11M result labels and shared reference colors.

The RGB values below intentionally use the same approved REF 0974 swatch palette
as the staff manual-entry form. This keeps the AI/image-analysis calibration and
human-facing form on one shared color reference. These are still photo/display
reference colors, not instrument-certified absolute coordinates.
"""
import math
import re

from src.manual_form_colors import MANUAL_FORM_COLORS, MANUAL_FORM_COLOR_SOURCE

_VALUES = {
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
    "ascorbic_acid": ["neg.", "+20(1.2)", "++40(2.4)"],
}

_LABELS = {
    "urobilinogen": ["0.1 (Normal)", "1 (16)", "2 (33)", "4 (66)", "8 (131)"],
    "glucose": ["neg", "± 100", "+ 250", "++ 500", "+++ 1000"],
    "bilirubin": ["neg", "+", "++", "+++"],
    "ketones": ["neg", "± 5", "+ 15", "++ 40", "+++ 100"],
    "specific_gravity": ["1.000", "1.005", "1.010", "1.015", "1.020", "1.025", "1.030"],
    "blood": ["neg", "Hemolysis +10 Ery/µL", "Hemolysis ++50 Ery/µL", "Hemolysis +++250 Ery/µL", "Non-Hemolysis +10", "Non-Hemolysis ++50"],
    "ph": ["5.0", "6.0", "6.5", "7.0", "8.0", "9.0"],
    "protein": ["neg", "trace", "+ 30", "++ 100", "+++ 300", "++++ 1000"],
    "nitrite": ["neg", "trace", "pos"],
    "leukocytes": ["neg", "+25 Leu/µL", "++75 Leu/µL", "+++500 Leu/µL"],
    "ascorbic_acid": ["neg", "+20 mg/dL", "++40 mg/dL"],
}

CYBOW_11M_STANDARDS = {
    param: [
        {
            "label": _LABELS[param][i],
            "rgb": tuple(MANUAL_FORM_COLORS[param][i]),
            "value": _VALUES[param][i],
            **({"pattern": "spots" if i == 4 else "spots_dense"} if param == "blood" and i >= 4 else {}),
        }
        for i in range(len(_VALUES[param]))
    ]
    for param in _VALUES
}

ALLOWED_VALUES = {param: list(values) for param, values in _VALUES.items()}
CALIBRATION_SOURCE = MANUAL_FORM_COLOR_SOURCE + " (shared by manual UI and AI calibration)"
UNVERIFIED_COLOR_PARAMETERS = {"blood"}

def valid_rgb(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 255 for x in value)

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
    match = re.fullmatch(r"([±+]*)(\d+(?:\.\d+)?)(?:\s*(mg/dl|g/l|ery/µl|leu/µl))?", text)
    if not match:
        return None
    if match[3] and match[3] != {"protein":"mg/dl","glucose":"mg/dl","ketones":"mg/dl","urobilinogen":"mg/dl","ascorbic_acid":"mg/dl","blood":"ery/µl","leukocytes":"leu/µl"}.get(param):
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
