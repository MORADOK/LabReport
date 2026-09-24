"""Build report narrative only from the values displayed in the current report.

This intentionally avoids reusing historical AI clinical_summary text, because
older summaries may contain interpretation rules that no longer match the report.
"""
from __future__ import annotations


def build_neutral_narrative(table_data):
    detected = []
    recorded = []
    for row in table_data or []:
        if len(row) < 5:
            continue
        name, result, _ref, _color, status = row[:5]
        if status == "Detected":
            detected.append(f"{name}: {result}")
        elif status == "Recorded":
            recorded.append(f"{name}: {result}")
    if detected:
        summary = "ผลจากแถบตรวจที่ตรวจพบ: " + ", ".join(detected) + "."
    else:
        summary = "ไม่พบผลบวกในพารามิเตอร์ที่รายงานแบบ Negative/Detected จากแถบตรวจนี้."
    if recorded:
        summary += " ค่าที่บันทึก: " + ", ".join(recorded) + "."
    bullets = [
        "ผลในตารางเป็นค่าที่บันทึกจากแถบ CYBOW 11M และไม่ถูกเปลี่ยนเป็นคำวินิจฉัยโดยระบบ",
        "คำว่า Detected หมายถึงตรวจพบตามระดับบนแถบ ไม่ได้หมายถึงการวินิจฉัยโรค",
        "ควรพิจารณาผลร่วมกับอาการ ประวัติ และการตรวจยืนยันตามดุลยพินิจของบุคลากรทางการแพทย์",
    ]
    return summary, bullets
