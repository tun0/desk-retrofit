#!/usr/bin/env python3
"""Confirm, per pixel, whether the actual isolation toolpath cuts through
real copper - not just "is this area white in the KiCad-rendered design",
which is a design-INTENT rendering, not a physical-material one. A raw
copper-clad blank is copper EVERYWHERE before milling; the KiCad zone-fill
render's own "white" areas (keepouts, clearances) are not bare substrate on
the actual blank - they're just areas the FINAL DESIGN doesn't want copper
in, which is only achieved once the mill actually cuts them away. Treating
that design-intent white as if it were already bare (an earlier version of
this script did exactly that) silently invents material removal that never
happened - confirmed as a real, substantive bug, not just a rendering
nitpick (see conversation). The only two things that are ever NOT copper on
the raw blank are drilled holes and space genuinely off the board outline;
everywhere else starts as copper and stays copper unless the real,
post-fix G-code toolpath actually sweeps over it.

Orange = the toolpath passes over a pixel that was copper on the raw blank
         (i.e. not a hole, not off-board) - confirmed real material removal.
Gray   = the toolpath passes over a hole or off-board space - nothing
         physical is being removed here (should be rare/near-zero).
Everything else = untouched: copper color = still copper (whether or not
the final design wanted it there - if the mill didn't cut it, it's still
there), black = drilled hole, a distinct off-board color = genuinely
outside the physical board (determined from the known board_width/
board_height rectangle, not from image content - confirmed KiCad's own
Edge.Cuts SVG export does not reliably fill the whole board interior
opaque, so alpha/color can't be used for this - see conversation).

Two resolutions are rendered for each of the diagnostic/realistic/
connectivity images:
- "detail" (100px/mm): true-scale channel width, used for the optional
  zoomed crop. At full-board scale a true-scale 0.1mm channel is a real,
  measured ~2.4% of the board area (1737mm of toolpath at 0.1mm wide, on a
  7000mm^2 board - see conversation) - accurate, but far too thin to
  survive being viewed/compressed at whole-board size, so at that size it's
  legitimately hard to tell "correct thin channel" from "channel silently
  missing".
- "overview" (~25px/mm, exaggerated minimum line width): a full-board image
  sized for direct viewing with NO further external resizing, where the
  channel is deliberately drawn at least OVERVIEW_MIN_LINE_PX wide even if
  the true tool_dia would round to less at this resolution. This trades
  strict to-scale accuracy for guaranteed visibility of every channel in
  the one image most likely to actually get looked at - the legend says so
  explicitly so it's never mistaken for a to-scale render.

Also writes <output>_connectivity.png and <output>_overview_connectivity.png:
label connected regions of copper actually remaining after the cut (using
the corrected raw-blank-is-copper-everywhere model above, not the design's
own white) and color each electrically-separate island a different color
(main/largest region keeps its real copper color). Same color where you
expect a gap = an unintended short; a different color splitting something
that should be one net = an unintended break.

Usage: python3 verify_isolation.py <copper.svg> <isolation.nc> <tool_dia_mm> <board_width_mm> <board_height_mm> <output.png> [x0 y0 x1 y1]
"""
import re
import sys

import cairosvg
import io
import colorsys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

OFFBOARD_COLOR = (255, 230, 120)


def parse_g1_segments(path):
    """Group consecutive G1 moves into separate point lists, breaking the
    group whenever a G0 move interrupts (rapid travel between disjoint
    isolation loops - joining across it would fabricate a cut that was
    never actually made)."""
    x, y = 0.0, 0.0
    segments = []
    current = []
    for line in open(path):
        s = line.strip()
        is_g0 = re.match(r"^G0?0\b", s)
        is_g1 = re.match(r"^G0?1\b", s)
        if not (is_g0 or is_g1):
            continue
        moved = False
        for axis, val in re.findall(r"([XY])(-?\d+\.?\d*)", s):
            if axis == "X":
                x = float(val)
            else:
                y = float(val)
            moved = True
        if is_g1 and moved:
            current.append((x, y))
        else:
            if len(current) >= 2:
                segments.append(current)
            current = []
    if len(current) >= 2:
        segments.append(current)
    return segments


def render_at(svg_path, segments, tool_dia, board_w, board_h, px_per_mm, min_line_px):
    """Composite the copper SVG and the swept toolpath at one specific
    resolution/line-width floor. Returns (base, on_blank_copper, swept,
    copper_color). Pulled out of main() so the full-board "overview" image
    (sized for direct viewing, guaranteed-visible channel) and the
    high-detail crop (true-scale channel) can each pick their own
    resolution/floor instead of one px_per_mm having to serve both."""
    png_bytes = cairosvg.svg2png(url=svg_path, output_width=None,
                                  scale=px_per_mm * 25.4 / 96)
    # Turns out kicad-cli's Edge.Cuts export does NOT reliably fill the
    # whole board interior opaque - confirmed directly: a point at (35,50)mm,
    # clearly mid-board between two traces, rendered alpha=0, identical to
    # genuinely off-board space (see conversation). Only specific drawn
    # shapes (keepouts, pads) get an explicit opaque fill; a plain gap
    # between copper features that isn't a named shape stays transparent
    # regardless of Edge.Cuts. So alpha can't be used to tell "off-board"
    # from "on-board bare" at all - composite transparency straight to
    # white (bare substrate is the correct default for "nothing drawn
    # here") and determine off-board a completely different way below.
    raw = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    bg = Image.new("RGB", raw.size, (255, 255, 255))
    bg.paste(raw, mask=raw.split()[3])
    board_only = np.array(bg)

    # kicad-cli's SVG export (--page-size-mode 2 --exclude-drawing-sheet) is
    # cropped tight to the board's own silhouette, with NO margin beyond it -
    # confirmed directly (sampling pixels at the array edge landed exactly on
    # the board boundary, never in true off-board space). That means every
    # image built straight from this render has literally no pixel that's
    # ever off-board: the board edge is never an explicit boundary, it's just
    # wherever the array happens to stop - so the physical edge/corner has no
    # visible representation at all (see conversation - this is the actual
    # cause of "borders/corners aren't properly represented", not a color
    # choice). Pad an explicit margin of off-board space on all four sides so
    # the true edge becomes a real, visible boundary instead of an implicit
    # one.
    MARGIN_MM = 3
    margin_px = round(MARGIN_MM * px_per_mm)
    base = np.full((board_only.shape[0] + 2 * margin_px, board_only.shape[1] + 2 * margin_px, 3),
                    OFFBOARD_COLOR, dtype=np.uint8)
    base[margin_px:margin_px + board_only.shape[0], margin_px:margin_px + board_only.shape[1]] = board_only

    # Off-board determined directly from known board geometry, not image
    # content: confirmed earlier in this conversation (and by the user) the
    # board is a plain rectangle with sharp corners - no rounding to model.
    # A pixel is off-board if its board-mm coordinate falls outside
    # [0,board_w] x [0,board_h], full stop. Origin is shifted by margin_px
    # since (0,0) in board mm now sits margin_px pixels in from the padded
    # canvas edge, not at the canvas edge itself.
    yy, xx = np.mgrid[0:base.shape[0], 0:base.shape[1]]
    x_mm = (xx - margin_px) / px_per_mm
    y_mm = board_h - (yy - margin_px) / px_per_mm
    is_offboard = (x_mm < 0) | (x_mm > board_w) | (y_mm < 0) | (y_mm > board_h)

    # Ground truth for "is this pixel copper": copper fill (colored),
    # drilled holes (black), on-board-but-bare substrate (white, including
    # the composited-transparent areas above), and off-board (computed from
    # geometry, not image content). Anything that isn't close to white,
    # close to black, or off-board is copper, regardless of which of the
    # two layer colors (red for F.Cu, blue for B.Cu) it is - this makes the
    # same check work for both layers.
    is_white = np.all(base > 240, axis=-1)
    is_black = np.all(base < 30, axis=-1)
    # Design-intent copper (matches the KiCad render's own copper color) -
    # kept only for sampling what color real copper actually is (legend,
    # below). NOT used to decide what's physically copper on the blank -
    # see on_blank_copper.
    is_copper = ~is_white & ~is_black & ~is_offboard
    if is_copper.any():
        copper_color = tuple(int(c) for c in np.median(base[is_copper], axis=0))
    else:
        copper_color = (200, 52, 52)
    base[is_offboard] = OFFBOARD_COLOR

    # What's actually copper on the raw blank, before any milling: anything
    # that isn't a drilled hole and isn't off the physical board. This
    # deliberately includes the design's own "white" clearance/keepout
    # areas - those are design intent, not a property of the raw material.
    on_blank_copper = ~is_black & ~is_offboard

    # Rasterize the actual toolpath as a thick line at the real tool
    # diameter - not a shapely buffer-and-Path-with-holes construction.
    # This IS what removing material with a round bit actually looks like:
    # a swept band along the path, correctly self-uniting at corners via
    # PIL's line joints without needing any polygon/hole bookkeeping.
    # min_line_px guarantees the channel survives at low resolutions
    # (an overview render at ~25px/mm would round 0.1mm down to 2-3px on
    # its own) - callers that need strict to-scale width instead pass
    # min_line_px=1, which never widens anything a real round() wouldn't.
    swept_mask = Image.new("L", (base.shape[1], base.shape[0]), 0)
    draw = ImageDraw.Draw(swept_mask)
    tool_px = max(min_line_px, round(tool_dia * px_per_mm))
    for seg in segments:
        pts = [(x * px_per_mm + margin_px, (board_h - y) * px_per_mm + margin_px) for x, y in seg]
        draw.line(pts, fill=255, width=tool_px, joint="curve")
        r = tool_px / 2.0
        for x, y in pts:
            draw.ellipse([x - r, y - r, x + r, y + r], fill=255)
    swept = np.array(swept_mask) > 0

    return base, on_blank_copper, swept, copper_color, margin_px


def compose_diagnostic(base, on_blank_copper, swept):
    really_removed = swept & on_blank_copper
    harmless_travel = swept & ~on_blank_copper
    out = base.copy()
    out[really_removed] = [255, 140, 0]     # orange
    out[harmless_travel] = [160, 160, 160]  # gray
    return out, really_removed


def compose_realistic(base, on_blank_copper, really_removed, copper_color):
    # A literal "what will the board actually look like" render: the whole
    # raw-copper area starts filled with the real copper color (not the
    # design's own white for areas it merely intends to be clear), and only
    # what the toolpath actually sweeps turns to bare white - matching how
    # milling physically works, not how the zone-fill was intended to look.
    realistic = base.copy()
    realistic[on_blank_copper] = copper_color
    realistic[really_removed] = [255, 255, 255]
    return realistic


def add_legend(img_array, entries, px_per_mm, notes=None):
    img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(img)
    sw = max(20, px_per_mm // 4)
    pad = sw // 2
    y = pad
    for color, label in entries:
        draw.rectangle([pad, y, pad + sw, y + sw], fill=color, outline=(0, 0, 0))
        draw.text((pad + sw + pad, y + sw // 4), label, fill=(0, 0, 0))
        y += sw + pad
    for note in notes or []:
        draw.text((pad, y), note, fill=(0, 0, 0))
        y += sw
    return np.array(img)


def compute_connectivity(base, on_blank_copper, swept, px_per_mm):
    """Isolation routing only cuts a thin channel, not the whole clearance
    area, so most of what's "no copper" in the design will physically stay
    copper-clad on the real board - NOT bare substrate like a fab-etched
    board. That's normal, but it means "is this milled" is the wrong
    question; what actually matters electrically is whether the channel
    forms a complete closed loop that disconnects it from copper it's
    supposed to be isolated from - a connectivity question, not a
    material-removal one (see conversation). Uses on_blank_copper, not the
    design's own white - the corrected model where a keepout's leftover
    copper still counts as "remaining" since the mill never actually
    removed it. 8-connectivity (count diagonal touches) errs toward
    flagging borderline single-pixel corner-touches as still-connected,
    rather than risk missing a real one."""
    remaining_copper = on_blank_copper & ~swept
    structure = np.ones((3, 3), dtype=int)
    labels, n = ndimage.label(remaining_copper, structure=structure)
    conn_out = np.full_like(base, 255)
    # Off-board space, drilled holes, and actually-milled-bare copper all
    # default to the same plain white above - which erases the board
    # outline entirely, exactly where it matters most (corners, edges near
    # mounting holes). Mark the first two explicitly so white means ONLY
    # "milled bare", matching the legend used in the realistic/diagnostic
    # images instead of silently disagreeing with it.
    is_offboard = np.all(base == OFFBOARD_COLOR, axis=-1)
    is_black = np.all(base < 30, axis=-1)
    conn_out[is_offboard] = OFFBOARD_COLOR
    conn_out[is_black] = [0, 0, 0]
    real_component_count = 0
    if n > 0:
        sizes = ndimage.sum(remaining_copper, labels, index=range(1, n + 1))
        main_label = int(np.argmax(sizes)) + 1
        conn_out[labels == main_label] = base[labels == main_label]
        # A raster boundary between two colors antialiases into a blend, and
        # that blend is neither close-to-white nor close-to-black - is_copper
        # picks some of those blended edge pixels up as "copper", leaving
        # tiny (sub-0.2mm) leftover specks right where the toolpath meets a
        # real copper edge. Confirmed directly, not assumed: checked actual
        # component sizes at exactly this kind of location and found a
        # cluster of 6-81px fragments (px_per_mm=60, so under 0.2mm) with
        # nothing between them and genuine features (smallest real hole
        # here is 0.6mm dia, ~1000px) - see conversation. Below this
        # threshold a component is rendering noise, not a real isolated
        # copper island, and gets excluded from distinct-color highlighting
        # rather than manufacturing a false "disconnection" out of it.
        min_diameter_mm = 0.25
        min_area_px = 3.14159 * (min_diameter_mm / 2 * px_per_mm) ** 2
        other_labels = [i for i in range(1, n + 1)
                        if i != main_label and sizes[i - 1] >= min_area_px]
        for i, lbl in enumerate(other_labels):
            hue = (i * 0.6180339887) % 1.0  # golden-ratio spacing - keeps
                                              # adjacent islands visually
                                              # distinct even with many of them
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.85, 0.95)]
            conn_out[labels == lbl] = [r, g, b]
        real_component_count = len(other_labels)
    noise_count = n - 1 - real_component_count if n else 0
    return conn_out, real_component_count, noise_count


def legend_entries_for(copper_color):
    return [
        ((255, 255, 255), "bare - actually milled away (nothing else is bare)"),
        ((0, 0, 0), "drilled mounting hole (NPTH)"),
        (OFFBOARD_COLOR, "off the physical board entirely"),
        (copper_color, "copper (design wants it or not - the mill never touched it)"),
    ]


def main():
    svg_path, nc_path, tool_dia_s, board_w_s, board_h_s, out_path = sys.argv[1:7]
    tool_dia = float(tool_dia_s)
    board_w = float(board_w_s)
    board_h = float(board_h_s)

    segments = parse_g1_segments(nc_path)
    if not segments:
        print("No G1 cutting segments found - nothing to check.", file=sys.stderr)
        sys.exit(1)

    # --- Detail resolution: true-scale channel width, used for the
    # diagnostic/connectivity images and the optional zoomed crop. High
    # enough that a 0.1mm toolpath line is still legible when cropped in
    # tight (see conversation) - but at full-board size this resolution
    # alone is NOT relied on for legibility any more; that's what the
    # overview render below is for.
    DETAIL_PX_PER_MM = 100
    base, on_blank_copper, swept, copper_color, margin_px = render_at(
        svg_path, segments, tool_dia, board_w, board_h, DETAIL_PX_PER_MM, min_line_px=1)
    out, really_removed = compose_diagnostic(base, on_blank_copper, swept)
    realistic = compose_realistic(base, on_blank_copper, really_removed, copper_color)
    legend_entries = legend_entries_for(copper_color)

    Image.fromarray(out).save(out_path)
    realistic_path = out_path.rsplit(".", 1)[0] + "_realistic.png"
    Image.fromarray(add_legend(realistic, legend_entries, DETAIL_PX_PER_MM)).save(realistic_path)
    print(f"wrote {realistic_path}")

    total_swept_px = int(swept.sum())
    removed_px = int(really_removed.sum())
    pct = 100 * removed_px / total_swept_px if total_swept_px else 0.0
    print(f"wrote {out_path}")
    print(f"toolpath pixels actually removing raw-blank copper: {removed_px}/{total_swept_px} ({pct:.1f}%)")

    conn_out, real_component_count, noise_count = compute_connectivity(
        base, on_blank_copper, swept, DETAIL_PX_PER_MM)
    conn_path = out_path.rsplit(".", 1)[0] + "_connectivity.png"
    Image.fromarray(conn_out).save(conn_path)
    print(f"wrote {conn_path} ({real_component_count} isolated copper "
          f"regions found besides the main one, {noise_count} "
          f"sub-0.25mm rendering-noise fragments excluded)")

    # Optional zoomed crop (mm, board coordinates: x0 y0 x1 y1) - a
    # dedicated close-up on a specific area (e.g. a corner), at true scale.
    if len(sys.argv) == 11:
        x0, y0, x1, y1 = (float(v) for v in sys.argv[7:11])
        px0, px1 = sorted([int(x0 * DETAIL_PX_PER_MM) + margin_px, int(x1 * DETAIL_PX_PER_MM) + margin_px])
        py0, py1 = sorted([int((board_h - y1) * DETAIL_PX_PER_MM) + margin_px, int((board_h - y0) * DETAIL_PX_PER_MM) + margin_px])
        crop_path = out_path.rsplit(".", 1)[0] + "_crop.png"
        Image.fromarray(out[py0:py1, px0:px1]).save(crop_path)
        print(f"wrote {crop_path}")
        realistic_crop_path = realistic_path.rsplit(".", 1)[0] + "_crop.png"
        Image.fromarray(add_legend(realistic[py0:py1, px0:px1], legend_entries, DETAIL_PX_PER_MM)).save(realistic_crop_path)
        print(f"wrote {realistic_crop_path}")
        conn_crop_path = conn_path.rsplit(".", 1)[0] + "_crop.png"
        Image.fromarray(conn_out[py0:py1, px0:px1]).save(conn_crop_path)
        print(f"wrote {conn_crop_path}")

    # --- Overview resolution: the whole board, sized so it's actually
    # viewable as delivered with NO further external downscaling needed -
    # a real risk at DETAIL_PX_PER_MM (6998x10000), where a naive resize
    # for display silently averages a true-scale 0.1mm channel away to
    # nothing (see conversation: the user correctly flagged the full-board
    # realistic render as looking like solid copper with "way too little
    # white", not because the channel was missing, but because it's
    # genuinely only ~2.4% of the board area at true scale - confirmed
    # directly: 1737mm/1693mm of toolpath at 0.1mm wide, on a 7000mm^2
    # board).
    #
    # Two lower-resolution approaches were tried and both FAILED, for two
    # different reasons - confirmed directly, not assumed:
    # 1. Re-rasterizing at 25px/mm: the image VIEWER itself further shrinks
    #    anything over ~2000px on its long side (observed: 1899x2650 got
    #    displayed at 1433x2000), and that second, invisible resize washed
    #    the channel out - a raw nearest-neighbor crop of the same array
    #    showed full coverage the shrunk-for-display version didn't.
    # 2. Re-rasterizing at 18px/mm (to dodge the viewer's own resize):
    #    STILL lost long diagonal traces, even with no further resize at
    #    all - confirmed by reading the saved file directly. PIL's own
    #    line-drawing introduces its own gaps/aliasing at that low a
    #    resolution, independent of any later display shrinking.
    # The only approach that's actually been confirmed correct is the
    # DETAIL_PX_PER_MM=100 render above (verified pixel-for-pixel against
    # the design SVG). So: downsample THAT proven-correct array instead of
    # re-deriving a new one at low resolution. Ordinary resizing would
    # still average a thin channel away, so `swept` specifically is
    # downsampled with an "any coverage survives" rule (resize the 0/255
    # mask, then keep any pixel that comes out above zero) - a single lit
    # source pixel anywhere in a block is enough to light the corresponding
    # output pixel, which is exactly the "don't let a thin line vanish"
    # property normal resizing doesn't have.
    def downsample_any(mask, new_w, new_h):
        small = Image.fromarray((mask.astype(np.uint8) * 255)).resize((new_w, new_h), Image.BILINEAR)
        return np.array(small) > 0

    def downsample_majority(mask, new_w, new_h):
        small = Image.fromarray((mask.astype(np.uint8) * 255)).resize((new_w, new_h), Image.BILINEAR)
        return np.array(small) >= 128

    TARGET_LONG_SIDE_PX = 1900
    scale = TARGET_LONG_SIDE_PX / max(base.shape[0], base.shape[1])
    new_w, new_h = round(base.shape[1] * scale), round(base.shape[0] * scale)
    OVERVIEW_PX_PER_MM = DETAIL_PX_PER_MM * scale

    obase = np.array(Image.fromarray(base).resize((new_w, new_h), Image.LANCZOS))
    oon_blank_copper = downsample_majority(on_blank_copper, new_w, new_h)
    oswept = downsample_any(swept, new_w, new_h)
    _, orr = compose_diagnostic(obase, oon_blank_copper, oswept)
    orealistic = compose_realistic(obase, oon_blank_copper, orr, copper_color)
    onotes = ["channel drawn with a minimum-visibility floor - not to scale, see the crop for true scale"]
    overview_realistic_path = out_path.rsplit(".", 1)[0] + "_overview_realistic.png"
    Image.fromarray(add_legend(orealistic, legend_entries_for(copper_color), round(OVERVIEW_PX_PER_MM), onotes)).save(overview_realistic_path)
    print(f"wrote {overview_realistic_path}")

    # NOT authoritative for connectivity: downsampling can still merge
    # features that are genuinely separate at true scale, overcounting or
    # undercounting isolated islands. Kept only as a visual "does the
    # overall isolation pattern look right" check; the detail connectivity
    # image above is the one to trust for an actual loop-closure/short
    # answer.
    oconn_out, oreal_component_count, onoise_count = compute_connectivity(
        obase, oon_blank_copper, oswept, OVERVIEW_PX_PER_MM)
    oconn_img = Image.fromarray(oconn_out)
    ImageDraw.Draw(oconn_img).text(
        (10, oconn_out.shape[0] - 30),
        "NOT authoritative - exaggerated line width overcounts isolated islands; see the true-scale _connectivity.png",
        fill=(200, 0, 0))
    overview_conn_path = out_path.rsplit(".", 1)[0] + "_overview_connectivity.png"
    oconn_img.save(overview_conn_path)
    print(f"wrote {overview_conn_path} ({oreal_component_count} isolated copper "
          f"regions found besides the main one, {onoise_count} "
          f"sub-0.25mm rendering-noise fragments excluded)")


if __name__ == "__main__":
    main()
