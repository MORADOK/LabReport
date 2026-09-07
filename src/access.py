"""Shared dashboard access gate. Configure DASHBOARD_PASSWORD before deployment."""
import hmac
import hashlib
import os

def require_dashboard_login(st):
    expected = os.getenv("DASHBOARD_PASSWORD", "")
    if not expected:
        st.error("ผู้ดูแลต้องตั้งค่า DASHBOARD_PASSWORD ก่อนเปิดรายงาน")
        st.stop()
    fingerprint = hashlib.sha256(expected.encode()).hexdigest()
    if st.session_state.get("_dashboard_auth") == fingerprint:
        if st.sidebar.button("ออกจากระบบ"):
            st.session_state.pop("_dashboard_auth", None)
            st.rerun()
        return
    with st.form("dashboard_login"):
        password = st.text_input("รหัสผ่านผู้ดูแล", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ")
    if submitted:
        if hmac.compare_digest(password.encode(), expected.encode()):
            st.session_state["_dashboard_auth"] = fingerprint
            st.rerun()
        st.error("รหัสผ่านไม่ถูกต้อง")
    st.stop()
