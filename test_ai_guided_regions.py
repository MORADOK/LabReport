import unittest
from PIL import Image, ImageDraw
from src.ai_guided_regions import detect_ai_guided_regions
from src.standards import ALLOWED_VALUES, CYBOW_11M_STANDARDS


class GuidedRegionTests(unittest.TestCase):
    def _image_and_ai(self, shift_x=-18, shift_y=14):
        image = Image.new("RGB", (1100, 360), (232, 232, 228))
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 145, 1020, 215), fill=(215, 215, 210))
        centers = [160 + i * 76 for i in range(11)]
        y = 180
        ai = {}
        for param, cx in zip(ALLOWED_VALUES, centers):
            color = CYBOW_11M_STANDARDS[param][0]["rgb"]
            draw.rectangle((cx-21, y-19, cx+21, y+19), fill=color)
            ex = (cx + shift_x) / image.width
            ey = (y + shift_y) / image.height
            ai[param] = [ex-.021, ey-.07, ex+.021, ey+.07]
        return image, ai, centers

    def test_refines_shifted_ai_regions_to_pixel_pads(self):
        image, ai, centers = self._image_and_ai()
        result = detect_ai_guided_regions(image, ai)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["source"], "ai_semantic_pixel_refined_v1")
        self.assertGreaterEqual(result["anchor_count"], 4)
        for param, expected_x in zip(ALLOWED_VALUES, centers):
            box = result["regions"][param]
            actual_x = ((box[0]+box[2])/2) * image.width
            self.assertLess(abs(actual_x-expected_x), 18)

    def test_rejects_incomplete_ai_regions(self):
        image = Image.new("RGB", (800, 300), "white")
        result = detect_ai_guided_regions(image, {})
        self.assertFalse(result["accepted"])

    def test_rejects_blank_image_without_pixel_anchors(self):
        image, ai, _ = self._image_and_ai()
        blank = Image.new("RGB", image.size, (230, 230, 230))
        result = detect_ai_guided_regions(blank, ai)
        self.assertFalse(result["accepted"])


if __name__ == "__main__":
    unittest.main()
