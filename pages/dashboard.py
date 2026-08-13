import streamlit as st
import sys
import os
import pandas as pd
import re
from datetime import datetime
from src.pdf_generator import create_pdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.analysis import load_data, create_trend_chart, parse_clinical_bullets, sanitize_thai_text

# ========================================
# 🎨 Page Configuration
# ========================================
st.set_page_config(
    page_title="LHome Medical Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# 🎯 Custom CSS for Modern UI
# ========================================
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1e3a8a; margin-bottom: 0.5rem; text-align: center; }
    .sub-header { font-size: 1.1rem; color: #64748b; text-align: center; margin-bottom: 2rem; }
    div[data-testid="metric-container"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    div[data-testid="metric-container"] > label { color: white !important; font-weight: 600; }
    div[data-testid="metric-container"] > div { color: white !important; font-size: 2rem !important; font-weight: 700 !important; }
    .dataframe { border-radius: 8px; overflow: hidden; }
    .stDownloadButton button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    .stDownloadButton button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%); }
    div[data-testid="stVerticalBlock"] > div:has(> div.element-container) { background-color: white; border-radius: 12px; padding: 1rem; }
</style>
""", unsafe_allow_html=True)

# ========================================
# 🌟 Data Mapping (แปลงค่าดิบเป็น 4 คอลัมน์)
# ========================================
def get_cybow_mapping(param_code, raw_val):
    val = str(raw_val).lower().strip()
    res = {"result": str(raw_val), "ref": "Negative", "color": "-", "status": "Normal"}
    
    if val in ["n/a", "-", "", "none"]:
        return {"result": "N/A", "ref": "-", "color": "-", "status": "N/A"}

    if param_code == "URO":
        res["ref"] = "0.1 - 1.0"  # ✅ Fixed spacing
        if "0.1" in val or "normal" in val:
            res.update({"result": "0.1 - 1.0", "color": "ครีม/พีชอ่อน", "status": "Normal"})
        elif "1(16)" in val:
            res.update({"result": "1.0 (16 µmol/L)", "color": "พีช", "status": "Normal"})
        else:
            res.update({"result": "> 2.0 (High)", "color": "ชมพู/แดง", "status": "Positive (High)"})
            
    elif param_code == "GLU":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "ฟ้า (Teal)", "status": "Normal"})
        else:
            res.update({"result": val.replace("±", "+-").upper(), "color": "เขียว/น้ำตาล", "status": "Positive"})
            
    elif param_code == "BIL":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "เบจ/ครีม", "status": "Normal"})
        else:
            res.update({"result": val.upper(), "color": "ชมพู/แดง", "status": "Positive"})
            
    elif param_code == "KET":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "เบจ/ครีม", "status": "Normal"})
        elif "±" in val or "15" in val:
            res.update({"result": "15 - 40 mg/dL", "color": "ชมพู/ม่วงอ่อน", "status": "Positive"})
        else:
            res.update({"result": "> 40 mg/dL", "color": "ม่วงเข้ม", "status": "Positive (High)"})
            
    elif param_code == "SG":
        res["ref"] = "1.005 - 1.030"  # ✅ Fixed spacing
        res["color"] = "เขียวมะกอก/เหลือง"
        try:
            num = float(re.findall(r'\d+\.?\d*', val)[0])
            res["result"] = f"{num:.3f}"
            res["status"] = "Normal" if 1.005 <= num <= 1.030 else "Abnormal"
        except:
            pass
            
    elif param_code == "BLO":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "เหลือง (Yellow)", "status": "Normal"})
        elif "10" in val:
            res.update({"result": "+ 10 Ery/µL", "color": "เขียวอ่อน (Light Green)", "status": "Positive"})
        else:
            res.update({"result": "++ 50 ถึง +++ 250", "color": "เขียวเข้ม (Dark Green)", "status": "Positive (High)"})
            
    elif param_code == "pH":
        res["ref"] = "5.0 - 8.0"
        try:
            num = float(re.findall(r'\d+\.?\d*', val)[0])
            nature = "(Acidic)" if num < 7.0 else "(Alkaline)" if num > 7.0 else "(Neutral)"
            res["result"] = f"{num:.1f} {nature}"
            res["color"] = "ส้ม (Orange)" if num < 7.0 else "เขียว/ฟ้า"
            res["status"] = "Normal" if 5.0 <= num <= 8.0 else "Abnormal"
        except:
            pass
            
    elif param_code == "PRO":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "เหลือง/เขียวอ่อน", "status": "Normal"})
        elif "trace" in val or "30" in val:
            res.update({"result": "15 - 30 mg/dL (Trace)", "color": "เขียวตองอ่อน", "status": "Positive"})
        else:
            res.update({"result": "> 100 mg/dL", "color": "เขียว (Green)", "status": "Positive (High)"})
            
    elif param_code == "NIT":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "ครีม/ขาว", "status": "Normal"})
        else:
            res.update({"result": "Positive", "color": "ชมพู/บานเย็น (Pink)", "status": "Positive"})
            
    elif param_code == "LEU":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "ขาวอมชมพูอ่อน", "status": "Normal"})
        elif "25" in val:
            res.update({"result": "+ 25 Leu/µL", "color": "ชมพูอ่อน", "status": "Positive"})
        else:
            res.update({"result": "++ 75 ถึง +++ 500", "color": "ม่วง/ชมพู (Purple)", "status": "Positive (High)"})
            
    elif param_code == "ASC":
        res["ref"] = "Negative"
        if val in ["neg.", "negative", "0", "neg"]:
            res.update({"result": "Negative", "color": "เขียวอ่อน/เหลือง", "status": "Normal"})
        else:
            res.update({"result": val.upper(), "color": "ส้ม", "status": "Positive"})

    return res

# Helper Function สำหรับเตรียมข้อมูล 5 คอลัมน์
def prepare_table_data(data):
    uro = get_cybow_mapping("URO", data.get('urobilinogen', 'N/A'))
    glu = get_cybow_mapping("GLU", data.get('glucose', 'N/A'))
    bil = get_cybow_mapping("BIL", data.get('bilirubin', 'N/A'))
    ket = get_cybow_mapping("KET", data.get('ketones', 'N/A'))
    sg  = get_cybow_mapping("SG", data.get('specific_gravity', 'N/A'))
    blo = get_cybow_mapping("BLO", data.get('blood', 'N/A'))
    ph  = get_cybow_mapping("pH", data.get('ph', 'N/A'))
    pro = get_cybow_mapping("PRO", data.get('protein', 'N/A'))
    nit = get_cybow_mapping("NIT", data.get('nitrite', 'N/A'))
    leu = get_cybow_mapping("LEU", data.get('leukocytes', 'N/A'))
    asc = get_cybow_mapping("ASC", data.get('ascorbic_acid', 'N/A'))

    return [
        ["URO (ยูโรบิลิโนเจน)", uro['result'], uro['ref'], uro['color'], uro['status']],
        ["GLU (กลูโคส)", glu['result'], glu['ref'], glu['color'], glu['status']],
        ["BIL (บิลิรูบิน)", bil['result'], bil['ref'], bil['color'], bil['status']],
        ["KET (คีโตน)", ket['result'], ket['ref'], ket['color'], ket['status']],
        ["SG (ความถ่วงจำเพาะ)", sg['result'], sg['ref'], sg['color'], sg['status']],
        ["BLO (เลือด)", blo['result'], blo['ref'], blo['color'], blo['status']],
        ["pH (ความเป็นกรด-ด่าง)", ph['result'], ph['ref'], ph['color'], ph['status']],
        ["PRO (โปรตีน)", pro['result'], pro['ref'], pro['color'], pro['status']],
        ["NIT (ไนไตรต์)", nit['result'], nit['ref'], nit['color'], nit['status']],
        ["LEU (เม็ดเลือดขาว)", leu['result'], leu['ref'], leu['color'], leu['status']],
        ["ASC (วิตามินซี)", asc['result'], asc['ref'], asc['color'], asc['status']]
    ]

# ========================================
# 📊 Load Data
# ========================================
@st.cache_data(ttl=60)
def get_data():
    return load_data()

with st.spinner("🔄 กำลังโหลดข้อมูล..."):
    df = get_data()

if df.empty:
    st.sidebar.warning("⚠️ Database Connection")
else:
    st.sidebar.success(f"✅ Connected: {len(df)} records")

# ========================================
# 🎨 Header Section
# ========================================
st.markdown('<h1 class="main-header">🏥 LHome Medical Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">ระบบวิเคราะห์ผลตรวจปัสสาวะด้วย AI | Urine Analysis System</p>', unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ ไม่สามารถโหลดข้อมูลจาก Database")
else:
    # ========================================
    # 🎯 KPI Metrics Section
    # ========================================
    valid_patients = df[df['notes'].notna() & (df['notes'] != '')]['notes'].unique().tolist()
    total_records = len(df)
    abnormal_blood = len(df[df['blood'].astype(str).str.contains(r'\+|pos|Hemolysis', case=False, na=False)])
    abnormal_protein = len(df[df['protein'].astype(str).str.contains(r'\+', case=False, na=False)])

    st.markdown("### 📊 สถิติภาพรวม")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("👥 ผู้ป่วยทั้งหมด", f"{len(valid_patients)}", "คน")
    with col2: st.metric("📋 จำนวนการตรวจ", f"{total_records}", "เคส")
    with col3: st.metric("🩸 พบเลือด", f"{abnormal_blood}", "เคส" if abnormal_blood > 0 else "ปกติ", delta_color="inverse")
    with col4: st.metric("🧪 พบโปรตีน", f"{abnormal_protein}", "เคส" if abnormal_protein > 0 else "ปกติ", delta_color="inverse")
    st.markdown("---")

    # ========================================
    # 🔍 Sidebar Filter
    # ========================================
    st.sidebar.markdown("## 🔍 เลือกข้อมูล")
    selected_patient = st.sidebar.selectbox("👤 เลือกผู้ป่วย:", ["📊 แสดงทั้งหมด"] + sorted(valid_patients))

    # ========================================
    # 📋 Data Display Section
    # ========================================
    if selected_patient == "📊 แสดงทั้งหมด":
        st.markdown("### 📋 รายการตรวจทั้งหมด")
        
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1: date_filter = st.date_input("📅 กรองตามวันที่:", value=None)
        with col_f2: search_term = st.text_input("🔎 ค้นหาชื่อ:", placeholder="พิมพ์ชื่อผู้ป่วย...")

        filtered_df = df.copy()
        if date_filter:
            filtered_df['date_only'] = pd.to_datetime(filtered_df['date']).dt.date
            filtered_df = filtered_df[filtered_df['date_only'] == date_filter]
        if search_term:
            filtered_df = filtered_df[filtered_df['notes'].str.contains(search_term, case=False, na=False)]

        display_cols = ['date', 'notes', 'glucose', 'protein', 'blood', 'ph', 'specific_gravity', 'ketones', 'leukocytes']

        st.info("💡 **Tip (Quick Download):** คลิกที่กล่องสี่เหลี่ยมด้านหน้าแถวของคนไข้ เพื่อสร้างและดาวน์โหลดรายงาน PDF ทันที")

        with st.container():
            event = st.dataframe(
                filtered_df[display_cols],
                use_container_width=True,
                height=400,
                hide_index=True,
                on_select="rerun", 
                selection_mode="single-row",
                column_config={
                    "date": st.column_config.DatetimeColumn("📅 วันที่", format="DD/MM/YYYY HH:mm"),
                    "notes": st.column_config.TextColumn("👤 ชื่อผู้ป่วย"),
                    "glucose": st.column_config.TextColumn("🍬 Glucose"),
                    "protein": st.column_config.TextColumn("🧪 Protein"),
                    "blood": st.column_config.TextColumn("🩸 Blood"),
                    "ph": st.column_config.NumberColumn("⚗️ pH", format="%.1f"),
                    "specific_gravity": st.column_config.NumberColumn("💧 S.G.", format="%.3f")
                }
            )

        # 🌟 Quick Download Logic
        selected_rows = event.selection.rows
        if selected_rows:
            selected_idx = selected_rows[0]
            target_record = filtered_df.iloc[selected_idx]
            
            st.markdown("---")
            st.markdown(f"#### 📄 เตรียมรายงานของ: **{target_record['notes']}**")
            
            with st.spinner("กำลังประกอบไฟล์ PDF..."):
                try:
                    date_obj = pd.to_datetime(target_record['date'])
                    case_id = f"CYBOW-{date_obj.strftime('%Y%m%d')}-{selected_idx:03d}"
                    table_data = prepare_table_data(target_record)
                    
                    # 🌟 Robust JSON parsing with Unicode escape handling + Text sanitization
                    db_summary = target_record.get('clinical_summary', 'ไม่มีบันทึกข้อบ่งชี้ทางคลินิกในระบบ')
                    raw_bullets = target_record.get('clinical_bullets', '[]')
                    db_bullets = parse_clinical_bullets(raw_bullets, sanitize=True)

                    pdf_bytes = create_pdf(
                        patient_name=target_record['notes'],
                        case_id=case_id,
                        date_str=str(target_record['date']),
                        table_data=table_data,
                        summary_text=sanitize_thai_text(db_summary),
                        bullet_points=db_bullets
                    )

                    if pdf_bytes:
                        st.download_button(
                            label=f"⬇️ โหลด PDF: {target_record['notes']}",
                            data=pdf_bytes,
                            file_name=f"{case_id}_{target_record['notes'].replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"❌ ระบบออกรายงานขัดข้อง: {e}")

    else:
        # ========================================
        # 👤 Individual Patient Report
        # ========================================
        patient_name = selected_patient
        patient_df = df[df['notes'] == patient_name].copy()

        if patient_df.empty:
            st.warning("⚠️ ไม่พบข้อมูลผู้ป่วย")
        else:
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.markdown(f"### 👤 รายงานผลตรวจ: **{patient_name}**")
                latest_date = patient_df.iloc[0]['date']
                st.caption(f"🕐 ตรวจล่าสุด: {latest_date} | 📊 มี {len(patient_df)} ครั้ง")

            latest = patient_df.iloc[0]
            st.markdown("#### 🔬 ผลตรวจล่าสุด")
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1: st.info(f"**🍬 Glucose**\n\n{latest['glucose']}")
            with col_r2: st.info(f"**🧪 Protein**\n\n{latest['protein']}")
            with col_r3: st.info(f"**🩸 Blood**\n\n{latest['blood']}")
            with col_r4: st.info(f"**⚗️ pH**\n\n{latest['ph']}")

            if 'clinical_summary' in latest and latest['clinical_summary']:
                st.markdown("#### 📝 สรุปผลการตรวจ")
                st.success(latest['clinical_summary'])
                if 'clinical_bullets' in latest and latest['clinical_bullets']:
                    try:
                        bullets = parse_clinical_bullets(latest['clinical_bullets'])
                        if bullets and isinstance(bullets, list):
                            st.markdown("**ข้อบ่งชี้ทางคลินิก:**")
                            for bullet in bullets: st.markdown(f"• {bullet}")
                    except: pass
            st.markdown("---")

            # Download Buttons
            st.markdown("#### 📥 ดาวน์โหลดรายงาน")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                display_cols = ['date', 'urobilinogen', 'glucose', 'bilirubin', 'ketones', 'specific_gravity', 'blood', 'ph', 'protein', 'nitrite', 'leukocytes', 'ascorbic_acid']
                csv_data = patient_df[display_cols].to_csv(index=False).encode('utf-8')
                st.download_button(label="📊 ดาวน์โหลด CSV", data=csv_data, file_name=f"Urine_Report_{patient_name.replace(' ', '_')}.csv", mime="text/csv", use_container_width=True)

            with col_d2:
                try:
                    date_obj = pd.to_datetime(latest['date'])
                    case_id = f"CYBOW-{date_obj.strftime('%Y%m%d')}-001"
                    table_data = prepare_table_data(latest)
                    
                    # 🌟 Robust JSON parsing with Unicode escape handling + Text sanitization
                    db_summary = latest.get('clinical_summary', 'ไม่มีบันทึกข้อบ่งชี้ทางคลินิกในระบบ')
                    raw_bullets = latest.get('clinical_bullets', '[]')
                    db_bullets = parse_clinical_bullets(raw_bullets, sanitize=True)

                    pdf_bytes = create_pdf(
                        patient_name=patient_name,
                        case_id=case_id,
                        date_str=str(latest['date']),
                        table_data=table_data,
                        summary_text=sanitize_thai_text(db_summary),
                        bullet_points=db_bullets
                    )

                    if pdf_bytes:
                        st.download_button(
                            label="📄 ดาวน์โหลดรายงาน PDF",
                            data=pdf_bytes,
                            file_name=f"{case_id}_{patient_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"❌ ระบบออกรายงานขัดข้อง: {e}")

            st.markdown("---")
            st.markdown("#### 📈 กราฟแนวโน้มสุขภาพ")
            tab1, tab2, tab3 = st.tabs(["⚗️ pH", "💧 Specific Gravity", "🧪 Custom"])
            with tab1:
                fig_ph = create_trend_chart(df, patient_name, 'ph', 'ค่า pH')
                if fig_ph: st.plotly_chart(fig_ph, use_container_width=True)
            with tab2:
                fig_sg = create_trend_chart(df, patient_name, 'specific_gravity', 'Specific Gravity')
                if fig_sg: st.plotly_chart(fig_sg, use_container_width=True)
            with tab3:
                param_options = {'pH': 'ph', 'Specific Gravity': 'specific_gravity', 'Glucose': 'glucose', 'Protein': 'protein', 'Blood': 'blood'}
                selected_param = st.selectbox("เลือกพารามิเตอร์:", list(param_options.keys()))
                if selected_param:
                    fig_custom = create_trend_chart(df, patient_name, param_options[selected_param], selected_param)
                    if fig_custom: st.plotly_chart(fig_custom, use_container_width=True)

# ========================================
# 📌 Footer
# ========================================
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ ข้อมูลระบบ\n- 🏥 **LHome Medical**\n- 🤖 **AI-Powered Analysis**\n- 📊 **Real-time Dashboard**\n- 🔒 **Secure & Private**")
st.sidebar.caption("© 2024 LHome Medical System")