#!/usr/bin/env python3
"""Generate an isolation-milling toolpath directly from the design's own
already-computed copper/clearance boundary - the same KiCad SVG render
verify_isolation.py already trusts as ground truth (render_at()) - instead
of handing the Gerber to FlatCAM or pcb2gcode and trusting their own
internal polygon-offset algorithm. Both of those showed real, confirmed
bugs on this board (FlatCAM: 3 distinct ones, see APPENDIX §7.1; pcb2gcode
--voronoi: 2 more). This generator has none found so far, across extensive
spot-checking (all four mounting holes, the DevKitC header row, several
vias/pads near C4/D4/U5, a thermal-relief pad) - see APPENDIX §7.1 for the
full investigation.

Pipeline: raster copper mask -> cv2.findContours (with hole hierarchy) ->
Shapely polygons -> Shapely .buffer() at N concentric radii (replicating
mill.tcl's 3-pass/40%-overlap/0.1mm-tool recipe) -> G-code directly in
board-mm coordinates (true board bottom-left = (0,0) by construction - no
dependency on pcb2gcode's bounding-box-inflation quirk at all, see
APPENDIX §7.1's "Coordinate frame" note on that).

Three defects were found and fixed during development, in order:

1. A pad's own future drill hole isn't a net boundary - it's still solid
   copper before drilling, and milling a channel around it is pure waste
   (drilling removes it regardless, and duplicating that risks a channel
   not landing exactly where the drill goes). Fixed by cross-referencing
   every hole in the copper mask against the real Excellon drill file:
   a hole whose own extent is no wider than its matching drill is skipped
   entirely (treated as solid copper); only holes wider than their drill
   (e.g. a mounting hole's clearance disc, deliberately drawn bigger than
   the hole itself) get a toolpath. See is_drilled_away().
2. Any copper feature that runs close to the board edge (the main ground
   pour routinely does) pushes an un-clipped offset boundary slightly past
   the true edge. Fixed by intersecting every offset pass with the board
   rectangle before emitting it - see channel_paths().
3. Wherever a design's own clearance gap is wider than the channel's reach
   from either side (twice ISOLATION_WIDTH_MM), whatever copper sits in
   the middle never gets touched by the channel toolpath alone - confirmed
   harmless (always disconnected from every net, never a short) but still
   real leftover copper, and pcb2gcode's own default output has an even
   larger total instance of the same characteristic on this board. Small,
   bounded instances of this are auto-cleared with a second, dedicated
   pocket-clearing pass (find_orphan_islands() + pocket_paths()); anything
   larger than MAX_ORPHAN_AREA_MM2 is left alone and warned about instead
   of blindly milled, since that would indicate a real bug rather than
   this expected characteristic.

Usage: python3 custom_isolate.py <copper.svg> <board_w> <board_h> <out.nc> <drill.drl> [--mirror]

--mirror: pass this for the back layer. The copper.svg for the back layer
must ALREADY be mirrored at kicad-cli export time (--mirror flag, the same
convention mill.tcl and the pcb2gcode Makefile target already use - "flip
like a page", about the board's own vertical centerline) - this flag only
tells THIS script to also mirror the (unmirrored, since a physical hole is
the same from either face) drill positions before matching them against
that already-mirrored copper mask.
"""
import argparse
import re
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import numpy as np
import cv2
from scipy import ndimage
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from verify_isolation import render_at

TOOL_DIA_MM = 0.1
ISOLATION_WIDTH_MM = 0.22
OVERLAP_FRACTION = 0.40
PX_PER_MM = 100
Z_SAFE = 2.0
Z_CUT = -0.1
FEED = 80
SPINDLE_SPEED = 10000  # matches --mill-speed in the pcb2gcode fallback recipe

# True board rectangle in Excellon/Gerber-native coordinates (X 15-85,
# Y -115 to -15 - established by matching a known mounting-hole drill
# position against its KiCad-absolute coordinates, see APPENDIX §7.1).
BOARD_XMIN_GERBER = 15.0
BOARD_YMIN_GERBER = -115.0

HOLE_MATCH_TOLERANCE_MM = 0.05

# An orphan island bigger than this is treated as a possible bug, not a
# legitimate leftover - e.g. a whole unconnected net that never got a
# channel at all would be way bigger than any real
# gap-wider-than-channel-reach case. Refuse to blindly mill something this
# large; investigate instead (see module docstring, point 3).
MAX_ORPHAN_AREA_MM2 = 4.0
MIN_ORPHAN_AREA_MM2 = 0.02  # below this: rendering-noise fragments, not real


def parse_drill_holes(drl_path, board_w, mirror):
    """Returns [(x_mm, y_mm, radius_mm), ...] in the same board-mm frame
    build_copper_polygons() works in. mirror=True flips x about the
    board's own centerline (board_w/2) - see module docstring."""
    tool_dia = {}
    holes = []
    current_tool = None
    for line in open(drl_path):
        s = line.strip()
        m = re.match(r"^T(\d+)C([\d.]+)$", s)
        if m:
            tool_dia[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"^T(\d+)$", s)
        if m:
            current_tool = m.group(1)
            continue
        m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", s)
        if m and current_tool is not None:
            gx, gy = float(m.group(1)), float(m.group(2))
            x_mm = gx - BOARD_XMIN_GERBER
            y_mm = gy - BOARD_YMIN_GERBER
            if mirror:
                x_mm = board_w - x_mm
            holes.append((x_mm, y_mm, tool_dia[current_tool] / 2))
    return holes


def hole_metrics(pts_mm):
    """centroid + max radius from centroid, for one contour's mm points."""
    arr = np.array(pts_mm)
    cx, cy = arr.mean(axis=0)
    r = np.max(np.hypot(arr[:, 0] - cx, arr[:, 1] - cy))
    return cx, cy, r


def is_drilled_away(cx, cy, r, drill_holes):
    """True if this hole is fully explained by a real drill position (a
    plain pad/via annular ring - drilling removes exactly this, no net
    boundary here) rather than genuine undrilled clearance (e.g. a
    mounting hole's clearance disc, deliberately wider than its own
    drill)."""
    for dx, dy, dr in drill_holes:
        if abs(cx - dx) < 0.3 and abs(cy - dy) < 0.3 and r <= dr + HOLE_MATCH_TOLERANCE_MM:
            return True
    return False


def build_copper_polygons(svg_path, board_w, board_h, drill_holes):
    base, on_blank_copper, _swept, _copper_color, margin_px = render_at(
        svg_path, [], TOOL_DIA_MM, board_w, board_h, PX_PER_MM, min_line_px=1)
    is_white = np.all(base > 240, axis=-1)
    is_offboard = ~on_blank_copper & ~np.all(base < 30, axis=-1)
    # Deliberately NOT excluding hole-marker pixels here - see module
    # docstring point 1 and is_drilled_away().
    is_copper = (~is_white & ~is_offboard).astype(np.uint8) * 255

    contours, hierarchy = cv2.findContours(is_copper, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    hierarchy = hierarchy[0]  # cv2 wraps it in an extra dim

    def to_mm(pts):
        xs = (pts[:, 0, 0] - margin_px) / PX_PER_MM
        ys = board_h - (pts[:, 0, 1] - margin_px) / PX_PER_MM
        return list(zip(xs, ys))

    polys = []
    n_holes_total = 0
    n_holes_skipped = 0
    for i, cnt in enumerate(contours):
        parent = hierarchy[i][3]
        if parent != -1:
            continue  # handled as a hole of its parent below
        if len(cnt) < 3:
            continue
        exterior = to_mm(cnt)
        holes = []
        child = hierarchy[i][2]
        while child != -1:
            if len(contours[child]) >= 3:
                n_holes_total += 1
                pts = to_mm(contours[child])
                cx, cy, r = hole_metrics(pts)
                if is_drilled_away(cx, cy, r, drill_holes):
                    n_holes_skipped += 1
                else:
                    holes.append(pts)
            child = hierarchy[child][0]
        try:
            poly = Polygon(exterior, holes)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.is_empty:
                polys.append(poly)
        except Exception as e:
            print(f"skipping bad contour {i}: {e}", file=sys.stderr)
    print(f"drill-matched holes skipped (no isolation needed): "
          f"{n_holes_skipped}/{n_holes_total}")
    return unary_union(polys)


def offset_radii():
    tool_r = TOOL_DIA_MM / 2
    step = TOOL_DIA_MM * (1 - OVERLAP_FRACTION)
    radii = [tool_r]
    while radii[-1] + step <= ISOLATION_WIDTH_MM - tool_r + 1e-9:
        radii.append(radii[-1] + step)
    return radii


def paths_of(geom):
    """Yield coordinate lists from a (possibly board-clipped) boundary
    geometry. Closed rings stay closed (first point == last); pieces cut
    open by the board rectangle become open paths - both are valid G-code
    paths, just retract/replunge instead of looping."""
    if geom.is_empty:
        return
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        if len(coords) >= 2:
            yield coords
    elif geom.geom_type in ("MultiLineString", "GeometryCollection"):
        for g in geom.geoms:
            yield from paths_of(g)


def channel_paths(copper_union, board_w, board_h):
    """The normal isolation-channel toolpath: N concentric offsets of the
    copper boundary, clipped to the board rectangle. Returns a list of
    coordinate lists (open or closed)."""
    board_rect = box(0, 0, board_w, board_h)
    paths = []
    for r in offset_radii():
        offset = copper_union.buffer(r, join_style="round", quad_segs=8)
        clipped = offset.boundary.intersection(board_rect)
        for coords in paths_of(clipped):
            if len(coords) >= 2:
                paths.append(coords)
    return paths


def find_orphan_islands(svg_path, board_w, board_h, channel_paths_list):
    """Copper the design wants bare but that sits further from any copper
    edge than the channel toolpath reaches - see module docstring point 3.
    Reuses render_at's own swept-mask rasterizer against the
    already-generated channel paths, rather than re-deriving it, so this
    stays consistent with the same tool verify_isolation.py trusts."""
    base, on_blank_copper, swept, _copper_color, margin_px = render_at(
        svg_path, channel_paths_list, TOOL_DIA_MM, board_w, board_h, PX_PER_MM, min_line_px=1)
    is_white = np.all(base > 240, axis=-1)
    is_offboard = ~on_blank_copper & ~np.all(base < 30, axis=-1)
    leftover = is_white & on_blank_copper & ~is_offboard & ~swept

    labels, n = ndimage.label(leftover, structure=np.ones((3, 3)))
    sizes = ndimage.sum(leftover, labels, index=range(1, n + 1))
    px_area_mm2 = 1 / (PX_PER_MM ** 2)

    islands = []
    for i, size_px in enumerate(sizes):
        area_mm2 = size_px * px_area_mm2
        if area_mm2 < MIN_ORPHAN_AREA_MM2:
            continue
        if area_mm2 > MAX_ORPHAN_AREA_MM2:
            print(f"WARNING: skipping a {area_mm2:.2f}mm^2 leftover region - "
                  f"too big to be a normal gap-wider-than-channel case, "
                  f"treating as a possible bug instead of auto-clearing it",
                  file=sys.stderr)
            continue
        mask = (labels == (i + 1)).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for cnt in contours:
            if len(cnt) < 3:
                continue
            xs = (cnt[:, 0, 0] - margin_px) / PX_PER_MM
            ys = board_h - (cnt[:, 0, 1] - margin_px) / PX_PER_MM
            poly = Polygon(zip(xs, ys))
            if not poly.is_valid:
                poly = poly.buffer(0)
            if not poly.is_empty:
                islands.append(poly)
    print(f"orphan islands found: {len(islands)} "
          f"(total {sum(p.area for p in islands):.2f}mm^2)")
    return islands


def pocket_paths(island_polys):
    """Fully clear each orphan island - not just its boundary - with
    concentric inward offsets (classic pocket-clearing), since these are
    small enough that machining time isn't a concern the way it would be
    for the whole board (see MAX_ORPHAN_AREA_MM2)."""
    paths = []
    step = TOOL_DIA_MM * (1 - OVERLAP_FRACTION)
    for poly in island_polys:
        current = poly
        while not current.is_empty and current.area > 1e-9:
            rings = current.geoms if current.geom_type == "MultiPolygon" else [current]
            for ring in [g.exterior for g in rings]:
                coords = list(ring.coords)
                if len(coords) >= 2:
                    paths.append(coords)
            current = current.buffer(-step, join_style="round", quad_segs=8)
    return paths


def write_gcode(paths, out_path):
    # snapmaker_header.py (which every mill.tcl/pcb2gcode output already
    # goes through too) locates the real job body by its first M03 - it
    # discards everything before that line and replaces it with the header
    # Snapmaker's own touchscreen requires. Needs a real M03 here for the
    # same reason those pipelines have one: turn the spindle on before the
    # first cutting move, not just to satisfy that parser.
    lines = ["( Isolation toolpath - direct KiCad-boundary offset, "
             "plus orphan-island pocket clearing - see custom_isolate.py )",
             "G94", "G21", "G90",
             f"G00 Z{Z_SAFE:.5f}",
             f"M03 S{SPINDLE_SPEED}"]
    n_points = 0
    for coords in paths:
        n_points += len(coords)
        x0, y0 = coords[0]
        lines.append(f"G00 X{x0:.5f} Y{y0:.5f}")
        lines.append(f"G01 Z{Z_CUT:.5f} F{FEED}")
        for x, y in coords[1:]:
            lines.append(f"G01 X{x:.5f} Y{y:.5f} F{FEED}")
        lines.append(f"G00 Z{Z_SAFE:.5f}")
    lines.append("M05")
    lines.append("M2")
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path}: {len(paths)} loops, {n_points} points")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("svg_path")
    p.add_argument("board_w", type=float)
    p.add_argument("board_h", type=float)
    p.add_argument("out_path")
    p.add_argument("drl_path")
    p.add_argument("--mirror", action="store_true",
                   help="back layer: svg_path must already be mirrored at "
                        "export time; this only mirrors drill positions "
                        "to match")
    args = p.parse_args()

    drill_holes = parse_drill_holes(args.drl_path, args.board_w, args.mirror)
    print(f"parsed {len(drill_holes)} drill positions from {args.drl_path}"
          f"{' (mirrored)' if args.mirror else ''}")
    copper_union = build_copper_polygons(args.svg_path, args.board_w, args.board_h, drill_holes)
    print(f"copper union: {copper_union.geom_type}, "
          f"{len(copper_union.geoms) if copper_union.geom_type == 'MultiPolygon' else 1} parts")
    main_paths = channel_paths(copper_union, args.board_w, args.board_h)
    islands = find_orphan_islands(args.svg_path, args.board_w, args.board_h, main_paths)
    extra_paths = pocket_paths(islands)
    write_gcode(main_paths + extra_paths, args.out_path)


if __name__ == "__main__":
    main()
