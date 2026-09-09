import unittest
from src.image_diagnostics import reconcile_results
from src.standards import ALLOWED_VALUES, CYBOW_11M_STANDARDS, UNVERIFIED_COLOR_PARAMETERS


class ResultFusionTests(unittest.TestCase):
    def _baseline(self):
        results = {}
        rgb = {}
        for p in ALLOWED_VALUES:
            refs = CYBOW_11M_STANDARDS.get(p, [])
            if p in UNVERIFIED_COLOR_PARAMETERS:
                results[p] = "neg."
                continue
            self.assertTrue(refs, p)
            results[p] = refs[0]["value"]
            rgb[p] = list(refs[0]["rgb"])
        return results, rgb

    def test_strong_pixel_evidence_can_correct_ai_label(self):
        results, rgb = self._baseline()
        refs = CYBOW_11M_STANDARDS["glucose"]
        target = refs[1]
        results["glucose"] = refs[0]["value"]
        rgb["glucose"] = list(target["rgb"])
        fused = reconcile_results(results, rgb)
        self.assertTrue(fused["accepted"], fused)
        self.assertEqual(fused["resolved_results"]["glucose"], target["value"])
        self.assertEqual(fused["decisions"]["glucose"]["source"], "pixel_primary")

    def test_far_color_requires_review(self):
        results, rgb = self._baseline()
        rgb["ascorbic_acid"] = [255, 255, 255]
        fused = reconcile_results(results, rgb)
        self.assertFalse(fused["accepted"])
        self.assertIn("ascorbic_acid", fused["review"])

    def test_distant_high_margin_color_cannot_be_pixel_primary(self):
        results, rgb = self._baseline()
        results["ketones"] = "neg."
        rgb["ketones"] = [128, 115, 34]
        fused = reconcile_results(results, rgb)
        self.assertFalse(fused["accepted"])
        self.assertIn("ketones", fused["review"])
        self.assertNotEqual(fused["decisions"]["ketones"]["source"], "pixel_primary")

    def test_neutral_background_cannot_create_positive_result(self):
        results, rgb = self._baseline()
        results["protein"] = "neg."
        rgb["protein"] = [186, 187, 188]
        fused = reconcile_results(results, rgb)
        self.assertFalse(fused["accepted"])
        self.assertIn("protein", fused["review"])

    def test_far_ai_tiebreak_is_rejected(self):
        results, rgb = self._baseline()
        results["ph"] = "6"
        rgb["ph"] = [177, 171, 163]
        fused = reconcile_results(results, rgb)
        self.assertFalse(fused["accepted"])
        self.assertIn("ph", fused["review"])


if __name__ == "__main__":
    unittest.main()
