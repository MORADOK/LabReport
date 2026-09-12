import os
import unittest
from unittest.mock import patch

from src.access import DEFAULT_STAFF_USERNAME, _accounts, _fingerprint


class AccessTests(unittest.TestCase):
    def test_staff_account_uses_requested_username(self):
        with patch.dict(
            os.environ,
            {
                "DASHBOARD_PASSWORD": "admin-secret",
                "DASHBOARD_STAFF_USERNAME": "Homestaff01",
                "DASHBOARD_STAFF_PASSWORD": "staff-secret",
            },
            clear=False,
        ):
            accounts = _accounts()
        staff = next(x for x in accounts if x["role"] == "staff")
        self.assertEqual(staff["username"], "Homestaff01")
        self.assertEqual(staff["password"], "staff-secret")

    def test_staff_account_not_enabled_without_password(self):
        with patch.dict(
            os.environ,
            {
                "DASHBOARD_STAFF_USERNAME": DEFAULT_STAFF_USERNAME,
                "DASHBOARD_STAFF_PASSWORD": "",
            },
            clear=False,
        ):
            accounts = _accounts()
        self.assertFalse(any(x["role"] == "staff" for x in accounts))

    def test_fingerprint_is_role_specific(self):
        self.assertNotEqual(
            _fingerprint("Homestaff01", "staff", "pw"),
            _fingerprint("Homestaff01", "admin", "pw"),
        )


if __name__ == "__main__":
    unittest.main()
