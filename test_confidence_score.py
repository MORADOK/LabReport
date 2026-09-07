import io
import unittest
from PIL import Image
from src.image_diagnostics import prepare_image, image_quality, sample_regions
from src.cybow_reference import calculate_confidence_from_rgb as similarity
from src.standards import valid_rgb

class ImageTests(unittest.TestCase):
    def test_perfect_color_and_invalid_inputs(self):
        self.assertEqual(similarity([92,151,185], "glucose", "neg."), 100)
        for rgb in (None, [], [1,2,"3"], [0,0,float("nan")], [-1,2,3], [True,2,3], [256,2,3]):
            self.assertFalse(valid_rgb(rgb))
            self.assertIsNone(similarity(rgb, "glucose", "neg."))

    def test_conflicting_references_disabled(self):
        for param in ("blood",):
            self.assertIsNone(similarity([100,100,100], param, "neg."))

    def test_color_normalization_corrects_channel_cast(self):
        from src.image_diagnostics import normalize_rgb
        n = {"gains": [1.1, 0.9, 1.0]}
        self.assertEqual(normalize_rgb([100, 100, 100], n), [110.0, 90.0, 100.0])

    def test_neutral_reference_reports_safe_gains(self):
        from src.image_diagnostics import estimate_neutral_reference
        image = Image.new("RGB", (200, 200), (210, 200, 190))
        result = estimate_neutral_reference(image)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["method"], "bright_low_saturation_white_balance_v1")
        self.assertEqual(len(result["gains"]), 3)

    def test_ref0974_calibration_key_colors(self):
        from src.standards import CYBOW_11M_STANDARDS, CALIBRATION_SOURCE
        self.assertIn("REF 0974", CALIBRATION_SOURCE)
        def rgb(param, value):
            return next(x["rgb"] for x in CYBOW_11M_STANDARDS[param] if x["value"] == value)
        self.assertEqual(rgb("blood", "neg."), (190,179,38))
        self.assertEqual(rgb("specific_gravity", "1.000"), (16,53,79))
        self.assertEqual(rgb("specific_gravity", "1.030"), (169,130,52))
        self.assertEqual(rgb("ascorbic_acid", "neg."), (29,97,102))
        self.assertEqual(rgb("ascorbic_acid", "++40(2.4)"), (173,167,30))

    def test_similarity_bounds(self):
        for n in range(256):
            score = similarity([n,n,n], "glucose", "neg.")
            self.assertTrue(0 <= score <= 100)

    def test_pixels_are_sampled(self):
        image = Image.new("RGB", (200,200), (92,151,185))
        result = sample_regions(image, {"glucose":[.1,.1,.4,.4]}, {"glucose":"neg."})
        self.assertEqual(result["detected_rgb"]["glucose"], [92,151,185])
        self.assertEqual(result["color_similarity_scores"]["glucose"], 100)

    def test_invalid_and_overlapping_regions(self):
        image = Image.new("RGB", (200,200))
        for region in (None, [0,0,2,1], [1,1,0,0], [0,0,float("nan"),1], [0,0,.001,.001]):
            self.assertEqual(sample_regions(image, {"glucose":region}, {})["detected_rgb"], {})
        result = sample_regions(image, {"glucose":[0,0,.5,.5],"protein":[0,0,.5,.5]}, {})
        self.assertEqual(len(result["detected_rgb"]), 1)

    def test_quality_rejects_blank_dark_and_tiny(self):
        for size, color in (((200,200),"white"), ((200,200),"black"), ((20,20),"red")):
            self.assertFalse(image_quality(Image.new("RGB",size,color))["accepted"])

    def test_quality_accepts_textured_image(self):
        image = Image.effect_noise((300,300),40).convert("RGB")
        self.assertTrue(image_quality(image)["accepted"])

    def test_resize_and_corrupt_input(self):
        buffer = io.BytesIO()
        Image.new("RGB",(2000,1000)).save(buffer, format="PNG")
        self.assertEqual(prepare_image(buffer.getvalue()).size,(1536,768))
        with self.assertRaises(Exception):
            prepare_image(b"invalid")

if __name__ == "__main__":
    unittest.main()
