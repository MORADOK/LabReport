import streamlit as st
import sys
import os
import pandas as pd

# 1. จัดการ Path ให้รันบน Streamlit Cloud ได้ปลอดภัย
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.analysis import load_data, create_trend_chart

st.set_page_config(page_title="Dashboard | LHome Medical", page_icon="📊", layout="wide")

st.title("📊 LHome: สรุปผลการตรวจปัสสาวะ")
st.markdown("---")

df = load_data()

# ---------------------------------------------------------
# 🌟 ฟังก์ชันวิเคราะห์ความผิดปกติ (Data Visualization)
# ---------------------------------------------------------
def highlight_abnormal(val):
    if pd.isna(val) or val == 'N/A':
        return ''
    val_str = str(val).strip()
    # Keyword ความผิดปกติตามมาตรฐาน CYBOW 11M
    abnormal_keywords = ['+', 'pos.', 'trace', 'Hemolysis', '(16)', '(33)', '(66)', '(131)']
    if any(keyword in val_str for keyword in abnormal_keywords):
        return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
    return 'color: #065f46;'

if df.empty:
    st.warning("⚠️ ยังไม่มีข้อมูลในระบบ หรือยังไม่ได้บันทึกข้อมูลผ่าน LINE Bot ครับ")
else:
    # --- ส่วนที่ 1: KPI Metrics ---
    st.markdown("### 📈 ภาพรวมวันนี้")
    valid_patients = df[df['notes'].astype(bool)]['notes'].unique().tolist()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="ผู้ป่วยที่ตรวจทั้งหมด", value=f"{len(valid_patients)} คน")
    with col2:
        st.metric(label="จำนวนครั้งที่ตรวจทั้งหมด", value=f"{len(df)} เคส")
    with col3:
        abnormal_blood = len(df[~df['blood'].astype(str).str.contains('neg', case=False, na=True)])
        st.metric(label="พบความเสี่ยง (Blood)", value=f"{abnormal_blood} เคส")
    with col4:
        st.metric(label="สถานะ Data Sync", value="Up to date 🔄")

    st.markdown("---")

    # --- ส่วนที่ 2: ฟิลเตอร์และตารางข้อมูล ---
    st.sidebar.header("🔍 ระบบค้นหา")
    selected_patient = st.sidebar.selectbox("เลือกชื่อผู้ป่วย:", ["แสดงทั้งหมด"] + valid_patients)

    display_cols = ['date', 'urobilinogen', 'glucose', 'bilirubin', 'ketones', 
                    'specific_gravity', 'blood', 'ph', 'protein', 'nitrite', 
                    'leukocytes', 'ascorbic_acid']

    if selected_patient == "แสดงทั้งหมด":
        st.subheader("📋 ประวัติการตรวจทั้งหมด (All Records)")
        with st.container(border=True):
            st.dataframe(
                df[display_cols + ['notes']].style.map(highlight_abnormal), 
                use_container_width=True, height=500
            )
    else:
        st.subheader(f"📋 รายงานผลตรวจของ: {selected_patient}")
        patient_df = df[df['notes'] == selected_patient]
        
        with st.container(border=True):
            st.dataframe(
                patient_df[display_cols].style.map(highlight_abnormal), 
                use_container_width=True
            )
        
        csv_data = patient_df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"🖨️ ดาวน์โหลดรายงาน (CSV) - {selected_patient}",
            data=csv_data,
            file_name=f"LHome_Urine_Report_{selected_patient.replace(' ', '_')}.csv",
            mime="text/csv",
            type="primary"
        )
        
        st.markdown("---")
        
        # --- ส่วนที่ 3: กราฟแนวโน้มสุขภาพ ---
        st.subheader("📉 วิเคราะห์แนวโน้มสุขภาพ (Health Trends)")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_ph = create_trend_chart(df, selected_patient, 'ph', 'ค่า pH')
            if fig_ph: st.plotly_chart(fig_ph, use_container_width=True)
        with col_g2:
            fig_sg = create_trend_chart(df, selected_patient, 'specific_gravity', 'ค่า Specific Gravity')
            if fig_sg: st.plotly_chart(fig_sg, use_container_width=True)