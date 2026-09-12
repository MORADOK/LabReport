import re
import unittest

from src.pdf_generator import create_pdf


class PDFGeneratorTests(unittest.TestCase):
    def _table(self):
        return [
            ["URO (ยูโรบิลิโนเจน)", "0.1 Normal", "0.1-1.0", "cream", "Normal"],
            ["GLU (กลูโคส)", "neg.", "Negative", "blue", "Normal"],
            ["BIL (บิลิรูบิน)", "neg.", "Negative", "beige", "Normal"],
            ["KET (คีโตน)", "neg.", "Negative", "beige", "Normal"],
            ["SG (ความถ่วงจำเพาะ)", "1.020", "1.005-1.030", "olive", "Normal"],
            ["BLO (เลือด)", "neg.", "Negative", "yellow", "Normal"],
            ["pH (ความเป็นกรด-ด่าง)", "6.5", "5.0-8.0", "yellow", "Normal"],
            ["PRO (โปรตีน)", "neg.", "Negative", "green", "Normal"],
            ["NIT (ไนไตรต์)", "neg.", "Negative", "cream", "Normal"],
            ["LEU (เม็ดเลือดขาว)", "neg.", "Negative", "pink", "Normal"],
            ["ASC (วิตามินซี)", "neg.", "Negative", "teal", "Normal"],
        ]

    def test_standard_report_is_single_page(self):
        data = create_pdf(
            patient_name="ผู้ป่วยทดสอบ",
            case_id="CYBOW-TEST",
            date_str="2026-09-12 08:00",
            table_data=self._table(),
            summary_text="ผลตรวจโดยรวมไม่พบค่าผิดปกติเด่นชัด",
            bullet_points=["ติดตามอาการตามความเหมาะสม", "พิจารณาตรวจซ้ำตามข้อบ่งชี้"],
        )
        # FPDF emits one /Type /Page object per physical page plus /Pages.
        pages = len(re.findall(rb"/Type\s*/Page\b", data))
        self.assertEqual(pages, 1)

    def test_long_narrative_does_not_push_standard_results_to_second_page(self):
        data = create_pdf(
            patient_name="ผู้ป่วยชื่อยาวสำหรับทดสอบรายงาน",
            case_id="CYBOW-LONG",
            date_str="2026-09-12 08:00",
            table_data=self._table(),
            summary_text="สรุปผลและคำอธิบายเพิ่มเติม " * 40,
            bullet_points=["คำแนะนำทางคลินิกที่มีรายละเอียดเพิ่มเติม " * 8 for _ in range(8)],
        )
        pages = len(re.findall(rb"/Type\s*/Page\b", data))
        self.assertEqual(pages, 1)


if __name__ == "__main__":
    unittest.main()
