"""Image diagnostics computed from pixels; pad locations remain model proposals."""
import io
import math
from PIL import Image, ImageOps, ImageStat, ImageFilter
from src.standards import ALLOWED_VALUES, CYBOW_11M_STANDARDS, UNVERIFIED_COLOR_PARAMETERS
from src.cybow_reference import calculate_confidence_from_rgb

CALIBRATION_NEUTRAL_RGB = (194.0, 194.0, 190.0)

def estimate_neutral_reference(image):
    hsv = image.convert("HSV")
    rgb_pixels = list(image.getdata())
    hsv_pixels = list(hsv.getdata())
    candidates = [rgb for rgb, h in zip(rgb_pixels, hsv_pixels)
                  if h[1] <= 28 and 120 <= h[2] <= 245]
    if len(candidates) < max(50, image.width * image.height // 500):
        return {"accepted": False, "reason": "insufficient neutral pixels",
                "observed_neutral": None, "gains": [1.0, 1.0, 1.0],
                "target_neutral": list(CALIBRATION_NEUTRAL_RGB)}
    candidates.sort(key=lambda px: sum(px), reverse=True)
    top = candidates[:max(50, len(candidates)//5)]
    observed = [float(x) for x in ImageStat.Stat(Image.new("RGB", (len(top), 1))).median] if False else None
    channels = list(zip(*top))
    observed = [float(sorted(ch)[len(ch)//2]) for ch in channels]
    gains = [max(0.70, min(1.40, target / max(obs, 1.0)))
             for target, obs in zip(CALIBRATION_NEUTRAL_RGB, observed)]
    accepted = all(0.70 < g < 1.40 for g in gains)
    return {"accepted": accepted,
            "reason": None if accepted else "white-balance correction exceeds safe limits",
            "observed_neutral": [round(x, 1) for x in observed],
            "gains": [round(x, 4) for x in gains],
            "target_neutral": list(CALIBRATION_NEUTRAL_RGB),
            "method": "bright_low_saturation_white_balance_v1"}

def normalize_rgb(rgb, normalization):
    gains = normalization.get("gains", [1.0, 1.0, 1.0])
    return [round(max(0, min(255, value * gain)), 1) for value, gain in zip(rgb, gains)]

def prepare_image(image_bytes, max_dimension=1536):
    with Image.open(io.BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((max_dimension, max_dimension))
        return image.copy()

def image_quality(image):
    gray = image.convert("L")
    stats = ImageStat.Stat(gray)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    inner = edges.crop((1, 1, edges.width-1, edges.height-1)) if min(edges.size) > 2 else edges
    sharpness = ImageStat.Stat(inner).mean[0]
    mean = stats.mean[0]
    reasons = []
    if min(image.size) < 128:
        reasons.append("ภาพมีความละเอียดต่ำเกินไป")
    if mean < 25 or mean > 245:
        reasons.append("ภาพมืดหรือสว่างเกินไป")
    if stats.stddev[0] < 3 or sharpness < 1:
        reasons.append("ภาพไม่มีรายละเอียดเพียงพอ")
    return {"accepted": not reasons, "reasons": reasons, "brightness": round(mean, 2),
            "sharpness": round(sharpness, 2), "method": "heuristic_v1"}

def _shrink_box(box, factor=0.55):
    x1, y1, x2, y2 = box
    cx, cy = (x1+x2)/2, (y1+y2)/2
    hw, hh = (x2-x1)*factor/2, (y2-y1)*factor/2
    return [cx-hw, cy-hh, cx+hw, cy+hh]

def _pixel_crosscheck(results, rgb):
    checks, mismatches = {}, []
    for param, detected in rgb.items():
        if param in UNVERIFIED_COLOR_PARAMETERS:
            continue
        refs = CYBOW_11M_STANDARDS.get(param, [])
        selected = results.get(param)
        if not refs or selected is None:
            continue
        ranked = sorted((math.dist(detected, ref["rgb"]), ref["value"]) for ref in refs)
        nearest_distance, nearest_value = ranked[0]
        selected_ref = next((ref for ref in refs if ref["value"] == selected), None)
        if selected_ref is None:
            continue
        selected_distance = math.dist(detected, selected_ref["rgb"])
        strong_mismatch = (nearest_value != selected and selected_distance - nearest_distance >= 35)
        too_far = selected_distance > 150
        if strong_mismatch or too_far:
            mismatches.append(param)
        checks[param] = {
            "selected": selected, "nearest": nearest_value,
            "selected_distance": round(selected_distance, 1),
            "nearest_distance": round(nearest_distance, 1),
            "strong_mismatch": strong_mismatch, "too_far": too_far
        }
    return {"checks": checks, "mismatches": mismatches, "accepted": not mismatches}

def sample_regions(image, regions, results):
    regions = regions if isinstance(regions, dict) else {}
    normalization = estimate_neutral_reference(image)
    rgb, normalized_rgb, boxes, sampled_boxes, scores, saturation = {}, {}, {}, {}, {}, {}
    for param in ALLOWED_VALUES:
        box = regions.get(param)
        if not isinstance(box, list) or len(box) != 4 or not all(
                type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in box):
            continue
        x1, y1, x2, y2 = box
        if x2 <= x1 or y2 <= y1:
            continue
        if any(min(x2, b[2]) > max(x1, b[0]) and min(y2, b[3]) > max(y1, b[1]) for b in boxes.values()):
            continue
        inner = _shrink_box(box)
        ix1, iy1, ix2, iy2 = inner
        bounds = (round(ix1*image.width), round(iy1*image.height), round(ix2*image.width), round(iy2*image.height))
        if bounds[2]-bounds[0] < 3 or bounds[3]-bounds[1] < 3:
            continue
        roi = image.crop(bounds)
        rgb[param] = ImageStat.Stat(roi).median
        normalized_rgb[param] = normalize_rgb(rgb[param], normalization)
        hsv = roi.convert("HSV")
        saturation[param] = round(ImageStat.Stat(hsv).median[1], 1)
        boxes[param] = box
        sampled_boxes[param] = inner
        scores[param] = calculate_confidence_from_rgb(normalized_rgb[param], param, results.get(param))

    spread = 0.0
    if len(rgb) >= 2:
        vals = list(rgb.values())
        spread = max(math.dist(a, b) for i, a in enumerate(vals) for b in vals[i+1:])
    roi_consistency = {
        "accepted": len(rgb) < 11 or spread >= 28,
        "max_pairwise_rgb_distance": round(spread, 1),
        "reason": None if (len(rgb) < 11 or spread >= 28) else "pad regions have implausibly low color variation"
    }
    crosscheck = _pixel_crosscheck(results, normalized_rgb)
    return {
        "detected_rgb": rgb, "normalized_rgb": normalized_rgb, "normalization": normalization,
        "pad_regions": boxes, "sampled_regions": sampled_boxes,
        "median_saturation": saturation, "color_similarity_scores": scores,
        "roi_consistency": roi_consistency, "pixel_crosscheck": crosscheck,
        "rgb_source": "pixel_median_center_shrunk_model_roi",
        "normalized_rgb_source": "white_balance_to_ref0974_neutral", "reference_calibrated": True
    }
