"""Geometry-first CYBOW 11M pad localization.

The detector uses image pixels to find a regularly spaced line of reagent pads.
AI-proposed regions are used only to resolve strip direction and as a fallback by the caller.
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


def _best_lattice(axis, image_size):
    projections = sorted(x[0] for x in axis["inliers"])
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
    # Quantize spacing candidates so repeated evidence reinforces the true pad pitch.
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
                matches = []
                for p in projections:
                    nearest = round((p - start) / spacing)
                    if 0 <= nearest <= 11:
                        error = abs(p - (start + nearest * spacing))
                        if error <= tolerance:
                            matches.append((nearest, error))
                unique = {}
                for idx, err in matches:
                    unique[idx] = min(err, unique.get(idx, 1e9))
                count = len(unique)
                if count < 4:
                    continue
                residual = sum(unique.values()) / count
                score = count * 100 - residual * 3 - abs(spacing - median(spacing_candidates)) * 0.05
                if best is None or score > best["score"]:
                    best = {"start": start, "spacing": spacing, "matches": unique,
                            "count": count, "residual": residual, "score": score}
    return best


def _geometry_centers(axis, lattice):
    ox, oy = axis["origin"]
    ux, uy = axis["u"]
    return [(ox + (lattice["start"] + i * lattice["spacing"]) * ux,
             oy + (lattice["start"] + i * lattice["spacing"]) * uy) for i in range(12)]


def _resolve_reagent_centers(centers, ai_regions):
    """Resolve lattice phase, compensation end, and semantic direction.

    Low-saturation pads can be absent from color-component detection, so the
    lattice phase may be one pitch off. AI endpoint proposals are used only
    to choose among integer-pitch geometry hypotheses.
    """
    if not isinstance(ai_regions, dict) or len(centers) != 12:
        return None
    uro, asc = ai_regions.get("urobilinogen"), ai_regions.get("ascorbic_acid")
    if not (isinstance(uro, list) and len(uro) == 4 and isinstance(asc, list) and len(asc) == 4):
        return None
    ai_uro, ai_asc = _center(uro), _center(asc)
    dx = centers[1][0] - centers[0][0]
    dy = centers[1][1] - centers[0][1]
    ranked = []
    for shift in range(-2, 3):
        shifted = [(x + shift * dx, y + shift * dy) for x, y in centers]
        hypotheses = [
            (shifted[1:], shifted[0], "compensation_before_forward"),
            (list(reversed(shifted[:-1])), shifted[-1], "compensation_after_reverse"),
        ]
        for reagent, compensation, direction in hypotheses:
            if any(not (0.005 <= x <= 0.995 and 0.005 <= y <= 0.995) for x, y in shifted):
                continue
            error = _dist(reagent[0], ai_uro) + _dist(reagent[-1], ai_asc)
            ranked.append((error, reagent, compensation, direction, shift))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0])
    if len(ranked) > 1 and ranked[1][0] - ranked[0][0] < 0.008:
        return None
    best = ranked[0]
    return {"centers": best[1], "compensation_center": best[2],
            "direction": best[3], "phase_shift": best[4], "endpoint_error": best[0]}

def detect_geometry_regions(image, ai_regions=None):
    components, thumb_size, scale = _candidate_components(image)
    axis = _best_axis(components)
    if not axis:
        return {"accepted": False, "reason": "insufficient aligned color components", "regions": {}}
    lattice = _best_lattice(axis, thumb_size)
    if not lattice or lattice["count"] < 4:
        return {"accepted": False, "reason": "could not fit 12-position CYBOW spacing", "regions": {}}

    centers_thumb = _geometry_centers(axis, lattice)
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

    mapping = _resolve_reagent_centers(centers_norm, ai_regions)
    if mapping is None:
        return {"accepted": False, "reason": "strip direction/compensation area is ambiguous", "regions": {},
                "angle_degrees": round(angle, 1), "matched_components": lattice["count"]}
    centers_norm = mapping["centers"]
    direction = mapping["direction"]

    spacing_x = lattice["spacing"] * sx / image.width
    spacing_y = lattice["spacing"] * sy / image.height
    half_w = max(0.004, spacing_x * 0.33)
    half_h = max(0.004, spacing_y * 0.30)
    regions = {}
    for param, (cx, cy) in zip(PARAMETERS, centers_norm):
        regions[param] = [max(0, cx - half_w), max(0, cy - half_h),
                          min(1, cx + half_w), min(1, cy + half_h)]

    # Compare geometry centers with all usable AI centers as a diagnostic only.
    errors = []
    for param, box in (ai_regions or {}).items():
        if param in regions and isinstance(box, list) and len(box) == 4:
            errors.append(_dist(_center(regions[param]), _center(box)))
    median_ai_error = median(errors) if errors else None
    return {
        "accepted": True,
        "reason": None,
        "regions": regions,
        "source": "pixel_geometry_lattice_v1",
        "direction": direction,
        "compensation_center": [round(v, 5) for v in mapping["compensation_center"]],
        "endpoint_error": round(mapping["endpoint_error"], 4),
        "phase_shift": mapping["phase_shift"],
        "lattice_positions": 12,
        "angle_degrees": round(angle, 1),
        "matched_components": lattice["count"],
        "spacing_pixels": round(lattice["spacing"] * (sx + sy) / 2.0, 1),
        "lattice_residual_pixels": round(lattice["residual"] * (sx + sy) / 2.0, 1),
        "median_ai_center_error": round(median_ai_error, 4) if median_ai_error is not None else None,
    }
