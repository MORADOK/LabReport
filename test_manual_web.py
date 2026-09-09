import unittest
from unittest.mock import patch

from src.manual_web import render_manual_form, save_manual_submission, validate_results
from src.standards import ALLOWED_VALUES


class ManualWebTests(unittest.TestCase):
    def _results(self):
        return {k: values[0] for k, values in ALLOWED_VALUES.items()}

    @patch("src.manual_web.get_manual_case")
    def test_form_uses_server_side_patient_name(self, get_case):
        get_case.return_value = {
            "token": "abc", "patient_name": "นายทดสอบ ระบบ", "line_user_id": "U1",
            "status": "pending", "created_at": None, "completed_at": None,
            "valid": True, "reason": None,
        }
        status, page = render_manual_form("abc")
        self.assertEqual(status, 200)
        self.assertIn("นายทดสอบ ระบบ", page)
        self.assertIn("Urobilinogen", page)
        self.assertIn("Ascorbic acid", page)
        self.assertNotIn("name='patient_name'", page)

    def test_validate_requires_all_11_values(self):
        values = self._results()
        values.pop("protein")
        with self.assertRaises(ValueError):
            validate_results(values)

    @patch("src.manual_web.db_handler.complete_manual_case", return_value=True)
    @patch("src.manual_web.db_handler.insert_record", return_value=True)
    @patch("src.manual_web.summarize_manual_results")
    @patch("src.manual_web.db_handler.claim_manual_case", return_value=True)
    @patch("src.manual_web.get_manual_case")
    def test_save_locks_case_and_persists_ai_summary(self, get_case, claim, summarize, insert, complete):
        get_case.return_value = {
            "token": "abc", "patient_name": "นายทดสอบ ระบบ", "line_user_id": "U1",
            "status": "pending", "created_at": None, "completed_at": None,
            "valid": True, "reason": None,
        }
        summarize.return_value = {
            "summary": "สรุปทดสอบ", "bullets": ["ข้อสังเกต"],
            "ai_used": True, "model": "test-model",
        }
        result = save_manual_submission("abc", self._results())
        self.assertTrue(result["ai_used"])
        claim.assert_called_once_with("abc")
        insert.assert_called_once()
        kwargs = insert.call_args.kwargs
        self.assertEqual(kwargs["notes"], "นายทดสอบ ระบบ")
        self.assertEqual(kwargs["clinical_summary"], "สรุปทดสอบ")
        self.assertEqual(kwargs["diagnostics"]["entry_mode"], "line_manual_visual_ref_0974_ai_summary")
        complete.assert_called_once_with("abc")

    @patch("src.manual_web.db_handler.claim_manual_case", return_value=False)
    @patch("src.manual_web.get_manual_case")
    def test_duplicate_submit_is_rejected(self, get_case, claim):
        get_case.return_value = {
            "token": "abc", "patient_name": "นายทดสอบ ระบบ", "line_user_id": "U1",
            "status": "pending", "created_at": None, "completed_at": None,
            "valid": True, "reason": None,
        }
        with self.assertRaises(ValueError):
            save_manual_submission("abc", self._results())


if __name__ == "__main__":
    unittest.main()
