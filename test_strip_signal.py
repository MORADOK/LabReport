import unittest
from PIL import Image, ImageDraw
from src.strip_signal import detect_strip_signal_regions
from src.standards import ALLOWED_VALUES


class StripSignalTests(unittest.TestCase):
    def _fixture(self, slope=0.0, pale=False):
        w, h = 1200, 320
        img = Image.new("RGB", (w, h), (224, 224, 220))
        draw = ImageDraw.Draw(img)
        x0, y0, pitch = 180, 160, 72
        colors = [
            (190,170,155),(80,145,180),(190,170,135),(180,160,150),(140,135,55),
            (170,150,55),(175,130,50),(155,160,90),(195,185,170),(170,145,165),(35,95,100)
        ]
        if pale:
            colors[3] = (205,202,196)
            colors[8] = (214,211,205)
            colors[9] = (208,205,203)
        boxes = {}
        for i, p in enumerate(ALLOWED_VALUES):
            cx = x0 + pitch*i
            cy = y0 + slope*(i-5)
            draw.rectangle((cx-15, cy-20, cx+15, cy+20), fill=colors[i])
            acx = cx + 5
            acy = y0 + 9
            boxes[p] = [(acx-22)/w, (acy-45)/h, (acx+22)/w, (acy+45)/h]
        return img, boxes

    def test_joint_signal_finds_sloped_strip(self):
        img, boxes = self._fixture(slope=2.6)
        result = detect_strip_signal_regions(img, boxes)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["source"], "joint_strip_signal_v6_ascorbic_locked")
        self.assertLessEqual(abs(result["phase_pixels"]), result["pitch_pixels"] * 0.12 + 0.2)
        self.assertGreaterEqual(result["strong_pad_count"], 5)
        self.assertEqual(len(result["regions"]), 11)

    def test_joint_signal_handles_pale_negative_pads(self):
        img, boxes = self._fixture(slope=1.8, pale=True)
        result = detect_strip_signal_regions(img, boxes)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(len(result["regions"]), 11)

    def test_sparse_semantic_boxes_still_fit_full_strip(self):
        img, boxes = self._fixture(slope=2.0)
        keep = {0, 2, 5, 8, 10}
        sparse = {p: box for i, (p, box) in enumerate(boxes.items()) if i in keep}
        result = detect_strip_signal_regions(img, sparse)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["semantic_anchor_count"], 5)
        self.assertEqual(len(result["regions"]), 11)

    def test_adjacent_sparse_boxes_do_not_define_whole_strip(self):
        img, boxes = self._fixture()
        sparse = {p: box for i, (p, box) in enumerate(boxes.items()) if i < 5}
        result = detect_strip_signal_regions(img, sparse)
        self.assertFalse(result["accepted"])
        self.assertIn("span", result["reason"])

    def test_endpoint_refinement_can_correct_last_pad(self):
        img, boxes = self._fixture(slope=1.2)
        # Shift only the final reagent pad farther along the strip, simulating
        # perspective/end-fit error while keeping it well below one full pitch.
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        # Paint a strong ascorbic-colored pad slightly to the right of the nominal slot.
        x0, y0, pitch = 180, 160, 72
        cx = x0 + pitch*10 + 14
        cy = y0 + 1.2*(10-5)
        draw.rectangle((cx-15, cy-20, cx+15, cy+20), fill=(35,95,100))
        result = detect_strip_signal_regions(img, boxes)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["source"], "joint_strip_signal_v6_ascorbic_locked")
        self.assertEqual(len(result["endpoint_signal_gains"]), 2)

    def test_ascorbic_endpoint_prefers_chromatic_pad_over_carrier(self):
        img, boxes = self._fixture(slope=0.8)
        draw = ImageDraw.Draw(img)
        x0, y0, pitch = 180, 160, 72
        nominal = x0 + pitch*10
        cy = y0 + 0.8*(10-5)
        # Neutralize nominal location, put the real chromatic end pad 0.28 pitch right.
        draw.rectangle((nominal-17, cy-22, nominal+17, cy+22), fill=(220,220,216))
        actual = nominal + int(round(pitch*0.28))
        draw.rectangle((actual-15, cy-20, actual+15, cy+20), fill=(35,95,100))
        result = detect_strip_signal_regions(img, boxes)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["source"], "joint_strip_signal_v6_ascorbic_locked")
        self.assertGreaterEqual(result["ascorbic_endpoint_quality"]["chroma"], 35)
        self.assertFalse(result["ascorbic_endpoint_quality"]["carrier_like"])

    def test_blank_image_rejected(self):
        img = Image.new("RGB", (1200, 320), (220,220,220))
        boxes = {}
        for i, p in enumerate(ALLOWED_VALUES):
            cx = 180 + 72*i
            boxes[p] = [(cx-20)/1200, .35, (cx+20)/1200, .65]
        result = detect_strip_signal_regions(img, boxes)
        self.assertFalse(result["accepted"])


if __name__ == "__main__":
    unittest.main()
