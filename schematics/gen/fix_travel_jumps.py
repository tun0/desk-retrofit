#!/usr/bin/env python3
"""Repair a real bug in FlatCAM Evo's isolation G-code generation: when the
isolation geometry for a copper region is a polygon-with-holes (an exterior
boundary plus several interior rings - exactly what you get isolating small
pads/vias sitting inside a large ground-fill zone), the path-optimization
code that's supposed to insert a retract-travel-replunge sequence between
separate loops silently degrades to nothing when no FlatCAM "exclusion
area" is defined (the normal case - this project never uses that feature).
Traced directly in camlib.py/appCommon/Common.py: travel_coordinates()
always returns at least one [None, end_point] entry even with zero
exclusion areas, but linear2gcode()'s handling of that entry only ever
emits a bare rapid_code (G00 X.. Y..) with no matching lift_code (G00 Z),
so the tool goes straight into the next loop's own linear_code (G01 X..
Y..) while still sitting at cutting depth from the previous loop - a
straight, uncontrolled gouge connecting two unrelated isolation loops.

A pure distance threshold (the original approach - any >1mm G1 move while
cutting) turned out unreliable once this project switched to iso_type=0
(see mill.tcl and the conversation): genuine bogus gouges and genuine long
STRAIGHT design cuts (e.g. a run parallel to the board's own straight edge,
which needs few tessellation points because it's not curved) overlap in
length with no clean gap - confirmed directly: raising the threshold from
1mm to 20mm only recovered isolation coverage from 33% to 62% of a 76%
ceiling, never cleanly separating the two classes, because some genuine
bogus jumps are as short as ~7mm and some genuine long cuts run 20mm+.
Blanket-fixing every long move destroyed roughly two-thirds of this
design's real isolation coverage - confirmed by directly measuring how much
of the design's own clearance-channel centerlines the toolpath actually
follows, with and without this fix applied.

The reliable distinguishing signal is geometric, not length-based: a
genuine isolation cut runs immediately alongside a real copper edge for its
ENTIRE length (that's what isolating a boundary means); a bogus gouge
connects two unrelated loops through open space, potentially far from any
copper edge along most of its route. So this now takes the same copper SVG
verify_isolation.py already knows how to render, computes "distance to
nearest copper" at every point on the board, and classifies a long move by
sampling points along it: if it hugs copper (within COPPER_HUG_TOLERANCE_MM)
the whole way, it's a real cut and is left alone regardless of length; if
it strays further from copper at any sampled point, it's treated as a
bogus gouge and rewritten as retract -> rapid -> replunge, using the SAME
travel/cut Z values already present elsewhere in the same file (not
hardcoded).

Usage: python3 fix_travel_jumps.py <input.nc> <output.nc> <copper.svg> <board_width_mm> <board_height_mm> [threshold_mm]
"""
import re
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from verify_isolation import render_at  # noqa: E402

# A real isolation cut is centered somewhere within the copper-to-copper
# clearance gap (0.4mm DRC minimum here) and is itself ~0.22mm wide (3
# passes, see mill.tcl) - so a point genuinely ON a cut is never more than
# about half the clearance gap from the nearest copper edge. 0.3mm gives
# comfortable margin above that without being so loose it accepts a real
# cross-board shortcut that happens to graze copper once in passing.
COPPER_HUG_TOLERANCE_MM = 0.3
# How finely to sample along a candidate long move - fine enough that a
# shortcut can't "jump over" a spot where it strays from copper.
SAMPLE_STEP_MM = 0.05


def build_distance_field(svg_path, board_w, board_h, px_per_mm=100):
    """Distance (mm) from every point on the board to the nearest
    copper/clearance EDGE in the KiCad design render - NOT distance to
    copper itself. That distinction matters: distance-to-copper is
    trivially 0 for any point already inside solid copper, so a gouge
    straight through the interior of a pad or trace would score as
    "hugging copper" and pass as safe - confirmed directly as a real blind
    spot before this was fixed. Distance-to-EDGE is small only near an
    actual copper/clearance transition, correctly flagging both a
    cross-country shortcut through open space AND a plow straight through
    copper interior, with one consistent rule: a genuine isolation cut
    stays near the boundary line it's isolating, the whole way.
    Reuses verify_isolation.py's own validated SVG rendering (segments=[]
    since only on_blank_copper is needed here, not any toolpath)."""
    from scipy import ndimage

    base, on_blank_copper, _swept, _copper_color, margin_px = render_at(
        svg_path, [], 0.1, board_w, board_h, px_per_mm, min_line_px=1)
    is_white = np.all(base > 240, axis=-1)
    is_black = np.all(base < 30, axis=-1)
    is_offboard = ~on_blank_copper & ~is_black
    is_copper_design = ~is_white & ~is_black & ~is_offboard
    eroded = ndimage.binary_erosion(is_copper_design)
    edge = is_copper_design & ~eroded
    dist_px = ndimage.distance_transform_edt(~edge)
    return dist_px / px_per_mm, margin_px, px_per_mm


def hugs_copper(x0, y0, x1, y1, dist_mm_field, margin_px, px_per_mm, board_h):
    """True if every sampled point along (x0,y0)-(x1,y1) stays within
    COPPER_HUG_TOLERANCE_MM of real copper - i.e. this looks like a genuine
    boundary-following cut, not a cross-country shortcut."""
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    steps = max(2, int(length / SAMPLE_STEP_MM))
    h, w = dist_mm_field.shape
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        px = int(round(x * px_per_mm + margin_px))
        py = int(round((board_h - y) * px_per_mm + margin_px))
        if not (0 <= py < h and 0 <= px < w):
            return False  # off the rendered board entirely - never a real cut
        if dist_mm_field[py, px] > COPPER_HUG_TOLERANCE_MM:
            return False
    return True


# Separate from the dangerous-jump bug above: even a loop FlatCAM computes
# correctly can get exported one segment short of actually closing back to
# its own start point - confirmed directly (one pad's isolation ring simply
# stops ~1mm shy of its start, with nothing else covering that stretch).
# Distinguishing this from a legitimate open loop (e.g. a pad with several
# same-net traces attached, correctly left uncut where they attach) needs a
# different, more direct test than hugs_copper: sample the DESIGN's own
# render along the straight gap - a legitimate skip runs through actual
# copper (a trace attaches there, no cut wanted); a genuine unclosed-loop
# bug runs entirely through white/clearance (the design plainly wants a cut,
# FlatCAM just didn't finish drawing it). Confirmed clean on every candidate
# found in this project's own output: every real gap scored 100% white,
# with no ambiguous middle ground - see conversation.
CLOSE_GAP_THRESHOLD_MM = 0.3
WHITE_FRACTION_THRESHOLD = 0.8


def frac_white_along(x0, y0, x1, y1, base, margin_px, px_per_mm, board_h):
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    steps = max(2, int(length / SAMPLE_STEP_MM))
    h, w, _ = base.shape
    white = 0
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        px = int(round(x * px_per_mm + margin_px))
        py = int(round((board_h - y) * px_per_mm + margin_px))
        if 0 <= py < h and 0 <= px < w and (base[py, px] > 240).all():
            white += 1
    return white / (steps + 1)


def close_unclosed_loops(lines, base, margin_px, px_per_mm, board_h):
    """Second pass: for every cutting segment (between a plunge and the
    next retract), if it ends more than CLOSE_GAP_THRESHOLD_MM from where
    it started AND the straight line back to the start runs through real
    design clearance, insert the missing closing cut before the retract."""
    out = []
    x, y = 0.0, 0.0
    cutting = False
    seg_start = None
    closed_count = 0

    move_re = re.compile(r"^(G0?[01])\b")
    coord_re = re.compile(r"([XYZ])(-?\d+\.?\d*)")

    for line in lines:
        s = line.strip()
        m = move_re.match(s)
        if not m:
            out.append(line)
            continue

        is_g0 = m.group(1) in ("G0", "G00")
        tokens = dict(coord_re.findall(s))
        has_z = "Z" in tokens
        has_xy = "X" in tokens or "Y" in tokens

        if has_z:
            if is_g0 and cutting and seg_start is not None:
                gap = ((x - seg_start[0]) ** 2 + (y - seg_start[1]) ** 2) ** 0.5
                if gap > CLOSE_GAP_THRESHOLD_MM:
                    frac = frac_white_along(x, y, seg_start[0], seg_start[1], base, margin_px, px_per_mm, board_h)
                    if frac > WHITE_FRACTION_THRESHOLD:
                        out.append(f"G01 X{seg_start[0]:.4f} Y{seg_start[1]:.4f}\n")
                        closed_count += 1
            cutting = not is_g0
            if not is_g0:
                seg_start = (x, y)
            out.append(line)
            continue

        if has_xy:
            x = float(tokens["X"]) if "X" in tokens else x
            y = float(tokens["Y"]) if "Y" in tokens else y
        out.append(line)

    return out, closed_count


def fix(lines, threshold, dist_field=None, margin_px=None, px_per_mm=None, board_h=None):
    out = []
    x, y = 0.0, 0.0
    cutting = False       # True once a down_code (G01 Z<cutz>) has run and
                            # no lift_code (G00 Z<travelz>) has run since
    cut_z = None
    travel_z = None
    fixed_count = 0
    geometry_aware = dist_field is not None

    move_re = re.compile(r"^(G0?[01])\b")
    coord_re = re.compile(r"([XYZ])(-?\d+\.?\d*)")

    for line in lines:
        s = line.strip()
        m = move_re.match(s)
        if not m:
            out.append(line)
            continue

        is_g0 = m.group(1) in ("G0", "G00")
        tokens = dict(coord_re.findall(s))
        has_z = "Z" in tokens
        has_xy = "X" in tokens or "Y" in tokens

        if has_z:
            z_val = float(tokens["Z"])
            if is_g0:
                travel_z = z_val
                cutting = False
            else:
                cut_z = z_val
                cutting = True

        if has_xy and not has_z:
            new_x = float(tokens["X"]) if "X" in tokens else x
            new_y = float(tokens["Y"]) if "Y" in tokens else y
            dist = ((new_x - x) ** 2 + (new_y - y) ** 2) ** 0.5

            is_dangerous = (not is_g0) and cutting and dist > threshold and travel_z is not None and cut_z is not None
            if is_dangerous and geometry_aware:
                # Only actually fix it if it does NOT look like a real
                # boundary-following cut - length alone is not enough
                # evidence any more (see module docstring).
                is_dangerous = not hugs_copper(x, y, new_x, new_y, dist_field, margin_px, px_per_mm, board_h)

            if is_dangerous:
                out.append(f"G00 Z{travel_z:.4f}\n")
                out.append(f"G00 X{new_x:.4f} Y{new_y:.4f}\n")
                out.append(f"G01 Z{cut_z:.4f}\n")
                fixed_count += 1
            else:
                out.append(line)

            x, y = new_x, new_y
        else:
            out.append(line)

    return out, fixed_count


def main():
    if len(sys.argv) not in (6, 7):
        print(__doc__)
        sys.exit(1)
    in_path, out_path, svg_path = sys.argv[1], sys.argv[2], sys.argv[3]
    board_w, board_h = float(sys.argv[4]), float(sys.argv[5])
    threshold = float(sys.argv[6]) if len(sys.argv) == 7 else 1.0

    dist_field, margin_px, px_per_mm = build_distance_field(svg_path, board_w, board_h)
    base, _on_blank_copper, _swept, _copper_color, _margin_px2 = render_at(
        svg_path, [], 0.1, board_w, board_h, px_per_mm, min_line_px=1)

    lines = open(in_path).readlines()
    fixed_lines, count = fix(lines, threshold, dist_field, margin_px, px_per_mm, board_h)
    fixed_lines, closed_count = close_unclosed_loops(fixed_lines, base, margin_px, px_per_mm, board_h)

    with open(out_path, "w") as f:
        f.writelines(fixed_lines)
    print(f"wrote {out_path} ({count} dangerous in-material jumps repaired, "
          f"{closed_count} unclosed loops closed, threshold {threshold}mm, geometry-aware)")


if __name__ == "__main__":
    main()
