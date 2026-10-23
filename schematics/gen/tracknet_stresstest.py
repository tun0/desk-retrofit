#!/usr/bin/env python3
"""Generate a second, complementary feed-rate calibration coupon:
feedrate_stresstest.py tests isolated single-pad shapes (does a channel
correctly separate ONE feature's own corners from surrounding copper);
this one tests whether the channel correctly separates NEIGHBOURING
copper features from EACH OTHER at the board's own real minimum spacing,
which is the failure mode that actually matters for signal routing.

Each row is one "network": 3 parallel signal-width tracks (top/mid/bot),
spaced at NET_GAP_MM (the board's own real DRC minimum copper clearance,
schematics/desk.kicad_pro - not an arbitrary number), running side by side
for NET_RUN_LENGTH_MM, then diverging at BOTH ends, mirror-symmetric about
the row's own centre - middle track stays straight, top bends
NET_TOP_ANGLE_DEG, bottom bends NET_BOT_ANGLE_DEG, each end terminated with
its own round pin. A single row this way exercises both real risks
together: sustained tight-clearance channel-following, and both corner
angles, TWICE each (once per side) - and every track gets a proper round
pin on each end instead of one bare cut end, which is both easier to probe
and gives twice as many physical contact points for the same electrical
pairs.

A 4th, straight track (pwr) runs outside "bot" at the board's real power-
net trace width (POWER_TRACK_WIDTH_MM=1.0mm vs the others' 0.5mm), still
at the same NET_GAP_MM clearance - representative of the real board's
K1/K2/D2 cluster, where a power trace is already routed at minimum
clearance next to a signal trace. Tests whether the extra copper/thermal
mass of a wider trace changes isolation reliability at the same gap.

The middle (green) net's own right-side pin additionally forks - a "<"
opening rightward - into 2 further pins, adding a genuine 3-way copper
junction to the coupon: a concave notch between the two fork arms, a
shape category none of the plain 2-segment bends elsewhere exercise (the
channel has to follow INTO a notch there, not just around a convex
corner). The fork is electrically the same net as the rest of "mid", not
a new pair to test - it's testing junction geometry, not isolation
between nets.

After cutting, check each row with a multimeter across all 6 pairs among
top/mid/bot/pwr (either side's pins will do, each is one net): any
continuity means that feed rate did NOT isolate the parallel run or a
corner reliably. The fastest row with every pair open is the feed rate to
use for real production - same objective, exact pass/fail methodology as
feedrate_stresstest.py, cross-check the two results against each other
since they're independent test geometries.

Each row also gets one thermal-relief pad (blue) to its right: a pad that
is DELIBERATELY still connected to the surrounding copper, through
THERMAL_N_SPOKES narrow spokes across a THERMAL_GAP_MM gap - the board's
own real zone settings (schematics/gen/reroute_pcb.py's ZONE_THERMAL_GAP_MM/
thermal_bridge_width), not arbitrary. Every other shape on this coupon
tests isolation (continuity = fail); this one tests the opposite failure
mode - continuity = PASS here, since the mill is meant to leave the spokes
intact. Probe the pad against any other bare copper on the coupon (a small
engraved ring elsewhere marks a reference point) - open circuit means the
mill cut through a spoke it shouldn't have.

Cut this on its own scrap offcut of copper-clad FR4, NOT the real board
blank and NOT the same piece as feedrate_stresstest.py's coupon - sized to
fit within the real 70x100mm blank (checked at generation time).

Usage: python3 tracknet_stresstest.py <out.nc> [--preview <out.png>]
Then: python3 snapmaker_header.py <out.nc> <out.snapmaker.nc>
(raw G-code crashes the Snapmaker touchscreen - see snapmaker_header.py's
own docstring - the same post-processing every other output here needs.)
"""
import math
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from custom_isolate import offset_radii, pocket_paths, Z_SAFE, Z_CUT, SPINDLE_SPEED

# Same sweep as feedrate_stresstest.py - cross-checking the two coupons
# against each other only makes sense if they test the same speeds.
FEED_RATES = [80, 120, 160, 200, 250, 300, 350, 400]

PLUNGE_FEED = 40  # mm/min - fixed and conservative; see module docstring

# --- The network geometry ---------------------------------------------
# NET_TRACK_WIDTH_MM/NET_GAP_MM are the board's own real values (schematics/
# desk.kicad_pro: min_track_width 0.5, min_clearance 0.4), not arbitrary -
# this is deliberately the tightest spacing actually present in production,
# since that's the case most likely to reveal a feed rate that's too fast.
NET_TRACK_WIDTH_MM = 0.5
NET_GAP_MM = 0.4
NET_PITCH_MM = NET_TRACK_WIDTH_MM + NET_GAP_MM  # centre-to-centre
NET_PIN_DIA_MM = 1.2  # matches the real via diameter; big enough to probe
NET_RUN_LENGTH_MM = 8.0  # parallel run at minimum clearance before the bend
NET_BRANCH_LENGTH_MM = 3.0  # length of each diverging stub past the bend
NET_STUB_LENGTH_MM = 3.5  # middle track's own continuation past the bend
NET_TOP_ANGLE_DEG = 45  # top track's bend, measured from horizontal
NET_BOT_ANGLE_DEG = 90  # bottom track's bend, measured from horizontal

# The middle (green) net forks at its own right-side pin into 2 further
# pins - a "<" opening rightward, vertex at that pin. Adds a genuine
# 3-way copper junction (a concave notch between the two arms) to the
# coupon, a shape category the plain bends elsewhere don't exercise.
NET_FORK_LENGTH_MM = 3.0
NET_FORK_ANGLE_DEG = 30  # each arm's angle from horizontal, +/- this

# A 4th, straight parallel track outside "bot", at the board's real power-
# net trace width (schematics/gen/reroute_pcb.py: POWER_TRACK_WIDTH_MM) -
# still at NET_GAP_MM clearance, since clearance is edge-to-edge regardless
# of width. Tests whether a wider trace's extra copper/thermal mass changes
# isolation reliability at the same minimum gap - representative of the
# real board's K1/K2/D2 cluster, already routed at 0.4mm clearance next to
# a 0.5mm signal trace.
POWER_TRACK_WIDTH_MM = 1.0
PWR_PITCH_MM = NET_TRACK_WIDTH_MM / 2 + NET_GAP_MM + POWER_TRACK_WIDTH_MM / 2
# pwr has no bend of its own (unlike top/bot, whose bends only work because
# they're the outermost lane, moving further away from the pack - a 4th
# lane outside bot would get crossed by bot's own 90-degree dive, which
# turns vertical exactly at bend_l/bend_r). Instead pwr's straight run
# stops PWR_INSET_MM short of bend_l/bend_r on each side, staying clear of
# where any bend actually happens - still a full sustained-proximity test,
# just slightly shorter than the other 3 lanes' run.
PWR_INSET_MM = 1.5

ROW_SPACING_MM = 9.5
MARGIN_MM = 9.0
LABEL_COL_WIDTH_MM = 16.5

# --- Thermal-relief pad -------------------------------------------------
# THERMAL_GAP_MM/THERMAL_BRIDGE_WIDTH_MM are the board's own real zone
# settings (schematics/gen/reroute_pcb.py: ZONE_THERMAL_GAP_MM=0.3,
# thermal_bridge_width=0.5), not arbitrary - same reasoning as NET_GAP_MM.
THERMAL_PAD_R_MM = 1.5  # relief pad radius (3mm dia, typical via/pad size)
THERMAL_GAP_MM = 0.3
THERMAL_BRIDGE_WIDTH_MM = 0.5
THERMAL_N_SPOKES = 4
THERMAL_REF_MARKER_R_MM = 1.0  # shallow reference-marker engraving only
THERMAL_REF_GAP_MM = 2.0  # gap from the relief pad's outer edge to the marker
THERMAL_TO_NET_GAP_MM = 4.0  # gap from the tracknet's own right edge

BOARD_W_MM, BOARD_H_MM = 70.0, 100.0

# --- Row labels: identical scheme to feedrate_stresstest.py ----------------
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
LABEL_FEED = 60
NET_X0_MM = MARGIN_MM + LABEL_COL_WIDTH_MM
LABEL_TO_NET_GAP_MM = 8.0  # same order as the network's own tightest gaps
LABEL_RIGHT_X_MM = NET_X0_MM - LABEL_TO_NET_GAP_MM


def label_text_width(text):
    n = len(text)
    return n * LABEL_DIGIT_WIDTH_MM + (n - 1) * LABEL_DIGIT_GAP_MM


def label_paths(text, right_x, y):
    """Right-aligned digit engraving - see feedrate_stresstest.py's own
    label_paths() for why right-aligned."""
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


def _wing_end(bend_x, y_lvl, length, angle_deg, mirror):
    """End point of one diverging stub, `length` from (bend_x,y_lvl) at
    `angle_deg` from horizontal. mirror=True reflects the X-component only
    (angle stays measured the same way), which is exactly what the left
    side of a mirror-symmetric wing needs - see network_at()."""
    ang = math.radians(angle_deg)
    dx = length * math.cos(ang) * (-1 if mirror else 1)
    dy = length * math.sin(ang)
    return (bend_x + dx, y_lvl + dy)


def network_at(cx, cy):
    """4 separate net shapes (top/mid/bot/pwr), each a track with a round
    pin at BOTH ends, mirror-symmetric about x=cx (pwr is straight, so it's
    trivially already symmetric) - see module docstring for what this
    pattern tests and why both ends diverge identically. The middle net
    additionally forks at its own right-side pin into 2 more pins (see
    NET_FORK_LENGTH_MM/NET_FORK_ANGLE_DEG)."""
    bend_l = cx - NET_RUN_LENGTH_MM / 2
    bend_r = cx + NET_RUN_LENGTH_MM / 2
    y_top, y_mid, y_bot = cy + NET_PITCH_MM, cy, cy - NET_PITCH_MM
    y_pwr = y_bot - PWR_PITCH_MM

    top_l = _wing_end(bend_l, y_top, NET_BRANCH_LENGTH_MM, NET_TOP_ANGLE_DEG, mirror=True)
    top_r = _wing_end(bend_r, y_top, NET_BRANCH_LENGTH_MM, NET_TOP_ANGLE_DEG, mirror=False)
    top_lines = [LineString([top_l, (bend_l, y_top), (bend_r, y_top), top_r])]
    top_ends = [top_l, top_r]

    mid_l = (bend_l - NET_STUB_LENGTH_MM, y_mid)
    mid_r = (bend_r + NET_STUB_LENGTH_MM, y_mid)
    fork_up = _wing_end(mid_r[0], mid_r[1], NET_FORK_LENGTH_MM, NET_FORK_ANGLE_DEG, mirror=False)
    fork_down = _wing_end(mid_r[0], mid_r[1], NET_FORK_LENGTH_MM, -NET_FORK_ANGLE_DEG, mirror=False)
    mid_lines = [LineString([mid_l, mid_r]), LineString([mid_r, fork_up]), LineString([mid_r, fork_down])]
    mid_ends = [mid_l, mid_r, fork_up, fork_down]

    bot_l = _wing_end(bend_l, y_bot, NET_BRANCH_LENGTH_MM, -NET_BOT_ANGLE_DEG, mirror=True)
    bot_r = _wing_end(bend_r, y_bot, NET_BRANCH_LENGTH_MM, -NET_BOT_ANGLE_DEG, mirror=False)
    bot_lines = [LineString([bot_l, (bend_l, y_bot), (bend_r, y_bot), bot_r])]
    bot_ends = [bot_l, bot_r]

    pwr_l = (bend_l + PWR_INSET_MM, y_pwr)
    pwr_r = (bend_r - PWR_INSET_MM, y_pwr)
    pwr_lines = [LineString([pwr_l, pwr_r])]
    pwr_ends = [pwr_l, pwr_r]

    nets = []
    for kind, lines, ends, width in [
        ("top", top_lines, top_ends, NET_TRACK_WIDTH_MM),
        ("mid", mid_lines, mid_ends, NET_TRACK_WIDTH_MM),
        ("bot", bot_lines, bot_ends, NET_TRACK_WIDTH_MM),
        ("pwr", pwr_lines, pwr_ends, POWER_TRACK_WIDTH_MM),
    ]:
        track = unary_union([ln.buffer(width / 2, cap_style="round",
                                        join_style="round", quad_segs=16) for ln in lines])
        pins = unary_union([Point(e).buffer(NET_PIN_DIA_MM / 2, quad_segs=16) for e in ends])
        nets.append((kind, unary_union([track, pins])))

    # The whole point of this coupon is 4 genuinely separate copper
    # features at minimum clearance - if the bare (pre-channel) shapes
    # already touch, the test geometry itself is wrong, not the mill.
    for i in range(len(nets)):
        for j in range(i + 1, len(nets)):
            assert not nets[i][1].intersects(nets[j][1]), (
                f"test geometry bug: {nets[i][0]} and {nets[j][0]} nets touch "
                f"before any milling - NET_GAP_MM/lengths need adjusting")
    return nets


# Measured directly off a sample network (cx=cy=0) rather than hand-derived
# from the angles/lengths above - less error-prone, and stays correct if
# those constants change.
_sample_bounds = unary_union([poly for _, poly in network_at(0.0, 0.0)]).bounds
NET_LEFT_MM = -_sample_bounds[0]
NET_DOWN_MM = -_sample_bounds[1]
NET_WIDTH_MM = _sample_bounds[2] - _sample_bounds[0]
NET_UP_MM = _sample_bounds[3]


def thermal_relief_gaps(cx, cy):
    """The THERMAL_N_SPOKES arc-shaped voids to actually mill for one
    thermal-relief pad - NOT a full isolation channel around its perimeter,
    since the pad is deliberately still connected to the surrounding
    copper through that many spokes. See module docstring for the
    inverted (continuity=pass) test this represents."""
    r_out = THERMAL_PAD_R_MM + THERMAL_GAP_MM
    annulus = Point(cx, cy).buffer(r_out, quad_segs=64).difference(
        Point(cx, cy).buffer(THERMAL_PAD_R_MM, quad_segs=64))
    spoke_len = r_out + 0.5  # generous overrun past r_out; the difference
    for i in range(THERMAL_N_SPOKES):  # with annulus clips it anyway
        ang = 360.0 / THERMAL_N_SPOKES * i
        spoke = box(cx, cy - THERMAL_BRIDGE_WIDTH_MM / 2, cx + spoke_len, cy + THERMAL_BRIDGE_WIDTH_MM / 2)
        annulus = annulus.difference(affinity.rotate(spoke, ang, origin=(cx, cy)))
    return list(annulus.geoms) if annulus.geom_type == "MultiPolygon" else [annulus]


def thermal_ref_marker(cx, cy):
    """A shallow, single-pass engraved ring (not milled/isolated) marking
    where to place the multimeter's second probe: anywhere on the coupon's
    general, un-milled background copper - one continuous sheet by design,
    since nothing isolates a row's background from its neighbours'."""
    return [list(Point(cx, cy).buffer(THERMAL_REF_MARKER_R_MM, quad_segs=32).exterior.coords)]


def channel_paths_for(base_poly):
    """3 concentric offset rings around one bare shape - same recipe as
    feedrate_stresstest.py's channel_paths_for() / custom_isolate.py's own
    channel_paths()."""
    return [list(base_poly.buffer(r, join_style="round", quad_segs=16).exterior.coords)
            for r in offset_radii()]


THERMAL_R_OUT_MM = THERMAL_PAD_R_MM + THERMAL_GAP_MM
THERMAL_CX_MM = (NET_X0_MM + NET_WIDTH_MM + THERMAL_TO_NET_GAP_MM + THERMAL_R_OUT_MM)
THERMAL_REF_CX_MM = (THERMAL_CX_MM + THERMAL_R_OUT_MM + THERMAL_REF_GAP_MM + THERMAL_REF_MARKER_R_MM)


def build_plan():
    """One shared list of (kind, coords, feed) tuples consumed by both
    write_gcode() and render_preview() - see feedrate_stresstest.py's own
    build_plan() for why this shape is shared rather than re-derived."""
    row0_cy = MARGIN_MM + NET_DOWN_MM
    coupon_w = THERMAL_REF_CX_MM + THERMAL_REF_MARKER_R_MM + MARGIN_MM
    coupon_h = row0_cy + (len(FEED_RATES) - 1) * ROW_SPACING_MM + NET_UP_MM + MARGIN_MM
    assert coupon_w <= BOARD_W_MM and coupon_h <= BOARD_H_MM, (
        f"coupon {coupon_w:.0f}x{coupon_h:.0f}mm doesn't fit the "
        f"{BOARD_W_MM:.0f}x{BOARD_H_MM:.0f}mm blank")
    assert ROW_SPACING_MM >= NET_UP_MM + NET_DOWN_MM, (
        "ROW_SPACING_MM too small - adjacent rows' networks would overlap")
    assert ROW_SPACING_MM >= 2 * max(THERMAL_R_OUT_MM, THERMAL_REF_MARKER_R_MM), (
        "ROW_SPACING_MM too small - adjacent rows' thermal-relief pads would overlap")

    plan = []
    for i, feed in enumerate(FEED_RATES):
        cy = row0_cy + i * ROW_SPACING_MM
        for coords in label_paths(str(feed), LABEL_RIGHT_X_MM, cy - LABEL_HEIGHT_MM / 2):
            plan.append(("label", coords, LABEL_FEED))
        for kind, poly in network_at(NET_X0_MM + NET_LEFT_MM, cy):
            for coords in channel_paths_for(poly):
                plan.append((kind, coords, feed))
        gaps = thermal_relief_gaps(THERMAL_CX_MM, cy)
        for coords in pocket_paths(gaps):
            plan.append(("thermal", coords, feed))
        for coords in thermal_ref_marker(THERMAL_REF_CX_MM, cy):
            plan.append(("thermal_ref", coords, LABEL_FEED))
    return plan, coupon_w, coupon_h


def write_gcode(plan, out_path):
    lines = [
        "( Track-network calibration coupon - see tracknet_stresstest.py )",
        "( Cut on SCRAP copper-clad stock, not the real board. )",
        "( 4 parallel tracks per row (3 signal + 1 power) at the board's own )",
        "( min clearance, diverging into a 45deg and a 90deg bend, pin at )",
        "( every endpoint; )",
        "( plus one thermal-relief pad per row - continuity=PASS there, )",
        "( unlike every other shape on this coupon (continuity=FAIL). )",
        "( Z-plunge feed fixed at %gmm/min throughout - only XY feed varies. )" % PLUNGE_FEED,
    ] + [f"( row {i + 1}: feed={f}mm/min )" for i, f in enumerate(FEED_RATES)] + [
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


def render_preview(plan, png_path, px_per_mm=16, margin_px=20):
    """True-scale preview PNG, drawn directly from the same plan the
    G-code comes from - see feedrate_stresstest.py's own render_preview()
    for why."""
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

    colors = {"label": (30, 100, 220), "top": (220, 40, 40),
              "mid": (30, 160, 60), "bot": (140, 60, 200), "pwr": (200, 140, 0),
              "thermal": (20, 120, 220), "thermal_ref": (150, 150, 150)}
    for kind, coords, _feed in plan:
        pts = [to_px(x, y) for x, y in coords]
        draw.line(pts, fill=colors[kind], width=2)
    img.save(png_path)
    print(f"wrote {png_path}")


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "tracknet_stresstest.nc"
    preview_path = None
    if "--preview" in sys.argv:
        preview_path = sys.argv[sys.argv.index("--preview") + 1]

    plan, coupon_w, coupon_h = build_plan()
    write_gcode(plan, out_path)
    print(f"feed rates tested (row 1 closest to origin): "
          + ", ".join(f"row {i + 1}={f}mm/min" for i, f in enumerate(FEED_RATES)))
    print(f"coupon size needed: {coupon_w:.1f} x {coupon_h:.1f}mm "
          f"(fits the {BOARD_W_MM:.0f}x{BOARD_H_MM:.0f}mm blank)")
    if preview_path:
        render_preview(plan, preview_path)


if __name__ == "__main__":
    main()
