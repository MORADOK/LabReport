from datetime import datetime
import html

import streamlit as st

from src import db_handler
from src.access import require_dashboard_login
from src.standards import CYBOW_11M_STANDARDS

st.set_page_config(page_title="CYBOW 11M Manual Entry", page_icon="🧪", layout="wide")
require_dashboard_login()

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

st.markdown("""
<style>
.block-container {max-width: 1200px; padding-top: 1.5rem;}
.ref-note {padding:12px 14px; border-radius:12px; background:#f8fafc; border:1px solid #dbe4ee; margin-bottom:16px;}
.test-card {padding:12px 14px 8px; border:1px solid #e2e8f0; border-radius:14px; background:#fff; margin:7px 0 12px; box-shadow:0 1px 3px rgba(0,0,0,.03);}
.swatch-row {display:flex; flex-wrap:wrap; gap:7px; margin:8px 0 4px;}
.swatch {display:inline-flex; align-items:center; gap:7px; border:1px solid #d1d5db; border-radius:10px; padding:6px 9px; background:#fff; font-size:.83rem;}
.swatch-color {width:30px; height:30px; border-radius:6px; border:1px solid rgba(0,0,0,.25); flex:none;}
.selected-chip {display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border-radius:10px; background:#ecfdf5; border:1px solid #86efac; font-weight:600; margin-top:5px;}
.summary-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:8px; margin:8px 0 16px;}
.summary-item {padding:9px 11px; border:1px solid #e2e8f0; border-radius:10px; background:#f8fafc;}
div[data-testid="stRadio"] > div {gap:.35rem .8rem;}
</style>
""", unsafe_allow_html=True)

st.title("🧪 บันทึกผล CYBOW 11M แบบอ่านด้วยตา")
st.markdown("""<div class='ref-note'><b>ขั้นตอน:</b> อ่านแถบตรวจตามเวลาที่กำหนด → เทียบกับฉลาก CYBOW 11M REF 0974 → เลือกค่าให้ครบ 11 รายการ → ตรวจทาน → ยืนยันบันทึก<br><b>เวลาอ่านตามฉลาก:</b> 60 วินาที และ Leukocytes 90–120 วินาที<br><b>โหมดนี้ไม่ใช้ AI ตัดสินสี</b> ค่าที่บันทึกคือค่าที่พนักงานเลือกเท่านั้น</div>""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    patient_name = st.text_input("ชื่อ-นามสกุลผู้ป่วย *", placeholder="กรอกชื่อผู้ป่วย")
with c2:
    operator_note = st.text_input("ผู้บันทึก / หมายเหตุ", placeholder="เช่น ชื่อพนักงาน หรือเลขตัวอย่าง")

st.subheader("ตารางเลือกสีและผล 11 ค่า")
st.caption("แตะค่าด้านล่างแต่ละรายการให้ตรงกับสีที่พนักงานเห็นบนแถบจริง")

selections = {}
for idx, (param, title, unit) in enumerate(PARAMETERS, 1):
    standards = CYBOW_11M_STANDARDS[param]
    options = [item["value"] for item in standards]
    default_key = f"manual_{param}"
    if default_key not in st.session_state:
        st.session_state[default_key] = None

    st.markdown(f"<div class='test-card'><b>{idx}. {html.escape(title)}</b>{(' · ' + html.escape(unit)) if unit else ''}", unsafe_allow_html=True)
    swatches = []
    for item in standards:
        r, g, b = item["rgb"]
        swatches.append(f"<span class='swatch'><span class='swatch-color' style='background:rgb({r},{g},{b})'></span>{html.escape(item['value'])}</span>")
    st.markdown("<div class='swatch-row'>" + "".join(swatches) + "</div>", unsafe_allow_html=True)
    selections[param] = st.radio(
        f"เลือกค่า {title}", options, index=None, horizontal=True,
        key=default_key, label_visibility="collapsed"
    )
    if selections[param] is not None:
        chosen = next(x for x in standards if x["value"] == selections[param])
        r, g, b = chosen["rgb"]
        st.markdown(f"<span class='selected-chip'><span class='swatch-color' style='width:22px;height:22px;background:rgb({r},{g},{b})'></span>เลือกแล้ว: {html.escape(selections[param])}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

missing = [title for param, title, _ in PARAMETERS if selections[param] is None]
selected_count = 11 - len(missing)
st.progress(selected_count / 11, text=f"เลือกแล้ว {selected_count}/11 ค่า")
st.caption("สีบนหน้าจอเป็นตัวช่วยอ้างอิงจากภาพ REF 0974 เท่านั้น การตัดสินควรเทียบแถบจริงกับฉลากผู้ผลิตภายใต้แสงที่เหมาะสม")

if "manual_review" not in st.session_state:
    st.session_state.manual_review = False

left, right = st.columns(2)
with left:
    if st.button("🔎 ตรวจทานผล 11 ค่า", type="primary", use_container_width=True):
        if not patient_name.strip():
            st.error("กรุณากรอกชื่อ-นามสกุลผู้ป่วย")
            st.session_state.manual_review = False
        elif missing:
            st.error("กรุณาเลือกให้ครบ 11 ค่า ยังขาด: " + ", ".join(missing))
            st.session_state.manual_review = False
        else:
            st.session_state.manual_review = True
with right:
    if st.button("↩️ กลับไปแก้ไข", use_container_width=True):
        st.session_state.manual_review = False

if st.session_state.manual_review and not missing and patient_name.strip():
    st.divider()
    st.subheader("ตรวจสอบก่อนบันทึก")
    items = []
    for param, title, _ in PARAMETERS:
        items.append(f"<div class='summary-item'><b>{html.escape(title)}</b><br>{html.escape(selections[param])}</div>")
    st.markdown("<div class='summary-grid'>" + "".join(items) + "</div>", unsafe_allow_html=True)
    confirm = st.checkbox("ฉันได้เทียบแถบจริงกับตาราง CYBOW 11M REF 0974 และตรวจทานครบทั้ง 11 ค่าแล้ว")

    if st.button("💾 ยืนยันและบันทึกผล", type="primary", use_container_width=True, disabled=not confirm):
        diagnostics = {
            "entry_mode": "manual_visual_ref_0974",
            "reference": "CYBOW 11M REF 0974",
            "entered_at": datetime.now().isoformat(timespec="seconds"),
            "operator_note": operator_note.strip(),
            "selected_results": dict(selections),
            "human_verified": True,
        }
        success = db_handler.insert_record(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            urobilinogen=selections["urobilinogen"], glucose=selections["glucose"],
            bilirubin=selections["bilirubin"], ketones=selections["ketones"],
            specific_gravity=float(selections["specific_gravity"]), blood=selections["blood"],
            ph=float(selections["ph"]), protein=selections["protein"], nitrite=selections["nitrite"],
            leukocytes=selections["leukocytes"], ascorbic_acid=selections["ascorbic_acid"],
            notes=patient_name.strip() + ((" | " + operator_note.strip()) if operator_note.strip() else ""),
            clinical_summary="; ".join(f"{p}: {selections[p]}" for p, _, _ in PARAMETERS),
            clinical_bullets=["ผลบันทึกด้วยตาโดยพนักงานเทียบกับ CYBOW 11M REF 0974"],
            diagnostics=diagnostics,
        )
        if success:
            st.success("✅ บันทึกผลตรวจครบ 11 ค่าเรียบร้อยแล้ว")
            st.session_state.manual_review = False
        else:
            st.error("บันทึกฐานข้อมูลไม่สำเร็จ กรุณาตรวจสอบการเชื่อมต่อฐานข้อมูล")
