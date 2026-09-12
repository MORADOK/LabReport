import os
import unittest
from unittest.mock import patch

from src.access import _accounts, _fingerprint


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
