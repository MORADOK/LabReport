"""Joint strip-signal localizer for CYBOW 11M.

AI proposals are optional semantic priors, never direct sampling ROIs. The localizer
fits one coherent 11-pad model, then applies bounded local refinement. Missing AI
boxes are tolerated when enough indexed semantic anchors remain.
"""
import math
from statistics import median
from PIL import ImageStat
from src.standards import ALLOWED_VALUES

PARAMETERS = list(ALLOWED_VALUES)


def _valid_box(box):
    return (isinstance(box, list) and len(box) == 4 and
            all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in box) and
            box[2] > box[0] and box[3] > box[1])


def _center(box):
    return ((box[0] + box[2]) * 0.5, (box[1] + box[3]) * 0.5)


def _fit_indexed_line(indexed_points):
    if len(indexed_points) < 2:
        return None
    xs = [float(i) for i, _ in indexed_points]
    xm = sum(xs) / len(xs)
    denom = sum((x-xm)**2 for x in xs)
    if denom <= 1e-9:
        return None
    out = []
    for dim in (0, 1):
        ys = [p[dim] for _, p in indexed_points]
        ym = sum(ys) / len(ys)
        slope = sum((x-xm)*(y-ym) for x, y in zip(xs, ys)) / denom
        intercept = ym - slope*xm
        out.append((intercept, slope))
    return out[0][0], out[1][0], out[0][1], out[1][1]


def _median_rgb(image, cx, cy, half_x, half_y):
    x1 = max(0, int(round(cx-half_x)))
    x2 = min(image.width, int(round(cx+half_x+1)))
    y1 = max(0, int(round(cy-half_y)))
    y2 = min(image.height, int(round(cy+half_y+1)))
    if x2-x1 < 3 or y2-y1 < 3:
        return None
    roi = image.crop((x1, y1, x2, y2))
    rgb = ImageStat.Stat(roi).median
    hsv = ImageStat.Stat(roi.convert("HSV")).median
    return (float(rgb[0]), float(rgb[1]), float(rgb[2])), float(hsv[1]), float(hsv[2])


def _point(base, u, v, along, perp):
    return (base[0] + u[0]*along + v[0]*perp,
            base[1] + u[1]*along + v[1]*perp)


def _pad_signal(image, center, u, v, pitch, half_along, half_perp):
    inner = _median_rgb(image, center[0], center[1], half_along, half_perp)
    if inner is None:
        return None
    rgb, sat, val = inner
    gap_rgbs = []
    for along in (-0.46*pitch, 0.46*pitch):
        p = _point(center, u, v, along, 0.0)
        sample = _median_rgb(image, p[0], p[1], max(2.0, half_along*0.55), max(2.0, half_perp*0.72))
        if sample is not None:
            gap_rgbs.append(sample[0])
    if gap_rgbs:
        gap = tuple(median([g[k] for g in gap_rgbs]) for k in range(3))
        contrast = math.dist(rgb, gap)
    else:
        contrast = 0.0
    chroma = max(rgb) - min(rgb)
    score = 0.42*sat + 0.72*contrast + 0.20*chroma
    if val < 28 or val > 250:
        score -= 28.0
    return {"score": score, "sat": sat, "contrast": contrast,
            "chroma": chroma, "value": val, "rgb": rgb}


def _smooth_local_offsets(offsets, pitch):
    if not offsets:
        return [], 0
    cleaned = list(offsets)
    reverted = 0
    for i, (a, p) in enumerate(offsets):
        neigh = offsets[max(0, i-1):min(len(offsets), i+2)]
        ma = median([x[0] for x in neigh])
        mp = median([x[1] for x in neigh])
        if abs(a-ma) > pitch*0.14 or abs(p-mp) > pitch*0.14:
            cleaned[i] = (0.0, 0.0)
            reverted += 1
    for i in range(1, len(cleaned)):
        if (abs(cleaned[i][0]-cleaned[i-1][0]) > pitch*0.18 or
                abs(cleaned[i][1]-cleaned[i-1][1]) > pitch*0.18):
            if abs(cleaned[i][0]) + abs(cleaned[i][1]) >= abs(cleaned[i-1][0]) + abs(cleaned[i-1][1]):
                cleaned[i] = (0.0, 0.0)
            else:
                cleaned[i-1] = (0.0, 0.0)
            reverted += 1
    return cleaned, reverted


def _refine_endpoint(image, center, u, v, pitch, half_along, half_perp, baseline_offset):
    """Wider but still bounded refinement for first/last reagent pads.

    End pads are the most affected by perspective/fit extrapolation. Search up to
    0.24 pitch, far below one full pad spacing, and only keep the candidate when it
    materially improves the visual signal. This cannot jump to a neighbouring pad.
    """
    base = _point(center, u, v, baseline_offset[0], baseline_offset[1])
    base_sig = _pad_signal(image, base, u, v, pitch, half_along, half_perp)
    base_score = base_sig["score"] if base_sig else -999.0
    best = (base_score, baseline_offset[0], baseline_offset[1])
    for along_i in range(-4, 5):
        along = pitch*0.06*along_i
        for perp_i in range(-3, 4):
            perp = pitch*0.06*perp_i
            if abs(along) > pitch*0.24 or abs(perp) > pitch*0.18:
                continue
            c = _point(center, u, v, along, perp)
            if not (half_along+2 < c[0] < image.width-half_along-2 and
                    half_perp+2 < c[1] < image.height-half_perp-2):
                continue
            sig = _pad_signal(image, c, u, v, pitch, half_along, half_perp)
            if sig is None:
                continue
            objective = sig["score"] - 0.20*abs(along) - 0.16*abs(perp)
            if objective > best[0]:
                best = (objective, along, perp)
    # Require a meaningful gain so a neutral background patch cannot pull an end pad.
    if best[0] >= base_score + 6.0:
        return (best[1], best[2]), round(best[0]-base_score, 1)
    return baseline_offset, 0.0


def detect_strip_signal_regions(image, ai_regions):
    if not isinstance(ai_regions, dict):
        return {"accepted": False, "reason": "AI semantic proposals unavailable", "regions": {}}

    indexed = []
    heights = []
    for i, param in enumerate(PARAMETERS):
        box = ai_regions.get(param)
        if not _valid_box(box):
            continue
        cx, cy = _center(box)
        indexed.append((i, (cx*image.width, cy*image.height)))
        heights.append((box[3]-box[1])*image.height)
    if len(indexed) < 5:
        return {"accepted": False, "reason": "too few semantic anchors for strip fit", "regions": {},
                "semantic_anchor_count": len(indexed)}
    if indexed[-1][0] - indexed[0][0] < 6:
        return {"accepted": False, "reason": "semantic anchors do not span enough reagent positions", "regions": {},
                "semantic_anchor_count": len(indexed)}

    fit = _fit_indexed_line(indexed)
    if fit is None:
        return {"accepted": False, "reason": "could not fit semantic strip axis", "regions": {}}
    x0, y0, dx, dy = fit
    pitch = math.hypot(dx, dy)
    if pitch < 10 or pitch > max(image.size)*0.18:
        return {"accepted": False, "reason": "semantic strip pitch is implausible", "regions": {},
                "pitch_pixels": round(pitch, 1)}

    u = (dx/pitch, dy/pitch)
    v = (-u[1], u[0])
    median_ai_h = median(heights)
    half_along = max(3.0, pitch*0.145)
    half_perp = max(3.0, min(pitch*0.19, median_ai_h*0.22))

    candidates = []
    for phase_i in range(-4, 5):
        phase = pitch*0.03*phase_i
        for perp_i in range(-5, 6):
            perp0 = pitch*0.04*perp_i
            for tilt_i in range(-3, 4):
                perp_step = pitch*0.006*tilt_i
                centers, signals = [], []
                valid = True
                for i in range(11):
                    base = (x0+dx*i, y0+dy*i)
                    c = _point(base, u, v, phase, perp0 + perp_step*(i-5))
                    if not (half_along+2 < c[0] < image.width-half_along-2 and
                            half_perp+2 < c[1] < image.height-half_perp-2):
                        valid = False
                        break
                    sig = _pad_signal(image, c, u, v, pitch, half_along, half_perp)
                    if sig is None:
                        valid = False
                        break
                    centers.append(c)
                    signals.append(sig)
                if not valid:
                    continue
                scores = sorted((s["score"] for s in signals), reverse=True)
                strong = sum(1 for s in signals if s["sat"] >= 25 or s["contrast"] >= 15 or s["chroma"] >= 20)
                visual = sum(scores[:7]) / 7.0
                prior_penalty = 0.22*abs(phase) + 0.10*abs(perp0) + 0.16*abs(perp_step)*5
                gap_like = median([s["contrast"] for s in signals])
                objective = visual + strong*1.5 + 0.10*gap_like - prior_penalty
                candidates.append({"objective": objective, "visual": visual, "strong": strong,
                                   "phase": phase, "perp0": perp0, "perp_step": perp_step,
                                   "centers": centers, "signals": signals})

    if not candidates:
        return {"accepted": False, "reason": "joint strip search produced no valid model", "regions": {}}
    candidates.sort(key=lambda c: c["objective"], reverse=True)
    best = candidates[0]
    competitor = None
    for cand in candidates[1:]:
        if (abs(cand["phase"]-best["phase"]) > pitch*0.12 or
                abs(cand["perp0"]-best["perp0"]) > pitch*0.12 or
                abs(cand["perp_step"]-best["perp_step"]) > pitch*0.018):
            competitor = cand
            break
    margin = best["objective"] - competitor["objective"] if competitor else 999.0
    median_contrast = median([s["contrast"] for s in best["signals"]])
    median_sat = median([s["sat"] for s in best["signals"]])

    if best["strong"] < 5:
        return {"accepted": False, "reason": "too few reagent pads have measurable pixel signal",
                "regions": {}, "strong_pad_count": best["strong"], "pitch_pixels": round(pitch, 1)}
    if best["visual"] < 20.0:
        return {"accepted": False, "reason": "joint strip visual signal is too weak", "regions": {},
                "visual_score": round(best["visual"], 1), "pitch_pixels": round(pitch, 1)}
    ai_close = abs(best["phase"]) <= pitch*0.10 and abs(best["perp0"]) <= pitch*0.18
    if margin < 2.0 and not ai_close:
        return {"accepted": False, "reason": "joint strip position is ambiguous", "regions": {},
                "model_margin": round(margin, 2), "pitch_pixels": round(pitch, 1)}
    if abs(best["perp_step"]*10) > pitch*0.22:
        return {"accepted": False, "reason": "strip slope correction is excessive", "regions": {}}

    raw_offsets = []
    for center in best["centers"]:
        local_best = None
        for along_i in range(-3, 4):
            along = pitch*0.06*along_i
            for perp_i in range(-2, 3):
                perp = pitch*0.06*perp_i
                c = _point(center, u, v, along, perp)
                if not (half_along+2 < c[0] < image.width-half_along-2 and
                        half_perp+2 < c[1] < image.height-half_perp-2):
                    continue
                sig = _pad_signal(image, c, u, v, pitch, half_along, half_perp)
                if sig is None:
                    continue
                objective = sig["score"] - 0.24*abs(along) - 0.18*abs(perp)
                if local_best is None or objective > local_best[0]:
                    local_best = (objective, along, perp)
        raw_offsets.append((0.0, 0.0) if local_best is None else (local_best[1], local_best[2]))

    offsets, reverted = _smooth_local_offsets(raw_offsets, pitch)
    endpoint_gains = [0.0, 0.0]
    # End pads can be slightly misregistered by a line fit that is excellent in the middle.
    for slot, gain_idx in ((0, 0), (10, 1)):
        offsets[slot], endpoint_gains[gain_idx] = _refine_endpoint(
            image, best["centers"][slot], u, v, pitch, half_along, half_perp, offsets[slot])

    refined_centers = [_point(c, u, v, a, p) for c, (a, p) in zip(best["centers"], offsets)]
    max_along_jump = max((abs(b[0]-a[0]) for a,b in zip(offsets, offsets[1:])), default=0.0)
    max_perp_jump = max((abs(b[1]-a[1]) for a,b in zip(offsets, offsets[1:])), default=0.0)

    regions = {}
    for param, (cx, cy) in zip(PARAMETERS, refined_centers):
        regions[param] = [max(0.0, (cx-half_along)/image.width),
                          max(0.0, (cy-half_perp)/image.height),
                          min(1.0, (cx+half_along)/image.width),
                          min(1.0, (cy+half_perp)/image.height)]

    return {"accepted": True, "reason": None, "regions": regions,
            "source": "joint_strip_signal_v5_endpoint_refined", "pitch_pixels": round(pitch, 1),
            "semantic_anchor_count": len(indexed), "semantic_span_slots": indexed[-1][0]-indexed[0][0],
            "strong_pad_count": best["strong"], "visual_score": round(best["visual"], 1),
            "model_margin": round(margin, 2), "median_pad_contrast": round(median_contrast, 1),
            "median_pad_saturation": round(median_sat, 1),
            "phase_pixels": round(best["phase"], 1),
            "perpendicular_offset_pixels": round(best["perp0"], 1),
            "perpendicular_step_pixels_per_pad": round(best["perp_step"], 2),
            "semantic_axis_step_pixels": [round(dx, 2), round(dy, 2)],
            "local_offsets_pixels": [[round(a,1), round(b,1)] for a,b in offsets],
            "local_refinement_reverted_count": reverted,
            "endpoint_signal_gains": endpoint_gains,
            "max_local_along_jump_pixels": round(max_along_jump,1),
            "max_local_perp_jump_pixels": round(max_perp_jump,1)}
