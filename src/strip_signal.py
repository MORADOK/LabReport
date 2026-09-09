"""Joint 1-D strip-signal localizer for CYBOW 11M.

This fallback treats AI boxes only as a coarse semantic/order prior. Instead of
moving eleven pads independently, it optimizes one global strip model (phase,
perpendicular offset and small slope correction) and evaluates color/contrast
signals for all reagent pads together. This avoids mutually inconsistent local
anchors on textured backgrounds.
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


def _fit_index_line(points):
    """Fit point(index) = intercept + step * index independently for x/y."""
    n = len(points)
    if n < 2:
        return None
    xs = list(range(n))
    xm = sum(xs) / n
    denom = sum((x - xm) ** 2 for x in xs)
    if denom <= 1e-9:
        return None
    out = []
    for dim in (0, 1):
        ys = [p[dim] for p in points]
        ym = sum(ys) / n
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
    # Axis-aligned crop is intentionally conservative; candidate model only permits
    # small angles. We compare pad center to carrier/gap samples on both sides.
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

    # Chroma works better than saturation alone for dark/strong reagent pads.
    chroma = max(rgb) - min(rgb)
    score = 0.42*sat + 0.72*contrast + 0.20*chroma
    if val < 28 or val > 250:
        score -= 28.0
    return {"score": score, "sat": sat, "contrast": contrast,
            "chroma": chroma, "value": val, "rgb": rgb}


def detect_strip_signal_regions(image, ai_regions):
    if not isinstance(ai_regions, dict):
        return {"accepted": False, "reason": "AI semantic proposals unavailable", "regions": {}}
    boxes = []
    for param in PARAMETERS:
        box = ai_regions.get(param)
        if not _valid_box(box):
            return {"accepted": False, "reason": "AI semantic proposals incomplete", "regions": {}}
        boxes.append(box)

    ai_centers = [(_center(b)[0]*image.width, _center(b)[1]*image.height) for b in boxes]
    fit = _fit_index_line(ai_centers)
    if fit is None:
        return {"accepted": False, "reason": "could not fit semantic strip axis", "regions": {}}
    x0, y0, dx, dy = fit
    pitch = math.hypot(dx, dy)
    if pitch < 10 or pitch > max(image.size)*0.18:
        return {"accepted": False, "reason": "semantic strip pitch is implausible", "regions": {},
                "pitch_pixels": round(pitch, 1)}

    u = (dx/pitch, dy/pitch)
    v = (-u[1], u[0])
    median_ai_h = median((b[3]-b[1])*image.height for b in boxes)
    half_along = max(3.0, pitch*0.145)
    half_perp = max(3.0, min(pitch*0.19, median_ai_h*0.22))

    candidates = []
    # Joint search. All pads move together, so any accepted solution is a single
    # coherent strip even when individual pale pads provide little visual signal.
    # Keep the global phase close to the semantic pad centers. Previous versions
    # allowed +/-0.225 pitch and could lock onto a neighboring reagent/gap.
    for phase_i in range(-4, 5):
        phase = pitch*0.03*phase_i   # +/-0.12 pitch
        for perp_i in range(-5, 6):
            perp0 = pitch*0.04*perp_i   # +/-0.20 pitch
            for tilt_i in range(-3, 4):
                # Limit total cross-strip drift to about 0.18 pitch across 10 gaps.
                perp_step = pitch*0.006*tilt_i
                centers = []
                signals = []
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
                # Use strongest 7 pads so pale/negative pads do not dominate; still
                # reward coverage and penalize large deviations from semantic prior.
                visual = sum(scores[:7]) / 7.0
                # Strongly discourage phase drift; visual peaks alone must not
                # pull the 11 semantic slots onto adjacent pads.
                prior_penalty = 0.22*abs(phase) + 0.10*abs(perp0) + 0.16*abs(perp_step)*5
                # Center-vs-gap periodicity rewards a true pad lattice rather than
                # a line that merely crosses colorful background patches.
                gap_like = median([s["contrast"] for s in signals])
                objective = visual + strong*1.5 + 0.10*gap_like - prior_penalty
                candidates.append({"objective": objective, "visual": visual, "strong": strong,
                                   "phase": phase, "perp0": perp0, "perp_step": perp_step,
                                   "centers": centers, "signals": signals})

    if not candidates:
        return {"accepted": False, "reason": "joint strip search produced no valid model", "regions": {}}
    candidates.sort(key=lambda c: c["objective"], reverse=True)
    best = candidates[0]
    # Compare against materially different models, not merely adjacent grid cells.
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
    # A small margin is tolerated when the best model stays very close to the AI
    # semantic line; this handles flat backgrounds where neighboring grid cells tie.
    ai_close = abs(best["phase"]) <= pitch*0.10 and abs(best["perp0"]) <= pitch*0.18
    if margin < 2.0 and not ai_close:
        return {"accepted": False, "reason": "joint strip position is ambiguous", "regions": {},
                "model_margin": round(margin, 2), "pitch_pixels": round(pitch, 1)}

    # Spacing is guaranteed by construction. Refuse excessive total slope correction.
    total_perp_drift = abs(best["perp_step"]*10)
    if total_perp_drift > pitch*0.22:
        return {"accepted": False, "reason": "strip slope correction is excessive", "regions": {}}

    regions = {}
    for param, (cx, cy) in zip(PARAMETERS, best["centers"]):
        regions[param] = [max(0.0, (cx-half_along)/image.width),
                          max(0.0, (cy-half_perp)/image.height),
                          min(1.0, (cx+half_along)/image.width),
                          min(1.0, (cy+half_perp)/image.height)]

    return {"accepted": True, "reason": None, "regions": regions,
            "source": "joint_strip_signal_v2_phase_locked", "pitch_pixels": round(pitch, 1),
            "strong_pad_count": best["strong"], "visual_score": round(best["visual"], 1),
            "model_margin": round(margin, 2), "median_pad_contrast": round(median_contrast, 1),
            "median_pad_saturation": round(median_sat, 1),
            "phase_pixels": round(best["phase"], 1),
            "perpendicular_offset_pixels": round(best["perp0"], 1),
            "perpendicular_step_pixels_per_pad": round(best["perp_step"], 2),
            "semantic_axis_step_pixels": [round(dx, 2), round(dy, 2)]}
