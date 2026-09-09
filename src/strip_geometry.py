"""Geometry-first CYBOW 11M pad localization.

The detector uses image pixels to find a regularly spaced line of reagent pads.
AI-proposed regions are used only to resolve strip direction/phase and as a fallback.
"""
import math
from statistics import median
from PIL import ImageStat
from src.standards import ALLOWED_VALUES

PARAMETERS = list(ALLOWED_VALUES)


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _candidate_components(image, max_dimension=640):
    thumb = image.copy()
    thumb.thumbnail((max_dimension, max_dimension))
    w, h = thumb.size
    hsv = thumb.convert("HSV")
    cell = max(4, int(round(min(w, h) / 110.0)))
    nx = max(1, math.ceil(w / cell))
    ny = max(1, math.ceil(h / cell))
    active = set()
    stats = {}
    for gy in range(ny):
        y1, y2 = gy * cell, min(h, (gy + 1) * cell)
        for gx in range(nx):
            x1, x2 = gx * cell, min(w, (gx + 1) * cell)
            roi = hsv.crop((x1, y1, x2, y2))
            med = ImageStat.Stat(roi).median
            sat, val = med[1], med[2]
            if sat >= 30 and 45 <= val <= 245:
                active.add((gx, gy))
                stats[(gx, gy)] = (sat, val)

    comps = []
    unseen = set(active)
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        cells = [seed]
        while stack:
            gx, gy = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == dy == 0:
                        continue
                    n = (gx + dx, gy + dy)
                    if n in unseen:
                        unseen.remove(n)
                        stack.append(n)
                        cells.append(n)
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        x1, y1 = min(xs) * cell, min(ys) * cell
        x2, y2 = min(w, (max(xs) + 1) * cell), min(h, (max(ys) + 1) * cell)
        bw, bh = x2 - x1, y2 - y1
        if len(cells) < 2 or min(bw, bh) < cell or max(bw, bh) > min(w, h) * 0.24:
            continue
        aspect = max(bw, bh) / max(1.0, min(bw, bh))
        if aspect > 3.8:
            continue
        sat = median(stats[c][0] for c in cells)
        comps.append({
            "center": ((x1 + x2) / 2.0, (y1 + y2) / 2.0),
            "bbox": (x1, y1, x2, y2),
            "size": (bw, bh),
            "sat": float(sat),
            "weight": float(sat) * math.sqrt(len(cells)),
        })
    comps.sort(key=lambda c: c["weight"], reverse=True)
    scale_x = image.width / w
    scale_y = image.height / h
    return comps[:60], (w, h), (scale_x, scale_y)


def _best_axis(components):
    if len(components) < 4:
        return None
    sizes = [min(c["size"]) for c in components[:30]]
    tol = max(6.0, median(sizes) * 0.9)
    best = None
    top = components[:30]
    for i, a in enumerate(top):
        for b in top[i + 1:]:
            dx = b["center"][0] - a["center"][0]
            dy = b["center"][1] - a["center"][1]
            length = math.hypot(dx, dy)
            if length < tol * 3:
                continue
            ux, uy = dx / length, dy / length
            inliers = []
            for c in top:
                rx = c["center"][0] - a["center"][0]
                ry = c["center"][1] - a["center"][1]
                perp = abs(rx * (-uy) + ry * ux)
                if perp <= tol:
                    proj = rx * ux + ry * uy
                    inliers.append((proj, c))
            if len(inliers) < 4:
                continue
            span = max(x[0] for x in inliers) - min(x[0] for x in inliers)
            score = len(inliers) * 1000 + span + sum(x[1]["sat"] for x in inliers)
            if best is None or score > best["score"]:
                best = {"origin": a["center"], "u": (ux, uy), "inliers": inliers,
                        "tolerance": tol, "score": score}
    return best


def _linear_fit(points):
    """Least-squares y = intercept + slope*x for (index, projection) anchors."""
    if len(points) < 2:
        return None
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - xm) ** 2 for x in xs)
    if denom <= 1e-9:
        return None
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
    intercept = ym - slope * xm
    residuals = [abs(y - (intercept + slope * x)) for x, y in zip(xs, ys)]
    return intercept, slope, (sum(residuals) / len(residuals))


def _best_lattice(axis, image_size):
    inliers = sorted(axis["inliers"], key=lambda item: item[0])
    projections = [x[0] for x in inliers]
    if len(projections) < 4:
        return None
    diffs = []
    for i, a in enumerate(projections):
        for b in projections[i + 1:]:
            delta = b - a
            for k in range(1, 12):
                s = delta / k
                if 8 <= s <= min(image_size) * 0.18:
                    diffs.append(s)
    if not diffs:
        return None
    buckets = {}
    for s in diffs:
        key = round(s / 2.0) * 2.0
        buckets[key] = buckets.get(key, 0) + 1
    spacing_candidates = [k for k, _ in sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)[:20]]
    best = None
    for spacing in spacing_candidates:
        tolerance = max(4.0, spacing * 0.25)
        for proj in projections:
            for index in range(12):
                start = proj - index * spacing
                unique = {}
                for p, comp in inliers:
                    nearest = round((p - start) / spacing)
                    if 0 <= nearest <= 11:
                        error = abs(p - (start + nearest * spacing))
                        if error <= tolerance and (nearest not in unique or error < unique[nearest][0]):
                            unique[nearest] = (error, p, comp)
                count = len(unique)
                if count < 4:
                    continue
                residual = sum(v[0] for v in unique.values()) / count
                score = count * 100 - residual * 3
                if best is None or score > best["score"]:
                    best = {"start": start, "spacing": spacing, "matches": unique,
                            "count": count, "residual": residual, "score": score}
    if not best:
        return None

    # Refine pitch and phase from the actual component centers, not from the
    # quantized spacing candidate. This prevents cumulative drift at strip ends.
    anchors = [(idx, item[1]) for idx, item in best["matches"].items()]
    fit = _linear_fit(anchors)
    if fit:
        fit_start, fit_spacing, fit_residual = fit
        if fit_spacing > 0 and abs(fit_spacing - best["spacing"]) <= best["spacing"] * 0.22:
            best["raw_start"] = best["start"]
            best["raw_spacing"] = best["spacing"]
            best["start"] = fit_start
            best["spacing"] = fit_spacing
            best["fit_residual"] = fit_residual
    return best


def _geometry_centers(axis, lattice):
    ox, oy = axis["origin"]
    ux, uy = axis["u"]
    return [(ox + (lattice["start"] + i * lattice["spacing"]) * ux,
             oy + (lattice["start"] + i * lattice["spacing"]) * uy) for i in range(12)]


def _refine_centers_from_components(axis, lattice, centers):
    """Snap centers to real detected pad components where evidence is strong.

    Missing/low-saturation pads stay on the fitted lattice. Anchor corrections are
    limited so unrelated colorful objects cannot pull a reagent ROI away.
    """
    ux, uy = axis["u"]
    vx, vy = -uy, ux
    spacing = lattice["spacing"]
    refined = list(centers)
    snapped = 0
    offsets = []
    for idx, center in enumerate(centers):
        best = None
        for proj, comp in axis["inliers"]:
            expected_proj = lattice["start"] + idx * spacing
            along = abs(proj - expected_proj)
            if along > spacing * 0.32:
                continue
            dx = comp["center"][0] - center[0]
            dy = comp["center"][1] - center[1]
            perp = abs(dx * vx + dy * vy)
            if perp > max(axis["tolerance"], spacing * 0.28):
                continue
            score = along + perp * 0.7 - min(comp["sat"], 180.0) * 0.015
            if best is None or score < best[0]:
                best = (score, comp["center"], along, perp)
        if best is not None:
            _, c, along, perp = best
            # Do not snap more than 0.36 pitch in Euclidean distance.
            if _dist(center, c) <= spacing * 0.36:
                refined[idx] = c
                snapped += 1
                offsets.append(_dist(center, c))
    return refined, snapped, (median(offsets) if offsets else None)


def _handle_score(image, endpoint, outward, spacing_norm):
    ux, uy = outward
    norm = math.hypot(ux, uy)
    if norm <= 0:
        return 0.0
    ux, uy = ux / norm, uy / norm
    score = 0.0
    valid = 0
    for step in (0.65, 1.0, 1.4, 1.8, 2.3, 2.8, 3.4):
        cx = endpoint[0] + ux * spacing_norm * step
        cy = endpoint[1] + uy * spacing_norm * step
        if not (0.01 < cx < 0.99 and 0.01 < cy < 0.99):
            continue
        half = max(3, int(round(min(image.size) * spacing_norm * 0.11)))
        px, py = int(round(cx * image.width)), int(round(cy * image.height))
        box = (max(0, px-half), max(0, py-half), min(image.width, px+half+1), min(image.height, py+half+1))
        roi = image.crop(box)
        if min(roi.size) < 3:
            continue
        hsv = roi.convert("HSV")
        hstat = ImageStat.Stat(hsv)
        gray = roi.convert("L")
        gstat = ImageStat.Stat(gray)
        sat, val = hstat.median[1], hstat.median[2]
        texture = gstat.stddev[0]
        valid += 1
        neutral = max(0.0, 1.0 - sat / 55.0)
        bright = max(0.0, min(1.0, (val - 100.0) / 115.0))
        smooth = max(0.0, 1.0 - texture / 28.0)
        score += 0.35 * neutral + 0.25 * bright + 0.40 * smooth
    return score / valid if valid else 0.0


def _resolve_reagent_centers(image, centers, ai_regions):
    if len(centers) != 12:
        return None
    dx = centers[1][0] - centers[0][0]
    dy = centers[1][1] - centers[0][1]
    spacing_norm = math.hypot(dx, dy)
    if spacing_norm <= 0:
        return None

    ai_uro = ai_asc = None
    if isinstance(ai_regions, dict):
        uro, asc = ai_regions.get("urobilinogen"), ai_regions.get("ascorbic_acid")
        if isinstance(uro, list) and len(uro) == 4 and isinstance(asc, list) and len(asc) == 4:
            ai_uro, ai_asc = _center(uro), _center(asc)

    ranked = []
    for shift in range(-2, 3):
        shifted = [(x + shift * dx, y + shift * dy) for x, y in centers]
        if any(not (0.005 <= x <= 0.995 and 0.005 <= y <= 0.995) for x, y in shifted):
            continue
        forward_handle = _handle_score(image, shifted[-1], (dx, dy), spacing_norm)
        reverse_handle = _handle_score(image, shifted[0], (-dx, -dy), spacing_norm)
        hypotheses = [
            (shifted[1:], shifted[0], "compensation_before_forward", forward_handle, reverse_handle),
            (list(reversed(shifted[:-1])), shifted[-1], "compensation_after_reverse", reverse_handle, forward_handle),
        ]
        for reagent, compensation, direction, handle_score, opposite_score in hypotheses:
            handle_margin = handle_score - opposite_score
            objective = handle_margin * 4.0 + handle_score
            endpoint_error = None
            if ai_uro is not None and ai_asc is not None:
                endpoint_error = _dist(reagent[0], ai_uro) + _dist(reagent[-1], ai_asc)
                objective -= endpoint_error * 4.0
            ranked.append({"objective": objective, "reagent": reagent, "compensation": compensation,
                           "direction": direction, "shift": shift, "handle_score": handle_score,
                           "opposite_handle_score": opposite_score, "handle_margin": handle_margin,
                           "endpoint_error": endpoint_error})
    if not ranked:
        return None
    ranked.sort(key=lambda x: x["objective"], reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    objective_gap = best["objective"] - second["objective"] if second else 999.0
    handle_clear = best["handle_margin"] >= 0.055
    combined_clear = objective_gap >= 0.035 and best["handle_score"] >= 0.45
    if not (handle_clear or combined_clear):
        return None
    return {"centers": best["reagent"], "compensation_center": best["compensation"],
            "direction": best["direction"], "phase_shift": best["shift"],
            "endpoint_error": best["endpoint_error"], "handle_score": best["handle_score"],
            "opposite_handle_score": best["opposite_handle_score"],
            "handle_margin": best["handle_margin"], "orientation_objective_gap": objective_gap,
            "orientation_source": "physical_handle" if handle_clear else "handle_plus_ai"}


def detect_geometry_regions(image, ai_regions=None):
    components, thumb_size, scale = _candidate_components(image)
    axis = _best_axis(components)
    if not axis:
        return {"accepted": False, "reason": "insufficient aligned color components", "regions": {}}
    lattice = _best_lattice(axis, thumb_size)
    if not lattice or lattice["count"] < 4:
        return {"accepted": False, "reason": "could not fit 12-position CYBOW spacing", "regions": {}}

    centers_thumb = _geometry_centers(axis, lattice)
    centers_thumb, snapped_count, snap_median = _refine_centers_from_components(axis, lattice, centers_thumb)
    angle = abs(math.degrees(math.atan2(axis["u"][1], axis["u"][0])))
    angle = min(angle, abs(180 - angle))
    if angle > 22:
        return {"accepted": False, "reason": "strip angle too steep for axis-aligned sampling",
                "angle_degrees": round(angle, 1), "regions": {}}

    sx, sy = scale
    centers_px = [(x * sx, y * sy) for x, y in centers_thumb]
    centers_norm = [(x / image.width, y / image.height) for x, y in centers_px]
    if any(not (0.01 <= x <= 0.99 and 0.01 <= y <= 0.99) for x, y in centers_norm):
        return {"accepted": False, "reason": "fitted pad lattice extends outside image", "regions": {}}

    mapping = _resolve_reagent_centers(image, centers_norm, ai_regions)
    if mapping is None:
        return {"accepted": False, "reason": "strip direction/compensation area is ambiguous", "regions": {},
                "angle_degrees": round(angle, 1), "matched_components": lattice["count"]}
    centers_norm = mapping["centers"]

    # Fail closed when the fitted line is too uncertain. 14 px residual from the
    # 2026-09-09 field image was enough to sample background instead of pads.
    residual_px = lattice.get("fit_residual", lattice["residual"]) * (sx + sy) / 2.0
    spacing_px = lattice["spacing"] * (sx + sy) / 2.0
    residual_ratio = residual_px / max(spacing_px, 1.0)
    if residual_ratio > 0.18 or (lattice["count"] < 6 and snapped_count < 5):
        return {"accepted": False, "reason": "pad lattice localization confidence too low", "regions": {},
                "angle_degrees": round(angle, 1), "matched_components": lattice["count"],
                "snapped_components": snapped_count, "lattice_residual_pixels": round(residual_px, 1),
                "residual_ratio": round(residual_ratio, 3)}

    spacing_x = lattice["spacing"] * sx / image.width
    spacing_y = lattice["spacing"] * sy / image.height
    half_w = max(0.004, spacing_x * 0.28)
    half_h = max(0.004, spacing_y * 0.24)
    regions = {}
    for param, (cx, cy) in zip(PARAMETERS, centers_norm):
        regions[param] = [max(0, cx - half_w), max(0, cy - half_h),
                          min(1, cx + half_w), min(1, cy + half_h)]

    errors = []
    for param, box in (ai_regions or {}).items():
        if param in regions and isinstance(box, list) and len(box) == 4:
            errors.append(_dist(_center(regions[param]), _center(box)))
    median_ai_error = median(errors) if errors else None
    return {"accepted": True, "reason": None, "regions": regions,
            "source": "pixel_geometry_lattice_v2_anchor_refined", "direction": mapping["direction"],
            "compensation_center": [round(v, 5) for v in mapping["compensation_center"]],
            "endpoint_error": round(mapping["endpoint_error"], 4) if mapping["endpoint_error"] is not None else None,
            "phase_shift": mapping["phase_shift"], "orientation_source": mapping["orientation_source"],
            "handle_score": round(mapping["handle_score"], 4),
            "opposite_handle_score": round(mapping["opposite_handle_score"], 4),
            "handle_margin": round(mapping["handle_margin"], 4),
            "orientation_objective_gap": round(mapping["orientation_objective_gap"], 4),
            "lattice_positions": 12, "angle_degrees": round(angle, 1),
            "matched_components": lattice["count"], "snapped_components": snapped_count,
            "snap_median_pixels": round(snap_median * (sx + sy) / 2.0, 1) if snap_median is not None else None,
            "spacing_pixels": round(spacing_px, 1), "lattice_residual_pixels": round(residual_px, 1),
            "residual_ratio": round(residual_ratio, 3),
            "median_ai_center_error": round(median_ai_error, 4) if median_ai_error is not None else None}
