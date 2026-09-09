"""Image diagnostics computed from pixels; pad locations remain model proposals."""
import io
import math
from PIL import Image, ImageOps, ImageStat, ImageFilter
from statistics import median
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



def estimate_local_carrier_reference(image, regions):
    """Estimate white balance from carrier gaps immediately beside reagent pads.

    Lateral gap samples remain on the physical strip and are much less likely than
    above/below bands to include tablecloth/background pixels.
    """
    if not isinstance(regions, dict):
        return estimate_neutral_reference(image)
    samples=[]
    for box in regions.values():
        if not (isinstance(box,list) and len(box)==4):
            continue
        x1,y1,x2,y2=box
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in box):
            continue
        px1,px2=x1*image.width,x2*image.width
        py1,py2=y1*image.height,y2*image.height
        w=max(3.0,px2-px1); h=max(3.0,py2-py1)
        # sample narrow lateral gaps close to the pad edge; stay vertically within carrier
        bands=[
            (px1-0.42*w, py1+0.18*h, px1-0.10*w, py2-0.18*h),
            (px2+0.10*w, py1+0.18*h, px2+0.42*w, py2-0.18*h),
        ]
        for bx1,by1,bx2,by2 in bands:
            bx1=max(0,int(round(bx1))); by1=max(0,int(round(by1)))
            bx2=min(image.width,int(round(bx2))); by2=min(image.height,int(round(by2)))
            if bx2-bx1 < 3 or by2-by1 < 3: continue
            roi=image.crop((bx1,by1,bx2,by2)); hsv=roi.convert('HSV')
            for rgb_px,hsv_px in zip(roi.getdata(),hsv.getdata()):
                if hsv_px[1] <= 72 and 70 <= hsv_px[2] <= 245:
                    samples.append(rgb_px)
    min_needed=max(60,len(regions)*8)
    if len(samples) < min_needed:
        fallback=estimate_neutral_reference(image)
        fallback['fallback_from']='strip_local_carrier_white_balance_v2'
        return fallback
    channels=list(zip(*samples))
    observed=[float(sorted(ch)[len(ch)//2]) for ch in channels]
    gains=[max(0.72,min(1.32,target/max(obs,1.0))) for target,obs in zip(CALIBRATION_NEUTRAL_RGB,observed)]
    accepted=all(0.72 < g < 1.32 for g in gains)
    return {
        'accepted':accepted,
        'reason':None if accepted else 'local carrier white-balance correction exceeds safe limits',
        'observed_neutral':[round(x,1) for x in observed],
        'gains':[round(x,4) for x in gains],
        'target_neutral':list(CALIBRATION_NEUTRAL_RGB),
        'sample_count':len(samples),
        'method':'strip_local_carrier_white_balance_v2'
    }


def _roi_quality(image, box, inner, rgb):
    """Measure whether a sampling ROI visually behaves like a reagent pad."""
    x1,y1,x2,y2=box
    ix1,iy1,ix2,iy2=inner
    cx=(ix1+ix2)*0.5*image.width; cy=(iy1+iy2)*0.5*image.height
    iw=max(3.0,(ix2-ix1)*image.width); ih=max(3.0,(iy2-iy1)*image.height)
    def med_at(px,py,w,h):
        b=(max(0,int(px-w/2)),max(0,int(py-h/2)),min(image.width,int(px+w/2)),min(image.height,int(py+h/2)))
        if b[2]-b[0] < 3 or b[3]-b[1] < 3: return None
        r=image.crop(b)
        return ImageStat.Stat(r).median
    around=[]
    for dx,dy in ((0,-0.9*ih),(0,0.9*ih),(-0.8*iw,0),(0.8*iw,0)):
        m=med_at(cx+dx,cy+dy,max(3,iw*0.45),max(3,ih*0.45))
        if m is not None: around.append(m)
    contrast=median([math.dist(rgb,a) for a in around]) if around else 0.0
    appearance=_pixel_appearance(rgb)
    carrier_like=(contrast < 12 and appearance['chroma'] < 18 and appearance['saturation_proxy'] < 28)
    return {
        'contrast_to_surround':round(contrast,1),
        'chroma':round(appearance['chroma'],1),
        'saturation_proxy':round(appearance['saturation_proxy'],1),
        'carrier_like':carrier_like
    }

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


def _pixel_appearance(rgb):
    vals = [float(v) for v in rgb]
    chroma = max(vals) - min(vals)
    mean = sum(vals) / 3.0
    saturation_proxy = chroma / max(max(vals), 1.0) * 255.0
    return {"chroma": chroma, "mean": mean, "saturation_proxy": saturation_proxy}


def _srgb_to_linear(v):
    c = max(0.0, min(255.0, float(v))) / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    r, g, b = [_srgb_to_linear(v) for v in rgb]
    x = (0.4124564*r + 0.3575761*g + 0.1804375*b) / 0.95047
    y = (0.2126729*r + 0.7151522*g + 0.0721750*b)
    z = (0.0193339*r + 0.1191920*g + 0.9503041*b) / 1.08883
    d = 6/29
    def f(t):
        return t ** (1/3) if t > d**3 else t/(3*d*d) + 4/29
    fx, fy, fz = f(x), f(y), f(z)
    return (116*fy-16, 500*(fx-fy), 200*(fy-fz))


def delta_e76(rgb1, rgb2):
    return math.dist(rgb_to_lab(rgb1), rgb_to_lab(rgb2))


def _is_positive_value(value):
    if value is None:
        return False
    text = str(value).strip().lower()
    normal_tokens = {"neg.", "neg", "negative", "0.1 normal", "1.000", "5", "6", "6.5", "7", "8", "9"}
    return text not in normal_tokens


def reconcile_results(results, rgb):
    """Fuse pixel evidence with AI labels using confident/borderline/review states.

    Borderline means the measured color is genuinely close to a calibrated
    reference but the neighboring class is also close. Borderline values may be
    carried forward only with an explicit warning; distant or background-like
    colors remain review and fail closed.
    """
    resolved = dict(results)
    decisions = {}
    review = []
    borderline = []
    for param in ALLOWED_VALUES:
        if param in UNVERIFIED_COLOR_PARAMETERS:
            decisions[param] = {"source": "ai_pattern_unverified", "value": results.get(param),
                                "confidence_level": "pattern_unverified"}
            continue
        detected = rgb.get(param)
        refs = CYBOW_11M_STANDARDS.get(param, [])
        if detected is None or not refs:
            review.append(param)
            decisions[param] = {"source": "unresolved", "reason": "missing pixel/reference data",
                                "confidence_level": "review"}
            continue

        ranked = sorted((math.dist(detected, ref["rgb"]), delta_e76(detected, ref["rgb"]), ref["value"])
                        for ref in refs)
        nearest_distance, nearest_de, nearest = ranked[0]
        second_distance = ranked[1][0] if len(ranked) > 1 else float("inf")
        second_de = ranked[1][1] if len(ranked) > 1 else float("inf")
        margin = second_distance - nearest_distance
        de_margin = second_de - nearest_de
        ai_value = results.get(param)
        appearance = _pixel_appearance(detected)
        low_signal = appearance["chroma"] < 18 and appearance["saturation_proxy"] < 28
        nearest_positive = _is_positive_value(nearest)

        common = {"nearest_distance": round(nearest_distance,1), "margin": round(margin,1),
                  "delta_e76": round(nearest_de,2), "delta_e_margin": round(de_margin,2),
                  "chroma": round(appearance["chroma"],1)}

        # Confident: close in both RGB and perceptual Lab space, with clear separation.
        if nearest_distance <= 58 and nearest_de <= 18 and margin >= 14 and de_margin >= 2.5:
            if nearest_positive and low_signal:
                review.append(param)
                decisions[param] = {"source": "review_background_like_roi", "ai_value": ai_value,
                                    "pixel_nearest": nearest, "confidence_level": "review", **common}
                continue
            resolved[param] = nearest
            source = "pixel_primary" if nearest != ai_value else "pixel_ai_agree"
            decisions[param] = {"source": source, "value": nearest, "ai_value": ai_value,
                                "confidence_level": "confident", **common}
            continue

        # Borderline: absolute color match is very good, but adjacent reference
        # levels are close. This is common for SG/pH/protein transitions.
        if nearest_distance <= 40 and nearest_de <= 13 and margin >= 5:
            if nearest_positive and low_signal:
                review.append(param)
                decisions[param] = {"source": "review_background_like_roi", "ai_value": ai_value,
                                    "pixel_nearest": nearest, "confidence_level": "review", **common}
                continue
            resolved[param] = nearest
            borderline.append(param)
            decisions[param] = {"source": "pixel_borderline", "value": nearest, "ai_value": ai_value,
                                "confidence_level": "borderline", **common}
            continue

        # Moderate agreement: AI and pixel choose the same class and both color
        # metrics are within a reasonable envelope.
        if nearest_distance <= 72 and nearest_de <= 22 and ai_value == nearest and margin >= 6:
            if nearest_positive and low_signal:
                review.append(param)
                decisions[param] = {"source": "review_background_like_roi", "ai_value": ai_value,
                                    "pixel_nearest": nearest, "confidence_level": "review", **common}
                continue
            resolved[param] = ai_value
            decisions[param] = {"source": "ai_pixel_agree_moderate", "value": ai_value,
                                "confidence_level": "moderate", **common}
            continue

        selected_ref = next((ref for ref in refs if ref["value"] == ai_value), None)
        if selected_ref is not None:
            selected_distance = math.dist(detected, selected_ref["rgb"])
            selected_de = delta_e76(detected, selected_ref["rgb"])
            if (selected_distance <= 65 and selected_de <= 20 and nearest_distance <= 65 and
                    selected_distance - nearest_distance <= 9):
                if _is_positive_value(ai_value) and low_signal:
                    review.append(param)
                    decisions[param] = {"source": "review_background_like_roi", "ai_value": ai_value,
                                        "pixel_nearest": nearest, "confidence_level": "review", **common}
                    continue
                resolved[param] = ai_value
                borderline.append(param)
                decisions[param] = {"source": "ai_tiebreak_borderline", "value": ai_value,
                                    "pixel_nearest": nearest, "selected_distance": round(selected_distance,1),
                                    "selected_delta_e76": round(selected_de,2),
                                    "confidence_level": "borderline", **common}
                continue

        review.append(param)
        decisions[param] = {"source": "review", "ai_value": ai_value, "pixel_nearest": nearest,
                            "confidence_level": "review", "saturation_proxy": round(appearance["saturation_proxy"],1),
                            **common}
    return {"resolved_results": resolved, "decisions": decisions,
            "review": review, "borderline": borderline,
            "accepted": not review,
            "overall_status": "review" if review else ("borderline" if borderline else "confident")}

def sample_regions(image, regions, results):
    regions = regions if isinstance(regions, dict) else {}
    normalization = estimate_local_carrier_reference(image, regions)
    rgb, normalized_rgb, boxes, sampled_boxes, scores, saturation, roi_quality = {}, {}, {}, {}, {}, {}, {}
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
        roi_quality[param] = _roi_quality(image, box, inner, rgb[param])
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
    fusion = reconcile_results(results, normalized_rgb)
    # Reclassify obvious carrier/background samples as localization failures for
    # parameters whose entire reference scale is chromatic. This keeps geometry
    # problems separate from genuine color ambiguity.
    localization_review = []
    for param, quality in roi_quality.items():
        refs = CYBOW_11M_STANDARDS.get(param, [])
        if not refs or not quality.get("carrier_like"):
            continue
        min_ref_chroma = min((max(ref["rgb"])-min(ref["rgb"]) for ref in refs), default=0)
        if min_ref_chroma >= 22 and param not in UNVERIFIED_COLOR_PARAMETERS:
            localization_review.append(param)
            if param not in fusion["review"]:
                fusion["review"].append(param)
            if param in fusion.get("borderline", []):
                fusion["borderline"].remove(param)
            fusion["decisions"][param] = {
                "source": "localization_review_carrier_like_roi",
                "confidence_level": "review",
                "reason": "ROI resembles strip carrier/background instead of reagent pad",
                **quality
            }
    if localization_review:
        fusion["accepted"] = False
        fusion["overall_status"] = "review"
        fusion["localization_review"] = localization_review
    return {
        "detected_rgb": rgb, "normalized_rgb": normalized_rgb, "normalization": normalization,
        "pad_regions": boxes, "sampled_regions": sampled_boxes,
        "median_saturation": saturation, "color_similarity_scores": scores,
        "roi_quality": roi_quality,
        "roi_consistency": roi_consistency, "pixel_crosscheck": crosscheck,
        "result_fusion": fusion,
        "rgb_source": "pixel_median_center_shrunk_model_roi",
        "normalized_rgb_source": normalization.get("method", "unknown"), "reference_calibrated": True
    }
