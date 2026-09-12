import unittest
from src.report_preview import build_report_preview_html

class ReportPreviewTests(unittest.TestCase):
    def test_preview_contains_print_button_and_all_rows(self):
        rows = [[f"P{i}", str(i), "ref", "color", "Normal"] for i in range(11)]
        page = build_report_preview_html("ผู้ป่วยทดสอบ", "CASE-1", "2026-09-12", rows, "สรุปผล", ["ข้อแนะนำ"])
        self.assertIn("window.print()", page)
        self.assertIn("พิมพ์รายงาน", page)
        self.assertEqual(page.count("<tr>"), 12)  # 1 header + 11 data rows
        self.assertIn("ผู้ป่วยทดสอบ", page)

    def test_preview_escapes_html(self):
        page = build_report_preview_html("<script>", "CASE", "DATE", [["<b>", "1", "r", "c", "Normal"]], "<x>", [])
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("&lt;b&gt;", page)

if __name__ == "__main__":
    unittest.main()
