import unittest
from PIL import Image, ImageDraw
from src.strip_geometry import detect_geometry_regions
from src.standards import ALLOWED_VALUES, CYBOW_11M_STANDARDS


class GeometryTests(unittest.TestCase):
    def _synthetic_strip(self, reverse=False):
        image = Image.new("RGB", (1000, 360), (230, 230, 225))
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 145, 920, 215), fill=(215, 215, 210))
        params = list(ALLOWED_VALUES)
        colors = [CYBOW_11M_STANDARDS[p][0]["rgb"] for p in params]
        sequence = [(205, 202, 195)] + colors
        if reverse:
            sequence = list(reversed(sequence))
        centers = [150 + i * 58 for i in range(12)]
        for cx, color in zip(centers, sequence):
            draw.rectangle((cx - 18, 163, cx + 18, 197), fill=color)
        reagent_centers = list(reversed(centers[:-1])) if reverse else centers[1:]
        ai = {}
        for param, cx in zip(params, reagent_centers):
            x = cx / image.width
            ai[param] = [x - .02, .44, x + .02, .56]
        return image, ai

    def test_detects_12_position_lattice(self):
        image, ai = self._synthetic_strip(False)
        result = detect_geometry_regions(image, ai)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["source"], "pixel_geometry_lattice_v2_anchor_refined")
        self.assertEqual(len(result["regions"]), 11)
        self.assertGreaterEqual(result["matched_components"], 8)
        self.assertGreaterEqual(result["snapped_components"], 8)
        self.assertLess(result["residual_ratio"], 0.18)

    def test_resolves_reverse_orientation(self):
        image, ai = self._synthetic_strip(True)
        result = detect_geometry_regions(image, ai)
        self.assertTrue(result["accepted"], result)
        box = result["regions"]["urobilinogen"]
        detected_x = (box[0] + box[2]) / 2
        ai_box = ai["urobilinogen"]
        ai_x = (ai_box[0] + ai_box[2]) / 2
        self.assertLess(abs(detected_x - ai_x), 0.04)

    def test_rejects_blank_image(self):
        image = Image.new("RGB", (800, 400), "white")
        result = detect_geometry_regions(image, {})
        self.assertFalse(result["accepted"])


if __name__ == "__main__":
    unittest.main()
