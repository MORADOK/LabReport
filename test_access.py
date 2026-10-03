import os
import unittest
from unittest.mock import patch

from src.access import _accounts, _fingerprint, _remember_token, _verify_remember_token


class AccessTests(unittest.TestCase):
    def test_admin_and_staff_passwords_create_separate_roles(self):
        with patch.dict(
            os.environ,
            {
                "DASHBOARD_PASSWORD": "admin-secret",
                "DASHBOARD_STAFF_PASSWORD": "staff-secret",
            },
            clear=False,
        ):
            accounts = _accounts()
        roles = {item["role"]: item["password"] for item in accounts}
        self.assertEqual(roles["admin"], "admin-secret")
        self.assertEqual(roles["staff"], "staff-secret")

    def test_staff_account_not_enabled_without_password(self):
        with patch.dict(
            os.environ,
            {"DASHBOARD_STAFF_PASSWORD": ""},
            clear=False,
        ):
            accounts = _accounts()
        self.assertFalse(any(x["role"] == "staff" for x in accounts))

    def test_fingerprint_is_role_specific(self):
        self.assertNotEqual(
            _fingerprint("staff", "pw"),
            _fingerprint("admin", "pw"),
        )

    def test_remember_token_is_signed_and_expires(self):
        accounts = [{"role": "admin", "password": "secret", "label": "Admin"}]
        token = _remember_token("admin", "secret", 2000)
        self.assertEqual(_verify_remember_token(token, accounts, now=1000)["role"], "admin")
        self.assertIsNone(_verify_remember_token(token, accounts, now=2000))
        self.assertIsNone(_verify_remember_token(token + "x", accounts, now=1000))

    def test_remember_token_invalidates_when_password_changes(self):
        token = _remember_token("admin", "old-secret", 2000)
        changed = [{"role": "admin", "password": "new-secret", "label": "Admin"}]
        self.assertIsNone(_verify_remember_token(token, changed, now=1000))

    def test_same_password_would_match_first_account_so_should_be_avoided(self):
        with patch.dict(
            os.environ,
            {
                "DASHBOARD_PASSWORD": "same",
                "DASHBOARD_STAFF_PASSWORD": "same",
            },
            clear=False,
        ):
            accounts = _accounts()
        self.assertEqual(accounts[0]["role"], "admin")
        self.assertEqual(accounts[1]["role"], "staff")


if __name__ == "__main__":
    unittest.main()
