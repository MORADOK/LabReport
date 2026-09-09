"""FastAPI HTML/JSON workflow for staff-entered CYBOW 11M results."""
from __future__ import annotations

import html
from datetime import datetime

from src import db_handler
from src.manual_cases import get_manual_case
from src.manual_summary import summarize_manual_results
from src.standards import CYBOW_11M_STANDARDS, ALLOWED_VALUES, normalize_value

PARAMETERS = [
    ("urobilinogen", "Urobilinogen", "mg/dL (µmol/L)"),
    ("glucose", "Glucose", "mg/dL (mmol/L)"),
    ("bilirubin", "Bilirubin", ""),
    ("ketones", "Ketones", "mg/dL (mmol/L)"),
    ("specific_gravity", "Specific Gravity (S.G.)", ""),
    ("blood", "Blood", "RBC/µL"),
    ("ph", "pH", ""),
    ("protein", "Protein", "mg/dL (g/L)"),
    ("nitrite", "Nitrite", ""),
    ("leukocytes", "Leukocytes", "WBC/µL"),
    ("ascorbic_acid", "Ascorbic acid", "mg/dL (mmol/L)"),
]


def _page(message: str, title: str = "CYBOW 11M") -> str:
    return f"""<!doctype html><html lang='th'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{html.escape(title)}</title><style>
body{{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;background:#f4f7f8;color:#17202a}} .wrap{{max-width:960px;margin:auto;padding:18px}}
.card{{background:white;border:1px solid #dbe5e8;border-radius:16px;padding:18px;box-shadow:0 2px 10px #0000000a}}
</style></head><body><div class='wrap'><div class='card'>{message}</div></div></body></html>"""


def render_manual_form(token: str) -> tuple[int, str]:
    case = get_manual_case(token)
    if not case:
        return 404, _page("<h2>ไม่พบเคส</h2><p>ลิงก์ไม่ถูกต้องหรือเคสถูกลบแล้ว</p>")
    if not case.get("valid"):
        reason = "เคสนี้ถูกบันทึกแล้ว" if case.get("reason") == "case_not_pending" else "ลิงก์นี้หมดอายุแล้ว"
        return 410, _page(f"<h2>ไม่สามารถเปิดฟอร์มได้</h2><p>{reason}</p>")

    blocks = []
    for idx, (param, title, unit) in enumerate(PARAMETERS, 1):
        options = []
        for item in CYBOW_11M_STANDARDS[param]:
            r, g, b = item["rgb"]
            value = html.escape(item["value"], quote=True)
            options.append(
                f"<label class='opt'><input type='radio' name='{param}' value='{value}' required>"
                f"<span class='sw' style='background:rgb({r},{g},{b})'></span><span>{value}</span></label>"
            )
        unit_html = f"<small>{html.escape(unit)}</small>" if unit else ""
        blocks.append(f"<section><h3>{idx}. {html.escape(title)} {unit_html}</h3><div class='opts'>{''.join(options)}</div></section>")

    patient = html.escape(case["patient_name"])
    token_js = html.escape(token, quote=True)
    body = f"""
<h1>🧪 CYBOW 11M — บันทึกผลด้วยตา</h1>
<div class='patient'><b>ผู้ป่วย:</b> {patient}</div>
<div class='note'><b>วิธีใช้:</b> เทียบแถบจริงกับฉลาก CYBOW 11M REF 0974 แล้วเลือกให้ครบ 11 ค่า<br><b>เวลาอ่าน:</b> 60 วินาที; Leukocytes 90–120 วินาที<br><b>AI จะไม่แก้ค่าที่พนักงานเลือก</b> แต่จะสรุปผลหลังยืนยัน</div>
<form id='f'>{''.join(blocks)}
<label class='verify'><input id='verify' type='checkbox' required> ฉันได้เทียบแถบจริงกับตาราง REF 0974 และตรวจครบ 11 ค่าแล้ว</label>
<button id='save' type='submit'>ยืนยันและบันทึกผล</button></form>
<div id='status'></div>
<script>
const form=document.getElementById('f'), btn=document.getElementById('save'), status=document.getElementById('status');
form.addEventListener('submit', async (e)=>{{e.preventDefault(); if(!form.reportValidity()) return; btn.disabled=true; btn.textContent='กำลังให้ AI สรุปและบันทึก...'; status.innerHTML='';
 const fd=new FormData(form), results={{}}; for(const [k,v] of fd.entries()) if(k!=='verify') results[k]=v;
 try{{const res=await fetch('/api/manual-entry',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{case:'{token_js}',results}})}}); const data=await res.json();
 if(!res.ok) throw new Error(data.detail||'บันทึกไม่สำเร็จ');
 form.style.display='none'; status.innerHTML='<div class="ok"><h2>✅ บันทึกสำเร็จ</h2><p>'+escapeHtml(data.summary)+'</p><ul>'+data.bullets.map(x=>'<li>'+escapeHtml(x)+'</li>').join('')+'</ul><p>สามารถปิดหน้านี้ได้</p></div>';
 }}catch(err){{status.innerHTML='<div class="err">❌ '+escapeHtml(err.message)+'</div>';btn.disabled=false;btn.textContent='ยืนยันและบันทึกผล';}} }});
function escapeHtml(s){{return String(s).replace(/[&<>\"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}}[m]));}}
</script>
"""
    css = """<style>
body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;background:#f4f7f8;color:#17202a}.wrap{max-width:980px;margin:auto;padding:14px}.card{background:white;border:1px solid #dce7e9;border-radius:16px;padding:18px}.patient{font-size:1.12rem;padding:12px;background:#e8f7ef;border-radius:10px;margin-bottom:10px}.note{background:#f7fafb;border:1px solid #dae4e8;padding:12px;border-radius:10px;margin-bottom:14px;line-height:1.55}section{border-top:1px solid #e5eaec;padding:12px 0}h3{margin:0 0 9px}.opts{display:flex;flex-wrap:wrap;gap:8px}.opt{display:flex;align-items:center;gap:7px;border:1px solid #cfd9dd;border-radius:10px;padding:7px 10px;cursor:pointer;background:#fff}.opt:has(input:checked){outline:3px solid #2f9e64;background:#effbf4}.sw{width:30px;height:30px;border:1px solid #777;border-radius:6px}.verify{display:block;padding:14px;background:#fff9db;border-radius:10px;margin:14px 0}button{width:100%;padding:14px;border:0;border-radius:11px;background:#16794b;color:white;font-size:1.05rem;font-weight:700}button:disabled{opacity:.6}.ok{background:#ecfdf3;border:1px solid #86d5a8;padding:16px;border-radius:12px}.err{background:#fff1f1;border:1px solid #f2aaaa;padding:12px;border-radius:10px;color:#9b1c1c}small{font-weight:400;color:#64748b}@media(max-width:600px){.opt{width:calc(50% - 26px)}.wrap{padding:8px}.card{padding:12px}}
</style>"""
    return 200, f"<!doctype html><html lang='th'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CYBOW 11M Manual Entry</title>{css}</head><body><div class='wrap'><div class='card'>{body}</div></div></body></html>"


def validate_results(raw_results: dict) -> dict:
    if not isinstance(raw_results, dict):
        raise ValueError("results must be an object")
    normalized = {}
    for param in ALLOWED_VALUES:
        value = normalize_value(param, raw_results.get(param))
        if value is None:
            raise ValueError(f"ค่าของ {param} ไม่ถูกต้องหรือยังไม่ได้เลือก")
        normalized[param] = value
    return normalized


def save_manual_submission(token: str, raw_results: dict) -> dict:
    case = get_manual_case(token)
    if not case or not case.get("valid"):
        raise ValueError("เคสไม่ถูกต้อง หมดอายุ หรือถูกบันทึกไปแล้ว")
    selections = validate_results(raw_results)
    if not db_handler.claim_manual_case(token):
        raise ValueError("เคสนี้กำลังถูกบันทึกหรือถูกบันทึกไปแล้ว")
    try:
        ai_summary = summarize_manual_results(selections)
        diagnostics = {
            "entry_mode": "line_manual_visual_ref_0974_ai_summary",
            "reference": "CYBOW 11M REF 0974",
            "entered_at": datetime.now().isoformat(timespec="seconds"),
            "selected_results": selections,
            "human_verified": True,
            "manual_case_token_tail": token[-6:],
            "line_user_id_present": bool(case.get("line_user_id")),
            "ai_summary_used": ai_summary.get("ai_used", False),
            "ai_summary_model": ai_summary.get("model"),
        }
        if ai_summary.get("error"):
            diagnostics["ai_summary_error"] = ai_summary["error"]
        success = db_handler.insert_record(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            urobilinogen=selections["urobilinogen"], glucose=selections["glucose"],
            bilirubin=selections["bilirubin"], ketones=selections["ketones"],
            specific_gravity=float(selections["specific_gravity"]), blood=selections["blood"],
            ph=float(selections["ph"]), protein=selections["protein"], nitrite=selections["nitrite"],
            leukocytes=selections["leukocytes"], ascorbic_acid=selections["ascorbic_acid"],
            notes=case["patient_name"], clinical_summary=ai_summary["summary"],
            clinical_bullets=ai_summary["bullets"], diagnostics=diagnostics,
        )
        if not success:
            db_handler.reopen_manual_case(token)
            raise RuntimeError("บันทึกฐานข้อมูลไม่สำเร็จ")
        db_handler.complete_manual_case(token)
        return {"summary": ai_summary["summary"], "bullets": ai_summary["bullets"], "ai_used": ai_summary.get("ai_used", False)}
    except Exception:
        db_handler.reopen_manual_case(token)
        raise
