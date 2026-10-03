"""Shared Streamlit dashboard authentication with admin/staff roles."""
import hashlib
import hmac
import os
import time

REMEMBER_COOKIE = "home_lab_remember"
REMEMBER_MAX_AGE = 30 * 24 * 60 * 60


def _remember_token(role: str, password: str, expires_at: int) -> str:
    """Create a signed login token without storing the password itself."""
    payload = f"{role}.{int(expires_at)}"
    key = _fingerprint(role, password).encode("ascii")
    signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _verify_remember_token(token: str, accounts, now=None):
    try:
        role, expires_text, signature = str(token or "").split(".", 2)
        expires_at = int(expires_text)
    except (TypeError, ValueError):
        return None

    if expires_at <= int(time.time() if now is None else now):
        return None

    account = next((item for item in accounts if item["role"] == role), None)
    if not account:
        return None

    expected = _remember_token(role, account["password"], expires_at)
    if not hmac.compare_digest(expected, str(token)):
        return None
    return account


def _fingerprint(role: str, password: str) -> str:
    raw = f"{role}\0{password}".encode("utf-8")
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
    if admin_password:
        accounts.append(
            {
                "password": admin_password,
                "role": "admin",
                "label": "ผู้ดูแลระบบ",
            }
        )

    staff_password = _setting("DASHBOARD_STAFF_PASSWORD", "", st=st)
    if staff_password:
        accounts.append(
            {
                "password": staff_password,
                "role": "staff",
                "label": "พนักงาน",
            }
        )

    return accounts


def current_dashboard_user(st):
    auth = st.session_state.get("_dashboard_auth")
    if isinstance(auth, dict) and auth.get("role"):
        return {"role": auth["role"]}
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

    from streamlit_cookies_controller import CookieController

    cookies = CookieController()
    auth = st.session_state.get("_dashboard_auth")
    if not isinstance(auth, dict):
        remembered = _verify_remember_token(cookies.get(REMEMBER_COOKIE), accounts)
        if remembered:
            auth = {
                "role": remembered["role"],
                "fingerprint": _fingerprint(remembered["role"], remembered["password"]),
            }
            st.session_state["_dashboard_auth"] = auth

    if isinstance(auth, dict):
        account = next(
            (item for item in accounts if item["role"] == auth.get("role")),
            None,
        )
        if account:
            expected_fp = _fingerprint(account["role"], account["password"])
            if hmac.compare_digest(str(auth.get("fingerprint", "")), expected_fp):
                if allowed_roles and account["role"] not in set(allowed_roles):
                    st.error("บัญชีนี้ไม่มีสิทธิ์เข้าถึงหน้านี้")
                    st.stop()

                role_text = "Admin" if account["role"] == "admin" else "Staff"
                st.sidebar.caption(f"👤 เข้าสู่ระบบเป็น {role_text}")
                if st.sidebar.button("ออกจากระบบ", key="_dashboard_logout"):
                    st.session_state.pop("_dashboard_auth", None)
                    cookies.remove(REMEMBER_COOKIE)
                    st.rerun()
                return {"role": account["role"]}

    with st.form("dashboard_login"):
        password = st.text_input("รหัสผ่าน", type="password")
        remember = st.checkbox("จดจำการเข้าสู่ระบบบนเครื่องนี้", value=True)
        submitted = st.form_submit_button("เข้าสู่ระบบ")

    if submitted:
        matched = None
        for account in accounts:
            if hmac.compare_digest(password.encode(), account["password"].encode()):
                matched = account
                break

        if matched:
            if allowed_roles and matched["role"] not in set(allowed_roles):
                st.error("รหัสผ่านนี้ไม่มีสิทธิ์เข้าถึงหน้านี้")
                st.stop()
            st.session_state["_dashboard_auth"] = {
                "role": matched["role"],
                "fingerprint": _fingerprint(matched["role"], matched["password"]),
            }
            if remember:
                expires_at = int(time.time()) + REMEMBER_MAX_AGE
                cookies.set(
                    REMEMBER_COOKIE,
                    _remember_token(matched["role"], matched["password"], expires_at),
                    max_age=REMEMBER_MAX_AGE,
                    same_site="strict",
                )
            else:
                cookies.remove(REMEMBER_COOKIE)
            st.rerun()

        st.error("รหัสผ่านไม่ถูกต้อง")

    st.stop()
