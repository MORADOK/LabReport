import streamlit as st
import sys
import os
import json
import pandas as pd
from datetime import datetime
from src.pdf_generator import create_pdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.analysis import load_data, create_trend_chart

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
    /* Header Styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="metric-container"] > label {
        color: white !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] > div {
        color: white !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    /* Table Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Button Styling */
    .stDownloadButton button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }

    /* Container Styling */
    div[data-testid="stVerticalBlock"] > div:has(> div.element-container) {
        background-color: white;
        border-radius: 12px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# 📊 Load Data
# ========================================
with st.spinner("🔄 กำลังโหลดข้อมูล..."):
    df = load_data()

# ========================================
# 🎨 Header Section
# ========================================
st.markdown('<h1 class="main-header">🏥 LHome Medical Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">ระบบวิเคราะห์ผลตรวจปัสสาวะด้วย AI | Urine Analysis System</p>', unsafe_allow_html=True)

# ========================================
# 📈 Main Dashboard
# ========================================
if df.empty:
    st.info("📭 ยังไม่มีข้อมูลในระบบ")
    st.markdown("""
    ### วิธีการใช้งาน:
    1. 🤖 เพิ่มเพื่อน LINE Bot
    2. 📸 ส่งรูปแผ่นตรวจปัสสาวะ
    3. 📝 ระบุชื่อ-นามสกุลผู้ป่วย
    4. ✅ รอระบบวิเคราะห์และบันทึกข้อมูล
    5. 📊 ดูผลการตรวจที่ Dashboard นี้
    """)
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

    with col1:
        st.metric(
            label="👥 ผู้ป่วยทั้งหมด",
            value=f"{len(valid_patients)}",
            delta="คน"
        )

    with col2:
        st.metric(
            label="📋 จำนวนการตรวจ",
            value=f"{total_records}",
            delta="เคส"
        )

    with col3:
        st.metric(
            label="🩸 พบเลือด",
            value=f"{abnormal_blood}",
            delta="เคส" if abnormal_blood > 0 else "ปกติ",
            delta_color="inverse"
        )

    with col4:
        st.metric(
            label="🧪 พบโปรตีน",
            value=f"{abnormal_protein}",
            delta="เคส" if abnormal_protein > 0 else "ปกติ",
            delta_color="inverse"
        )

    st.markdown("---")

    # ========================================
    # 🔍 Sidebar Filter
    # ========================================
    st.sidebar.markdown("## 🔍 เลือกข้อมูล")
    st.sidebar.markdown("---")

    selected_patient = st.sidebar.selectbox(
        "👤 เลือกผู้ป่วย:",
        ["📊 แสดงทั้งหมด"] + sorted(valid_patients),
        help="เลือกผู้ป่วยเพื่อดูรายงานส่วนบุคคล"
    )

    # ========================================
    # 📋 Data Display Section
    # ========================================
    if selected_patient == "📊 แสดงทั้งหมด":
        st.markdown("### 📋 รายการตรวจทั้งหมด")

        # Data filtering options
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            date_filter = st.date_input(
                "📅 กรองตามวันที่:",
                value=None,
                help="เลือกวันที่ต้องการดู (เว้นว่างเพื่อแสดงทั้งหมด)"
            )
        with col_f2:
            search_term = st.text_input(
                "🔎 ค้นหาชื่อ:",
                placeholder="พิมพ์ชื่อผู้ป่วย...",
                help="ค้นหาด้วยชื่อผู้ป่วย"
            )

        # Apply filters
        filtered_df = df.copy()
        if date_filter:
            filtered_df['date_only'] = pd.to_datetime(filtered_df['date']).dt.date
            filtered_df = filtered_df[filtered_df['date_only'] == date_filter]
        if search_term:
            filtered_df = filtered_df[filtered_df['notes'].str.contains(search_term, case=False, na=False)]

        # Display table
        display_cols = ['date', 'notes', 'glucose', 'protein', 'blood', 'ph',
                       'specific_gravity', 'ketones', 'leukocytes']

        with st.container():
            st.dataframe(
                filtered_df[display_cols],
                use_container_width=True,
                height=400,
                hide_index=True,
                column_config={
                    "date": st.column_config.DatetimeColumn("📅 วันที่", format="DD/MM/YYYY HH:mm"),
                    "notes": st.column_config.TextColumn("👤 ชื่อผู้ป่วย", width="medium"),
                    "glucose": st.column_config.TextColumn("🍬 Glucose"),
                    "protein": st.column_config.TextColumn("🧪 Protein"),
                    "blood": st.column_config.TextColumn("🩸 Blood"),
                    "ph": st.column_config.NumberColumn("⚗️ pH", format="%.1f"),
                    "specific_gravity": st.column_config.NumberColumn("💧 S.G.", format="%.3f")
                }
            )

        st.caption(f"📊 แสดง {len(filtered_df)} รายการจากทั้งหมด {len(df)} รายการ")

    else:
        # ========================================
        # 👤 Individual Patient Report
        # ========================================
        patient_name = selected_patient
        patient_df = df[df['notes'] == patient_name].copy()

        if patient_df.empty:
            st.warning("⚠️ ไม่พบข้อมูลผู้ป่วย")
        else:
            # Header with patient info
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.markdown(f"### 👤 รายงานผลตรวจ: **{patient_name}**")
                latest_date = patient_df.iloc[0]['date']
                st.caption(f"🕐 ตรวจล่าสุด: {latest_date} | 📊 มี {len(patient_df)} ครั้ง")

            # Latest Test Results in Cards
            st.markdown("#### 🔬 ผลตรวจล่าสุด")
            latest = patient_df.iloc[0]

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.info(f"**🍬 Glucose**\n\n{latest['glucose']}")
            with col_r2:
                st.info(f"**🧪 Protein**\n\n{latest['protein']}")
            with col_r3:
                st.info(f"**🩸 Blood**\n\n{latest['blood']}")
            with col_r4:
                st.info(f"**⚗️ pH**\n\n{latest['ph']}")

            # Clinical Summary (if available)
            if 'clinical_summary' in latest and latest['clinical_summary']:
                st.markdown("#### 📝 สรุปผลการตรวจ")
                st.success(latest['clinical_summary'])

                # Clinical bullets
                if 'clinical_bullets' in latest and latest['clinical_bullets']:
                    try:
                        bullets = json.loads(latest['clinical_bullets']) if isinstance(latest['clinical_bullets'], str) else latest['clinical_bullets']
                        if bullets:
                            st.markdown("**ข้อบ่งชี้ทางคลินิก:**")
                            for bullet in bullets:
                                st.markdown(f"• {bullet}")
                    except:
                        pass

            st.markdown("---")

            # Full Data Table
            st.markdown("#### 📊 ข้อมูลทั้งหมด")
            display_cols = ['date', 'urobilinogen', 'glucose', 'bilirubin', 'ketones',
                           'specific_gravity', 'blood', 'ph', 'protein', 'nitrite',
                           'leukocytes', 'ascorbic_acid']

            with st.container():
                st.dataframe(
                    patient_df[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "date": st.column_config.DatetimeColumn("📅 วันที่", format="DD/MM/YYYY HH:mm")
                    }
                )

            # Download Buttons
            st.markdown("#### 📥 ดาวน์โหลดรายงาน")
            col_d1, col_d2 = st.columns(2)

            with col_d1:
                csv_data = patient_df[display_cols].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 ดาวน์โหลด CSV",
                    data=csv_data,
                    file_name=f"Urine_Report_{patient_name.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with col_d2:
                if st.button("📄 สร้างรายงาน PDF", use_container_width=True, type="primary"):
                    with st.spinner("🔄 กำลังสร้าง PDF..."):
                        table_data = {
                            "GLU (กลูโคส)": latest['glucose'],
                            "BIL (บิลิรูบิน)": latest['bilirubin'],
                            "KET (คีโตน)": latest['ketones'],
                            "SG (ความถ่วงจำเพาะ)": latest['specific_gravity'],
                            "BLO (เลือด)": latest['blood'],
                            "pH (ความเป็นกรด-ด่าง)": latest['ph'],
                            "PRO (โปรตีน)": latest['protein'],
                            "URO (ยูโรบิลิโนเจน)": latest['urobilinogen'],
                            "NIT (ไนไตรต์)": latest['nitrite'],
                            "LEU (เม็ดเลือดขาว)": latest['leukocytes'],
                            "ASC (วิตามินซี)": latest['ascorbic_acid']
                        }

                        try:
                            db_bullets = json.loads(latest.get('clinical_bullets', '[]'))
                        except:
                            db_bullets = []

                        db_summary = latest.get('clinical_summary', 'ไม่มีบันทึกข้อบ่งชี้ทางคลินิกในระบบ')

                        pdf_bytes = create_pdf(
                            patient_name=patient_name,
                            date_str=str(latest['date']),
                            table_data=table_data,
                            summary_text=db_summary,
                            bullet_points=db_bullets
                        )

                        st.download_button(
                            label="⬇️ คลิกดาวน์โหลด PDF",
                            data=pdf_bytes,
                            file_name=f"LHome_Report_{patient_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

            # Health Trends
            st.markdown("---")
            st.markdown("#### 📈 กราฟแนวโน้มสุขภาพ")

            tab1, tab2, tab3 = st.tabs(["⚗️ pH", "💧 Specific Gravity", "🧪 Custom"])

            with tab1:
                fig_ph = create_trend_chart(df, patient_name, 'ph', 'ค่า pH')
                if fig_ph:
                    st.plotly_chart(fig_ph, use_container_width=True)
                else:
                    st.info("ไม่มีข้อมูลกราฟ pH")

            with tab2:
                fig_sg = create_trend_chart(df, patient_name, 'specific_gravity', 'Specific Gravity')
                if fig_sg:
                    st.plotly_chart(fig_sg, use_container_width=True)
                else:
                    st.info("ไม่มีข้อมูลกราฟ Specific Gravity")

            with tab3:
                param_options = {
                    'pH': 'ph',
                    'Specific Gravity': 'specific_gravity',
                    'Glucose': 'glucose',
                    'Protein': 'protein',
                    'Blood': 'blood'
                }
                selected_param = st.selectbox("เลือกพารามิเตอร์:", list(param_options.keys()))

                if selected_param:
                    fig_custom = create_trend_chart(df, patient_name, param_options[selected_param], selected_param)
                    if fig_custom:
                        st.plotly_chart(fig_custom, use_container_width=True)
                    else:
                        st.info(f"ไม่มีข้อมูลกราฟ {selected_param}")

# ========================================
# 📌 Footer
# ========================================
st.sidebar.markdown("---")
st.sidebar.markdown("""
### ℹ️ ข้อมูลระบบ
- 🏥 **LHome Medical**
- 🤖 **AI-Powered Analysis**
- 📊 **Real-time Dashboard**
- 🔒 **Secure & Private**
""")
st.sidebar.caption("© 2024 LHome Medical System")
