import unittest
from PIL import Image, ImageDraw
from src.image_diagnostics import estimate_local_carrier_reference, normalize_rgb
from src.standards import ALLOWED_VALUES


class LocalCarrierNormalizationTests(unittest.TestCase):
    def _fixture(self, carrier=(210, 198, 185), background=(245, 235, 230)):
        w, h = 1200, 320
        img = Image.new('RGB', (w, h), background)
        draw = ImageDraw.Draw(img)
        x0, y, pitch = 180, 160, 72
        # strip carrier around the reagent row
        draw.rectangle((110, 125, 1030, 195), fill=carrier)
        colors = [(190,170,155),(80,145,180),(190,170,135),(180,160,150),(140,135,55),
                  (170,150,55),(175,130,50),(155,160,90),(195,185,170),(170,145,165),(35,95,100)]
        regions = {}
        for i, p in enumerate(ALLOWED_VALUES):
            cx = x0 + pitch*i
            draw.rectangle((cx-15, y-20, cx+15, y+20), fill=colors[i])
            regions[p] = [(cx-18)/w, (y-24)/h, (cx+18)/w, (y+24)/h]
        return img, regions

    def test_local_reference_prefers_strip_carrier_over_background(self):
        img, regions = self._fixture()
        norm = estimate_local_carrier_reference(img, regions)
        self.assertTrue(norm['accepted'], norm)
        self.assertEqual(norm['method'], 'strip_local_carrier_white_balance_v2')
        observed = norm['observed_neutral']
        self.assertLess(abs(observed[0] - 210), 8)
        self.assertLess(abs(observed[1] - 198), 8)
        self.assertLess(abs(observed[2] - 185), 8)

    def test_local_normalization_moves_carrier_toward_calibration_target(self):
        img, regions = self._fixture(carrier=(215, 190, 175))
        norm = estimate_local_carrier_reference(img, regions)
        corrected = normalize_rgb([215,190,175], norm)
        self.assertLess(abs(corrected[0]-194), 5)
        self.assertLess(abs(corrected[1]-194), 5)
        self.assertLess(abs(corrected[2]-190), 5)


if __name__ == '__main__':
    unittest.main()
