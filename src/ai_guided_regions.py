"""Pixel-refined fallback for CYBOW 11M pad localization.

AI boxes are treated only as semantic coarse proposals. Pixel search finds real pad
centers near those proposals, fits a smooth correction across the strip, then
returns tight sampling regions. Fail closed when evidence is insufficient.
"""
import math
from statistics import median
from PIL import ImageStat
from src.standards import ALLOWED_VALUES

PARAMETERS = list(ALLOWED_VALUES)


def _center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _valid_box(box):
    return (isinstance(box, list) and len(box) == 4 and
            all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in box) and
            box[2] > box[0] and box[3] > box[1])


def _median_rgb(image, cx, cy, half):
    x1 = max(0, int(round(cx - half)))
    y1 = max(0, int(round(cy - half)))
    x2 = min(image.width, int(round(cx + half + 1)))
    y2 = min(image.height, int(round(cy + half + 1)))
    if x2 - x1 < 3 or y2 - y1 < 3:
        return None, None, None
    roi = image.crop((x1, y1, x2, y2))
    rgb = ImageStat.Stat(roi).median
    hsv = ImageStat.Stat(roi.convert("HSV")).median
    return rgb, hsv[1], hsv[2]


def _candidate_score(image, cx, cy, half, expected):
    rgb, sat, val = _median_rgb(image, cx, cy, half)
    if rgb is None:
        return None
    # Compare pad center with a surrounding window. Reagent pads usually differ
    # from the pale plastic carrier even when the reagent itself is low-saturation.
    outer_half = half * 2.4
    outer_rgb, _, _ = _median_rgb(image, cx, cy, outer_half)
    contrast = math.dist(rgb, outer_rgb) if outer_rgb is not None else 0.0
    dist = math.hypot(cx - expected[0], cy - expected[1])
    # Distance penalty prevents the search from jumping into the neighboring pad.
    score = 0.62 * sat + 0.88 * contrast - 0.32 * dist
    if val < 35 or val > 248:
        score -= 35
    return {"center": (cx, cy), "score": score, "sat": float(sat),
            "contrast": float(contrast), "rgb": rgb, "value": float(val),
            "distance": dist}


def _fit_linear(points):
    """Fit correction = intercept + slope*index."""
    if len(points) < 2:
        return None
    xs = [float(i) for i, _ in points]
    ys = [float(v) for _, v in points]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - xm) ** 2 for x in xs)
    if denom <= 1e-9:
        return ym, 0.0
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
    return ym - slope * xm, slope


def detect_ai_guided_regions(image, ai_regions):
    if not isinstance(ai_regions, dict):
        return {"accepted": False, "reason": "AI pad proposals unavailable", "regions": {}}
    boxes = []
    for param in PARAMETERS:
        box = ai_regions.get(param)
        if not _valid_box(box):
            return {"accepted": False, "reason": "AI pad proposals incomplete", "regions": {}}
        boxes.append(box)

    centers = [(_center(b)[0] * image.width, _center(b)[1] * image.height) for b in boxes]
    pitches = [math.hypot(centers[i+1][0]-centers[i][0], centers[i+1][1]-centers[i][1])
               for i in range(len(centers)-1)]
    pitch = median([p for p in pitches if p > 2]) if pitches else 0.0
    if pitch < 10:
        return {"accepted": False, "reason": "AI pad spacing is implausible", "regions": {}}

    half = max(3.0, pitch * 0.15)
    radius = pitch * 0.38
    # Search a 9x7 grid near each semantic proposal. The radius is < half a pitch,
    # so a proposal cannot legitimately jump to the adjacent reagent pad.
    local = []
    for expected in centers:
        best = None
        for ox_i in range(-4, 5):
            for oy_i in range(-3, 4):
                cx = expected[0] + radius * ox_i / 4.0
                cy = expected[1] + radius * oy_i / 3.0
                if not (half < cx < image.width-half and half < cy < image.height-half):
                    continue
                cand = _candidate_score(image, cx, cy, half, expected)
                if cand is not None and (best is None or cand["score"] > best["score"]):
                    best = cand
        local.append(best)

    # Only strong visual candidates become anchors. Weak/negative pads are later
    # positioned by the smooth correction learned from strong pads.
    anchors = []
    for i, cand in enumerate(local):
        if cand and cand["score"] >= 24 and (cand["sat"] >= 28 or cand["contrast"] >= 18):
            dx = cand["center"][0] - centers[i][0]
            dy = cand["center"][1] - centers[i][1]
            if math.hypot(dx, dy) <= radius * 1.05:
                anchors.append((i, dx, dy, cand))

    if len(anchors) < 4 or (max(a[0] for a in anchors) - min(a[0] for a in anchors) < 5):
        return {"accepted": False, "reason": "insufficient pixel anchors near AI pad proposals",
                "regions": {}, "anchor_count": len(anchors), "pitch_pixels": round(pitch, 1)}

    fit_x = _fit_linear([(i, dx) for i, dx, _, _ in anchors])
    fit_y = _fit_linear([(i, dy) for i, _, dy, _ in anchors])
    if fit_x is None or fit_y is None:
        return {"accepted": False, "reason": "could not fit pixel-guided pad correction", "regions": {}}

    corrected = []
    for i, expected in enumerate(centers):
        dx = fit_x[0] + fit_x[1] * i
        dy = fit_y[0] + fit_y[1] * i
        if math.hypot(dx, dy) > radius * 1.15:
            return {"accepted": False, "reason": "pixel correction exceeds safe search radius", "regions": {}}
        corrected.append((expected[0] + dx, expected[1] + dy))

    # Validate smooth monotonic spacing after correction.
    cpitches = [math.hypot(corrected[i+1][0]-corrected[i][0], corrected[i+1][1]-corrected[i][1])
                for i in range(10)]
    pitch_ratio = median(cpitches) / pitch
    if not (0.82 <= pitch_ratio <= 1.18) or any(not (0.62*pitch <= p <= 1.38*pitch) for p in cpitches):
        return {"accepted": False, "reason": "pixel-refined pad spacing is inconsistent", "regions": {},
                "pitch_ratio": round(pitch_ratio, 3)}

    # Anchor residual measures whether one smooth strip correction explains the
    # detected colored pads. Large residual means unrelated objects were selected.
    residuals = []
    for i, dx, dy, cand in anchors:
        pred_dx = fit_x[0] + fit_x[1] * i
        pred_dy = fit_y[0] + fit_y[1] * i
        residuals.append(math.hypot(dx-pred_dx, dy-pred_dy))
    med_residual = median(residuals)
    if med_residual > pitch * 0.18:
        return {"accepted": False, "reason": "pixel anchors do not form one consistent strip",
                "regions": {}, "anchor_count": len(anchors),
                "anchor_residual_pixels": round(med_residual, 1)}

    sample_half_x = max(3.0, pitch * 0.16)
    # Use actual proposal height as a weak prior, but keep region well inside a pad.
    median_ai_h = median((b[3]-b[1]) * image.height for b in boxes)
    sample_half_y = max(3.0, min(pitch * 0.18, median_ai_h * 0.22))
    regions = {}
    for param, (cx, cy) in zip(PARAMETERS, corrected):
        regions[param] = [max(0.0, (cx-sample_half_x)/image.width),
                          max(0.0, (cy-sample_half_y)/image.height),
                          min(1.0, (cx+sample_half_x)/image.width),
                          min(1.0, (cy+sample_half_y)/image.height)]

    return {"accepted": True, "reason": None, "regions": regions,
            "source": "ai_semantic_pixel_refined_v1", "anchor_count": len(anchors),
            "pitch_pixels": round(pitch, 1), "pitch_ratio": round(pitch_ratio, 3),
            "anchor_residual_pixels": round(med_residual, 1),
            "correction_start_pixels": [round(fit_x[0], 1), round(fit_y[0], 1)],
            "correction_slope_pixels_per_pad": [round(fit_x[1], 2), round(fit_y[1], 2)],
            "anchor_indices": [a[0] for a in anchors]}
