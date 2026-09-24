"""Single source of truth for CYBOW 11M report display.

Recorded strip values are authoritative. This module preserves those values and
uses neutral observation labels; it does not diagnose or turn strip levels into
clinical Normal/Abnormal conclusions.
"""
from __future__ import annotations

from src.standards import ALLOWED_VALUES, normalize_value

PARAM_CODE_TO_FIELD = {
    "URO": "urobilinogen", "GLU": "glucose", "BIL": "bilirubin",
    "KET": "ketones", "SG": "specific_gravity", "BLO": "blood",
    "pH": "ph", "PRO": "protein", "NIT": "nitrite",
    "LEU": "leukocytes", "ASC": "ascorbic_acid",
}
REFERENCE_TEXT = {
    "URO": "CYBOW 11M scale", "GLU": "Negative", "BIL": "Negative",
    "KET": "Negative", "SG": "CYBOW 11M scale", "BLO": "Negative",
    "pH": "CYBOW 11M scale", "PRO": "Negative", "NIT": "Negative",
    "LEU": "Negative", "ASC": "Negative",
}
COLOR_TEXT = {code: "เทียบแถบ CYBOW 11M" for code in PARAM_CODE_TO_FIELD}
_NEGATIVE = {"neg.", "neg", "negative", "0"}


def _observation(param_code: str, value: str) -> str:
    """Neutral strip observation; never a clinical Normal/Abnormal judgment."""
    text = str(value).strip().lower()
    if param_code in {"SG", "pH", "URO"}:
        return "Recorded"
    return "Not detected" if text in _NEGATIVE else "Detected"


def _display_result(field: str, raw_value, normalized: str | None) -> str:
    if normalized is None:
        return str(raw_value).strip()
    # DB numeric columns may return 1.0 even when the CYBOW level is 1.000.
    if field == "specific_gravity":
        return f"{float(raw_value):.3f}"
    if field == "ph":
        return f"{float(raw_value):.1f}"
    return normalized


def get_report_mapping(param_code, raw_value):
    field = PARAM_CODE_TO_FIELD.get(param_code)
    if not field or raw_value is None or str(raw_value).strip().lower() in {"", "none", "n/a", "-"}:
        return {"result": "N/A", "ref": "-", "color": "-", "status": "N/A"}
    normalized = normalize_value(field, raw_value)
    result = _display_result(field, raw_value, normalized)
    status = _observation(param_code, result) if normalized is not None else "Unverified"
    return {"result": result, "ref": REFERENCE_TEXT[param_code], "color": COLOR_TEXT[param_code], "status": status}


def validate_all_allowed_values():
    errors = []
    for code, field in PARAM_CODE_TO_FIELD.items():
        for value in ALLOWED_VALUES[field]:
            mapped = get_report_mapping(code, value)
            if field == "ph": expected = f"{float(value):.1f}"
            elif field == "specific_gravity": expected = f"{float(value):.3f}"
            else: expected = value
            if mapped["result"] != expected:
                errors.append((field, value, mapped["result"]))
    return errors
