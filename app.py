import streamlit as st

st.set_page_config(
    page_title="LHome Medical | Urine Tracker",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS เพื่อตกแต่ง Card ให้ดูทันสมัย
st.markdown("""
    <style>
    .main-card {
        background-color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        background-color: #d1fae5;
        color: #065f46;
        font-weight: 600;
        font-size: 0.875rem;
    }
    </style>
""", unsafe_allow_html=True)

# ส่วน Header
st.markdown("""
    <div class="main-card">
        <h1 style='color: #0066cc; margin-bottom: 0;'>🏥 LHome Urine Tracker</h1>
        <p style='color: #64748b; font-size: 1.1rem;'>ระบบวิเคราะห์และจัดการผลตรวจปัสสาวะ CYBOW 11M อัตโนมัติ</p>
    </div>
""", unsafe_allow_html=True)

# ส่วนแสดงข้อมูลและเมนู
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📋 เริ่มต้นการใช้งาน")
    st.info("👈 **คลิกที่เมนู '1 Dashboard'** บริเวณแถบด้านซ้ายมือ เพื่อเข้าสู่หน้ารายงานผล สถิติคนไข้ และดาวน์โหลดข้อมูล")
    
with col2:
    st.markdown("### ⚡ สถานะระบบ")
    st.markdown("<span class='status-badge'>🟢 AI Vision: Online</span>", unsafe_allow_html=True)
    st.markdown("<br><span class='status-badge'>🟢 LINE Bot: Active</span>", unsafe_allow_html=True)
    st.markdown("<br><span class='status-badge'>🟢 Database: Connected</span>", unsafe_allow_html=True)

st.divider()
st.caption("© 2026 LHome Medical Center - Developed with Python & Streamlit")