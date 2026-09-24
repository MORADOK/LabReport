import unittest
from src.report_mapping import get_report_mapping, validate_all_allowed_values

class ReportMappingTests(unittest.TestCase):
    def test_every_allowed_value_round_trips(self):
        self.assertEqual(validate_all_allowed_values(), [])

    def test_result_is_not_replaced_by_severity_label(self):
        self.assertEqual(get_report_mapping("GLU", "++500(28)")["result"], "++500(28)")
        self.assertEqual(get_report_mapping("PRO", "+++300(3.0)")["result"], "+++300(3.0)")
        self.assertEqual(get_report_mapping("LEU", "+++500")["result"], "+++500")

    def test_neutral_flags(self):
        self.assertEqual(get_report_mapping("GLU", "neg.")["status"], "Not detected")
        self.assertEqual(get_report_mapping("GLU", "+250(14)")["status"], "Detected")
        self.assertEqual(get_report_mapping("SG", "1.000")["status"], "Outside reference")
        self.assertEqual(get_report_mapping("SG", "1.020")["status"], "Within reference")
        self.assertEqual(get_report_mapping("pH", "9.0")["status"], "Outside reference")
        self.assertEqual(get_report_mapping("NIT", "trace")["status"], "Detected")

if __name__ == "__main__":
    unittest.main()
