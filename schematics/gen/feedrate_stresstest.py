#!/usr/bin/env python3
"""Generate a feed-rate calibration coupon: the exact same 3-pass/40%-
overlap isolation-channel recipe custom_isolate.py uses for the real board
(same offset_radii(), same tool diameter, same channel width), repeated at
a range of XY cutting feed rates - so the fastest speed that still
isolates reliably can be found empirically on SCRAP copper-clad stock,
rather than guessed. mill.tcl has carried a "TODO: calibrate against test
coupon" placeholder for iso_feedrate since early in this project; this is
that calibration, finally done.

Cut this on a scrap offcut of copper-clad FR4, NOT the real board blank -
sized to fit within the real 70x100mm blank (checked at generation time)
so the existing jig (enclosure/mill_jig.scad) can still register it.

Four isolated pad shapes per row (sized like a typical via/pad on the
real board), each row at a different XY feed rate:
  - circle: smooth curves only, no corners.
  - square: axis-aligned straight edges, four 90-degree corners.
  - diamond (a square rotated 45 degrees): diagonal straight edges,
    still four 90-degree corners - tests diagonal motion, NOT sharper
    cornering.
  - right isoceles triangle: two genuine 45-degree corners plus one
    90-degree corner - a tighter direction change than square/diamond
    give, and the case most likely to actually reveal cornering/
    deflection problems before a 90-degree corner does.
Z-axis plunge feed is held fixed and conservative (PLUNGE_FEED) across
every row and shape, so XY feed is the only variable under test -
custom_isolate.py's own G-code uses the same feed value for plunge and
XY cutting, which would confound the two if tested directly through
Luban's own speed override instead.

Each row is also engraved with its own feed-rate number (simple
7-segment-style digit strokes, single shallow pass - not the isolation
treatment, since a label is informational, not an electrical feature)
so rows stay identifiable by eye without cross-referencing this script.

After cutting, check each row's pad with a multimeter: continuity between
the pad and the surrounding copper means that row's feed rate did NOT
isolate reliably. The fastest row with NO continuity is the feed rate to
use for real production. This is an objective, exact pass/fail test - no
need to eyeball the cut under magnification.

Usage: python3 feedrate_stresstest.py <out.nc> [--preview <out.png>]
Then: python3 snapmaker_header.py <out.nc> <out.snapmaker.nc>
(raw G-code crashes the Snapmaker touchscreen - see snapmaker_header.py's
own docstring - the same post-processing every other output here needs.)
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from shapely.geometry import Point, Polygon, box
from shapely import affinity
from custom_isolate import offset_radii, Z_SAFE, Z_CUT, SPINDLE_SPEED

# The range under test - from the current production baseline (80mm/min)
# up to 400mm/min. Not a documented machine limit, just where the sweep
# currently stops; extend further if the fastest row here still isolates
# cleanly.
FEED_RATES = [80, 120, 160, 200, 250, 300, 350, 400]

PLUNGE_FEED = 40  # mm/min - fixed and conservative; see module docstring
PAD_SIZE_MM = 3.0  # typical via/pad scale on the real board (diameter/side)
ROW_SPACING_MM = 11.5  # leaves ~8mm of surrounding copper for multimeter probes
COL_SPACING_MM = 11.0
MARGIN_MM = 9.0
SHAPE_NAMES = ["circle", "square", "diamond", "triangle"]

# Board is confirmed a plain 70x100mm rectangle (see mill.tcl/README) -
# checked at generation time that the coupon fits inside it, since the
# real jig (enclosure/mill_jig.scad) is sized for exactly that blank.
BOARD_W_MM, BOARD_H_MM = 70.0, 100.0

# --- Row labels: simple 7-segment-style digit engraving --------------------
# Single shallow stroke per segment, not the 3-pass isolation treatment -
# labels are informational engraving, not an electrical feature, so their
# own cut quality isn't part of what this coupon is testing. Always cut at
# LABEL_FEED regardless of the row's own test feed, so label legibility
# doesn't depend on the thing being tested.
_SEGMENTS = {
    "a": ((0, 1), (1, 1)), "b": ((1, 1), (1, 0.5)), "c": ((1, 0.5), (1, 0)),
    "d": ((0, 0), (1, 0)), "e": ((0, 0.5), (0, 0)), "f": ((0, 1), (0, 0.5)),
    "g": ((0, 0.5), (1, 0.5)),
}
_DIGITS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}
LABEL_HEIGHT_MM = 4.0
LABEL_DIGIT_WIDTH_MM = LABEL_HEIGHT_MM * 0.55
LABEL_DIGIT_GAP_MM = LABEL_HEIGHT_MM * 0.18
LABEL_FEED = 60  # mm/min - fixed, independent of the row's own test feed
LABEL_COL_WIDTH_MM = 16.5  # space reserved to the left of the shape columns
# Same edge-to-edge gap as between shape columns (COL_SPACING_MM minus one
# pad width), so the label reads as just another evenly-spaced column
# instead of being crammed against the first shape.
LABEL_TO_SHAPE_GAP_MM = COL_SPACING_MM - PAD_SIZE_MM
LABEL_RIGHT_X_MM = MARGIN_MM + LABEL_COL_WIDTH_MM - LABEL_TO_SHAPE_GAP_MM


def label_text_width(text):
    n = len(text)
    return n * LABEL_DIGIT_WIDTH_MM + (n - 1) * LABEL_DIGIT_GAP_MM


def label_paths(text, right_x, y):
    """Line segments (open paths) engraving `text` (digits only) with its
    bottom-RIGHT corner at (right_x,y), each digit LABEL_HEIGHT_MM tall.
    Right-aligned rather than left-aligned so every row's last digit lines
    up in the same column regardless of how many digits that row's feed
    rate has (80 vs 300, say) - reads more naturally as a column of
    numbers than left-aligned would."""
    paths = []
    cx = right_x - label_text_width(text)
    for ch in text:
        for seg_name in _DIGITS[ch]:
            (x0, y0), (x1, y1) = _SEGMENTS[seg_name]
            paths.append([
                (cx + x0 * LABEL_DIGIT_WIDTH_MM, y + y0 * LABEL_HEIGHT_MM),
                (cx + x1 * LABEL_DIGIT_WIDTH_MM, y + y1 * LABEL_HEIGHT_MM),
            ])
        cx += LABEL_DIGIT_WIDTH_MM + LABEL_DIGIT_GAP_MM
    return paths


def shape_at(name, cx, cy):
    """One bare test polygon (before isolation offsetting), centered at
    (cx,cy) - see module docstring for what each shape is meant to catch."""
    s = PAD_SIZE_MM
    if name == "circle":
        return Point(cx, cy).buffer(s / 2, quad_segs=32)
    if name == "square":
        return box(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2)
    if name == "diamond":
        return affinity.rotate(box(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2),
                                45, origin=(cx, cy))
    if name == "triangle":
        # Right isoceles triangle: right angle at the shape's own
        # bottom-left corner, legs of length s along +X/+Y, so the other
        # two vertices each have a genuine 45-degree interior angle.
        x0, y0 = cx - s / 2, cy - s / 2
        return Polygon([(x0, y0), (x0 + s, y0), (x0, y0 + s)])
    raise ValueError(name)


def channel_paths_for(base_poly):
    """3 concentric offset rings around one bare shape - channel_paths()'s
    own recipe in custom_isolate.py, but starting from a plain polygon
    instead of the real design's copper polygon (a stress-test coupon has
    no existing design, just solid copper stock everywhere)."""
    return [list(base_poly.buffer(r, join_style="round", quad_segs=16).exterior.coords)
            for r in offset_radii()]


def build_plan():
    """One shared list of (kind, coords, feed) tuples - 'kind' is "label"
    or one of SHAPE_NAMES - consumed by both write_gcode() and
    render_preview(), so the preview always shows exactly what the G-code
    actually contains instead of re-parsing G-code text back into shapes
    (fragile, and exactly the kind of thing this whole investigation has
    repeatedly found bugs in for OTHER tools - no reason to reinvent that
    risk here). Returns (plan, coupon_w, coupon_h)."""
    col_x = [MARGIN_MM + LABEL_COL_WIDTH_MM + j * COL_SPACING_MM for j in range(len(SHAPE_NAMES))]
    coupon_w = col_x[-1] + MARGIN_MM
    coupon_h = MARGIN_MM * 2 + (len(FEED_RATES) - 1) * ROW_SPACING_MM
    assert coupon_w <= BOARD_W_MM and coupon_h <= BOARD_H_MM, (
        f"coupon {coupon_w:.0f}x{coupon_h:.0f}mm doesn't fit the "
        f"{BOARD_W_MM:.0f}x{BOARD_H_MM:.0f}mm blank")

    plan = []
    for i, feed in enumerate(FEED_RATES):
        cy = MARGIN_MM + i * ROW_SPACING_MM
        for coords in label_paths(str(feed), LABEL_RIGHT_X_MM, cy - LABEL_HEIGHT_MM / 2):
            plan.append(("label", coords, LABEL_FEED))
        for name, cx in zip(SHAPE_NAMES, col_x):
            for coords in channel_paths_for(shape_at(name, cx, cy)):
                plan.append((name, coords, feed))
    return plan, coupon_w, coupon_h


def write_gcode(plan, out_path):
    lines = [
        "( Feed-rate calibration coupon - see feedrate_stresstest.py )",
        "( Cut on SCRAP copper-clad stock, not the real board. )",
        "( 4 isolated pad shapes per row (circle/square/diamond/triangle), )",
        "( each row engraved with its own feed rate and cut at that feed; )",
        "( Z-plunge feed fixed at %gmm/min throughout - only XY feed varies. )" % PLUNGE_FEED,
    ] + [f"( row {i + 1} (Y={MARGIN_MM + i * ROW_SPACING_MM:.0f}mm): feed={f}mm/min )"
         for i, f in enumerate(FEED_RATES)] + [
        "G94", "G21", "G90", f"G00 Z{Z_SAFE:.5f}", f"M03 S{SPINDLE_SPEED}",
    ]
    prev_kind = None
    for kind, coords, feed in plan:
        if kind != prev_kind:
            lines.append(f"( {kind} )")
            prev_kind = kind
        x0, y0 = coords[0]
        lines.append(f"G00 X{x0:.5f} Y{y0:.5f}")
        lines.append(f"G01 Z{Z_CUT:.5f} F{PLUNGE_FEED}")
        for x, y in coords[1:]:
            lines.append(f"G01 X{x:.5f} Y{y:.5f} F{feed}")
        lines.append(f"G00 Z{Z_SAFE:.5f}")
    lines += ["M05", "M2"]
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out_path}")


def render_preview(plan, coupon_w, coupon_h, png_path, px_per_mm=16, margin_px=20):
    """True-scale preview PNG, drawn directly from the same plan the
    G-code comes from - see build_plan()'s own docstring for why."""
    from PIL import Image, ImageDraw
    w = int(BOARD_W_MM * px_per_mm) + 2 * margin_px
    h = int(BOARD_H_MM * px_per_mm) + 2 * margin_px
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([margin_px, margin_px,
                    margin_px + BOARD_W_MM * px_per_mm, margin_px + BOARD_H_MM * px_per_mm],
                   outline=(150, 150, 150), width=2)

    def to_px(x, y):
        return (margin_px + x * px_per_mm, margin_px + (BOARD_H_MM - y) * px_per_mm)

    for kind, coords, _feed in plan:
        color = (30, 100, 220) if kind == "label" else (255, 140, 0)
        pts = [to_px(x, y) for x, y in coords]
        draw.line(pts, fill=color, width=2)
    img.save(png_path)
    print(f"wrote {png_path}")


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "feedrate_stresstest.nc"
    preview_path = None
    if "--preview" in sys.argv:
        preview_path = sys.argv[sys.argv.index("--preview") + 1]

    plan, coupon_w, coupon_h = build_plan()
    write_gcode(plan, out_path)
    print(f"feed rates tested (row 1 = Y={MARGIN_MM:.0f}mm, closest to origin): "
          + ", ".join(f"row {i + 1}={f}mm/min" for i, f in enumerate(FEED_RATES)))
    print(f"coupon size needed: {coupon_w:.0f} x {coupon_h:.0f}mm "
          f"(fits the {BOARD_W_MM:.0f}x{BOARD_H_MM:.0f}mm blank)")
    if preview_path:
        render_preview(plan, coupon_w, coupon_h, preview_path)


if __name__ == "__main__":
    main()
