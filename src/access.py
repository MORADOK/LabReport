"""Shared Streamlit dashboard authentication with admin/staff roles."""
import hashlib
import hmac
import os


DEFAULT_STAFF_USERNAME = "Homestaff01"


def _fingerprint(username: str, role: str, password: str) -> str:
    raw = f"{username}\0{role}\0{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _setting(name: str, default: str = "", st=None) -> str:
    """Read Streamlit Secrets first, then environment variables."""
    if st is not None:
        try:
            value = st.secrets.get(name)
            if value is not None:
                return str(value)
        except Exception:
            pass
    value = os.getenv(name)
    return str(value) if value is not None else default


def _accounts(st=None):
    accounts = []

    admin_password = _setting("DASHBOARD_PASSWORD", "", st=st)
    admin_username = (
        _setting("DASHBOARD_ADMIN_USERNAME", "admin", st=st).strip() or "admin"
    )
    if admin_password:
        accounts.append(
            {
                "username": admin_username,
                "password": admin_password,
                "role": "admin",
                "label": "ผู้ดูแลระบบ",
            }
        )

    staff_username = _setting(
        "DASHBOARD_STAFF_USERNAME", DEFAULT_STAFF_USERNAME, st=st
    ).strip()
    staff_password = _setting("DASHBOARD_STAFF_PASSWORD", "", st=st)
    if staff_username and staff_password:
        accounts.append(
            {
                "username": staff_username,
                "password": staff_password,
                "role": "staff",
                "label": "พนักงาน",
            }
        )

    return accounts


def current_dashboard_user(st):
    auth = st.session_state.get("_dashboard_auth")
    if isinstance(auth, dict) and auth.get("username") and auth.get("role"):
        return {"username": auth["username"], "role": auth["role"]}
    return None


def require_dashboard_login(st=None, allowed_roles=None):
    if st is None:
        import streamlit as st

    accounts = _accounts(st=st)
    if not accounts:
        st.error(
            "กรุณาตั้งค่า DASHBOARD_PASSWORD หรือ DASHBOARD_STAFF_PASSWORD "
            "ใน Streamlit Secrets หรือ Environment Variables ก่อนใช้งาน"
        )
        st.stop()

    auth = st.session_state.get("_dashboard_auth")
    if isinstance(auth, dict):
        account = next(
            (
                item
                for item in accounts
                if item["username"] == auth.get("username")
                and item["role"] == auth.get("role")
            ),
            None,
        )
        if account:
            expected_fp = _fingerprint(
                account["username"], account["role"], account["password"]
            )
            if hmac.compare_digest(str(auth.get("fingerprint", "")), expected_fp):
                if allowed_roles and account["role"] not in set(allowed_roles):
                    st.error("บัญชีนี้ไม่มีสิทธิ์เข้าถึงหน้านี้")
                    st.stop()

                role_text = "Admin" if account["role"] == "admin" else "Staff"
                st.sidebar.caption(f"👤 {account['username']} • {role_text}")
                if st.sidebar.button("ออกจากระบบ", key="_dashboard_logout"):
                    st.session_state.pop("_dashboard_auth", None)
                    st.rerun()
                return {
                    "username": account["username"],
                    "role": account["role"],
                }

    with st.form("dashboard_login"):
        username = st.text_input("ชื่อผู้ใช้", placeholder="Username")
        password = st.text_input("รหัสผ่าน", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ")

    if submitted:
        submitted_username = username.strip()
        for account in accounts:
            if (
                hmac.compare_digest(
                    submitted_username.casefold(), account["username"].casefold()
                )
                and hmac.compare_digest(password.encode(), account["password"].encode())
            ):
                if allowed_roles and account["role"] not in set(allowed_roles):
                    st.error("บัญชีนี้ไม่มีสิทธิ์เข้าถึงหน้านี้")
                    st.stop()
                st.session_state["_dashboard_auth"] = {
                    "username": account["username"],
                    "role": account["role"],
                    "fingerprint": _fingerprint(
                        account["username"], account["role"], account["password"]
                    ),
                }
                st.rerun()
        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    st.stop()
