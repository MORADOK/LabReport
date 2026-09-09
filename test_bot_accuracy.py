import ast
import json
import sys
import subprocess
import unittest
from pathlib import Path
from src.standards import ALLOWED_VALUES, normalize_value
from src.cybow_reference import enforce_strict_cybow_standards as validate, get_severity_level

class ValidationTests(unittest.TestCase):
    def test_every_canonical_value_survives(self):
        for param, values in ALLOWED_VALUES.items():
            for value in values:
                with self.subTest(param=param, value=value):
                    self.assertEqual(normalize_value(param, value), value)

    def test_missing_and_unreadable_are_unknown(self):
        for value in (None, "", "unreadable", "none", "not negative", True):
            self.assertIsNone(validate({"protein": value})["protein"])
        self.assertFalse(validate({})["is_valid"])

    def test_exact_morphology(self):
        self.assertEqual(normalize_value("blood", "Non Hemolysis ++50"), "Non Hemolysis ++50")
        self.assertIsNone(normalize_value("blood", "50"))
        self.assertIsNone(normalize_value("blood", "+10"))

    def test_numeric_aliases_are_whole_values(self):
        self.assertEqual(normalize_value("protein", "100 mg/dL"), "++100(1.0)")
        self.assertEqual(normalize_value("ph", 6.0), "6")
        for value in ("1", "1 mmol/L", "not 100", "-100", "100 or 300", "+100"):
            self.assertIsNone(normalize_value("protein", value))

    def test_severity_zero_and_unknown(self):
        self.assertEqual(get_severity_level("GLU", "0")[0], "normal")
        for param, val in (("GLU", "unknown"), ("pH", "NaN"), ("SG", None), ("xxx", "0")):
            self.assertEqual(get_severity_level(param, val)[0], "unknown")
        self.assertEqual(get_severity_level("PRO", "+30(0.3)")[0], "warning")

    def test_invalid_metadata_is_safe(self):
        for payload in ({"detected_rgb": None}, {"detected_rgb": []},
                        {"confidence_scores": {"glucose": 999}}, {"confidence_scores": {"glucose": "high"}}):
            result = validate(payload)
            self.assertIsNone(result["overall_confidence"])
            self.assertTrue(all(v is None for v in result["confidence_scores"].values()))

    def test_reject_non_object(self):
        for payload in (None, [], "text"):
            with self.assertRaises(ValueError):
                validate(payload)

    def test_complete_record_valid(self):
        payload = {p: values[0] for p, values in ALLOWED_VALUES.items()}
        self.assertTrue(validate(payload)["is_valid"])

    def test_imports_do_not_start_bot(self):
        # Run this assertion in a fresh interpreter so unrelated test modules
        # that legitimately exercise db_handler cannot make the result order-dependent.
        code = (
            "import sys; "
            "from src.standards import ALLOWED_VALUES; "
            "from src.cybow_reference import enforce_strict_cybow_standards; "
            "assert 'bot' not in sys.modules; "
            "assert 'src.db_handler' not in sys.modules"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == "__main__":
    unittest.main()
