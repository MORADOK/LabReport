"""Printable HTML preview for CYBOW 11M lab reports shown inside Streamlit."""
from __future__ import annotations
import html

def _esc(value):
    return html.escape(str(value if value is not None else ""))

def _status_class(status):
    text = str(status or "")
    if "Normal" in text: return "normal"
    if text == "N/A": return "na"
    if text in ("Positive", "Abnormal") or any(x in text for x in ("Trace","Small","Mod")): return "positive"
    return "high"

def build_report_preview_html(patient_name, case_id, date_str, table_data, summary_text, bullet_points):
    rows = []
    for row in table_data:
        values = list(row) + [""] * (5-len(row))
        rows.append(
            "<tr>"
            f"<td class='param'>{_esc(values[0])}</td>"
            f"<td>{_esc(values[1])}</td>"
            f"<td class='muted'>{_esc(values[2])}</td>"
            f"<td>{_esc(values[3])}</td>"
            f"<td><span class='badge {_status_class(values[4])}'>{_esc(values[4])}</span></td>"
            "</tr>"
        )
    bullets = [str(x).strip() for x in (bullet_points or []) if str(x).strip()]
    bullet_html = "".join(f"<li>{_esc(x)}</li>" for x in bullets[:4])
    if len(bullets) > 4:
        bullet_html += "<li>มีคำแนะนำเพิ่มเติมในข้อมูลที่บันทึกในระบบ</li>"
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#eef2f7;color:#172033;font-family:Arial,'Noto Sans Thai',sans-serif}}
.toolbar{{display:flex;justify-content:flex-end;margin:0 auto 8px;max-width:900px}}
.print-btn{{border:0;border-radius:8px;padding:8px 16px;background:#16794b;color:white;font-weight:700;cursor:pointer}}
.sheet{{max-width:900px;margin:auto;background:white;padding:16px 20px;border:1px solid #d9e2ec;border-radius:10px;box-shadow:0 4px 18px #0f172a12}}
.header{{text-align:center;border-bottom:2px solid #1e3a8a;padding-bottom:6px;margin-bottom:8px}}
.header h1{{font-size:19px;color:#1e3a8a;margin:0 0 2px}}.header p{{font-size:10px;color:#64748b;margin:0}}
.info{{display:grid;grid-template-columns:1fr 1fr;gap:3px 18px;background:#f8fafc;border:1px solid #dbe4ee;border-radius:8px;padding:7px 9px;font-size:10px;margin-bottom:8px}}
.summary{{border:1px solid #fecaca;background:#fff7f7;border-radius:8px;padding:6px 9px;margin-bottom:8px;font-size:10px;line-height:1.35}}.summary b{{color:#b91c1c}}
table{{width:100%;border-collapse:collapse;font-size:9.5px}}thead th{{background:#1e3a8a;color:white;padding:5px 4px;text-align:center}}
tbody td{{padding:4.5px 4px;border-bottom:1px solid #e2e8f0;vertical-align:middle}}tbody tr:nth-child(odd){{background:#f8fafc}}
.param{{font-weight:700}}.muted{{color:#64748b}}.badge{{display:inline-block;border-radius:999px;padding:2px 6px;font-weight:700;font-size:8.5px;white-space:nowrap}}
.normal{{background:#dcfce7;color:#166534}}.positive{{background:#ffedd5;color:#9a3412}}.high{{background:#fee2e2;color:#991b1b}}.na{{background:#e2e8f0;color:#475569}}
.notes{{margin-top:8px;border:1px solid #bfdbfe;background:#eff6ff;border-radius:8px;padding:6px 9px;font-size:9.5px}}.notes b{{color:#1d4ed8}}.notes ul{{margin:3px 0 0 16px;padding:0}}.notes li{{margin:1px 0}}
.footer{{text-align:center;color:#64748b;font-size:8px;margin-top:7px;padding-top:4px;border-top:1px solid #e2e8f0}}
@media(max-width:650px){{.sheet{{padding:10px 8px}}.info{{grid-template-columns:1fr}}table{{font-size:8px}}thead th,tbody td{{padding:3px 2px}}}}
@media print{{@page{{size:A4 portrait;margin:8mm}}body{{background:white}}.toolbar{{display:none!important}}.sheet{{max-width:none;border:0;border-radius:0;box-shadow:none;padding:0;margin:0}}}}
</style></head><body>
<div class='toolbar'><button class='print-btn' onclick='window.print()'>🖨️ พิมพ์รายงาน</button></div>
<main class='sheet'><div class='header'><h1>รายงานผลวิเคราะห์แถบสีปัสสาวะ (CYBOW 11M)</h1><p>Urine Analysis Report • REF 0974</p></div>
<div class='info'><div><b>ชื่อผู้ป่วย:</b> {_esc(patient_name)}</div><div><b>วันที่ตรวจ:</b> {_esc(date_str)}</div><div><b>รหัสเคส:</b> {_esc(case_id)}</div><div><b>ชุดตรวจ:</b> CYBOW 11M (REF 0974)</div></div>
<div class='summary'><b>สรุปผล:</b> {_esc(summary_text)}</div>
<table><thead><tr><th>พารามิเตอร์</th><th>ค่าที่อ่านได้</th><th>ค่ามาตรฐาน</th><th>แถบสี</th><th>สถานะ</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<div class='notes'><b>ข้อบ่งชี้ทางคลินิกและคำแนะนำ</b><ul>{bullet_html or '<li>-</li>'}</ul></div>
<div class='footer'>เอกสารนี้ใช้สำหรับการประเมินคัดกรองเบื้องต้น ควรแปลผลร่วมกับข้อมูลทางคลินิก • LHome Facility</div></main></body></html>"""
