#!/usr/bin/env python3
"""Strip routing from ../desk.kicad_pcb and re-route it from scratch.

For experimenting with placement: drag footprints around in KiCad's PCB
editor (or move them via the pcbnew API), save, then run this script. It
throws away all existing tracks/vias/zones, re-routes with Freerouting,
widens any undersized SMD-fanout stub and drops any single-layer
dangling via Freerouting's own fanout stage leaves behind, and refills
both ground pours plus a keepout around every mounting hole
(MOUNTING_HOLE_KEEPOUT_MM) - the same manual sequence this session used
for every placement change, now in one command.

Does NOT touch footprint positions, the board outline, or anything else -
only tracks, vias, and zones (the two GND pours and the mounting-hole
keepouts). Re-run after every placement change you want to test.

Usage (from schematics/gen/):
    python3 reroute_pcb.py [--passes N]

Requires:
    - Freerouting jar installed at the path below (KiCad plugin manager,
      "Freerouting" plugin)
    - Java on PATH
    - pcbnew Python module (comes with the KiCad install)

Implementation note: each pcbnew-touching step below runs as its own
`python3 -c ...` subprocess rather than inline in this process. Chaining
multiple LoadBoard/Remove/Export/Import calls within a single long-lived
pcbnew session corrupts the SWIG bindings after a few operations (this
KiCad build) - AttributeErrors on a previously-fine BOARD object, for no
apparent reason tied to code order. One pcbnew call per process sidesteps
it entirely, matching how this whole PCB layout was developed by hand.
"""
import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile

PCB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "desk.kicad_pcb"))
# .kicad_pro is gitignored (never version-controlled) - it holds real,
# hand-set DRC rules (0.4mm clearance etc.) that don't live in the .kicad_pcb
# itself. Loading a board from one path and Save()-ing it to another where a
# .kicad_pro already exists causes pcbnew to silently overwrite that project
# file with in-memory defaults (observed directly: min_clearance 0.4 -> 0.0,
# min_track_width 0.5 -> 0.2, after nothing more than a LoadBoard+Save
# round-trip through a temp copy). Since there's no git history to recover
# it from, back it up before touching anything and restore it unconditionally
# when done, regardless of what pcbnew's Save() calls did to it.
PRO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "desk.kicad_pro"))
FREEROUTING_JAR = os.path.expanduser(
    "~/.local/share/kicad/10.0/3rdparty/plugins/"
    "app_freerouting_kicad-plugin/jar/freerouting-2.3.0.jar"
)

# Must match the board's real netclass rules (board setup -> Design Rules).
# ExportSpecctraDSN always writes generic 0.2mm/0.2mm/0.6mm-0.3mm-via
# defaults regardless of the actual netclass, so these get patched in.
TRACK_WIDTH_MM = 0.5
CLEARANCE_MM = 0.4
VIA_PAD_MM = 1.2
VIA_DRILL_MM = 0.6

# Motor-current-carrying nets get a wider trace than the generic
# TRACK_WIDTH_MM signal default - checked directly against pcbnew (see
# conversation): the whole board was a uniform 0.5mm, which a standard
# IPC-2221 external-layer/1oz-copper table puts at roughly 1A for a sane
# thermal rise, undersized for this design's measured 1.8A supply
# (current-limited, but "2 min continuous at half load" is a real,
# documented duty mode, not just brief pulses). 1.0mm covers 1.8A with
# real margin. These have to be their own Specctra DSN class (pulled out
# of kicad_default's member list below), not just a bigger number
# patched into the global (width 500) after export - a uniform widen-
# in-place attempt broke clearance against neighbouring pads in the
# tightly-packed relay/diode cluster (K1/K2/D2), which was already
# routed right at the 0.4mm clearance limit at 0.5mm width. Freerouting
# needs the wider requirement as an actual per-net rule so it can find
# valid paths around that, not have it forced on afterward.
POWER_TRACK_WIDTH_MM = 1.0
POWER_NETS = ("VSW", "/MRET", "/DRV_UP", "Net-(TB1-Pin_1)", "Net-(TB1-Pin_2)")

ZONE_CLEARANCE_MM = 0.4
ZONE_THERMAL_GAP_MM = 0.3
BOARD_MARGIN_MM = 2.0

# MountingHole_* footprints (H1-H4) use a single NPTH pad (no copper
# annulus) with no keepout zone of their own - checked directly (see
# conversation): the GND pour was filling to within ~0.3mm of the drill
# edge, just the zone's own generic clearance setting, not a real
# mechanical keepout. A common M3 screw/washer head (~6mm) needs about
# 1.4mm past the 3.2mm drill edge to actually clear copper. This is a
# rule-area keepout (no copper fill, any layer), not just a wider
# clearance number, so it survives regardless of zone settings.
MOUNTING_HOLE_KEEPOUT_MM = 6.5


def run_py(code):
    """Run `code` as a standalone python3 subprocess and return stdout."""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"subprocess failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def check_overlaps(src_path):
    # Courtyard-only, not full bounding box: silkscreen overlaps are expected
    # and accepted on this board (irrelevant for a self-milled design) - only
    # a real F.Courtyard overlap indicates parts that would physically collide.
    out = run_py(f"""
import pcbnew
b = pcbnew.LoadBoard({src_path!r})

def courtyard_bbox(fp):
    bbox = None
    for item in fp.GraphicalItems():
        if item.GetLayerName() == 'F.Courtyard':
            bb = item.GetBoundingBox()
            l, t, r, bo = bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()
            if bbox is None:
                bbox = [l, t, r, bo]
            else:
                bbox = [min(bbox[0], l), min(bbox[1], t), max(bbox[2], r), max(bbox[3], bo)]
    return bbox

def intersects(a, c):
    return not (a[2] <= c[0] or c[2] <= a[0] or a[3] <= c[1] or c[3] <= a[1])

fps = list(b.GetFootprints())
boxes = [(fp.GetReference(), courtyard_bbox(fp)) for fp in fps]
boxes = [(ref, bb) for ref, bb in boxes if bb is not None]
overlaps = [(boxes[i][0], boxes[j][0])
            for i in range(len(boxes)) for j in range(i+1, len(boxes))
            if intersects(boxes[i][1], boxes[j][1])]
print(overlaps)
""")
    overlaps = ast.literal_eval(out.strip().splitlines()[-1])
    if overlaps:
        sys.exit(f"Footprint courtyard overlaps found, fix placement first: {overlaps}")


def strip_routing(src_path, dst_path):
    run_py(f"""
import pcbnew
b = pcbnew.LoadBoard({src_path!r})
for t in list(b.Tracks()):
    b.Remove(t)
for z in list(b.Zones()):
    b.Remove(z)
b.Save({dst_path!r})
""")


def board_outline_mm(src_path):
    out = run_py(f"""
import pcbnew
b = pcbnew.LoadBoard({src_path!r})
edges = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
minx = min(pcbnew.ToMM(d.GetBoundingBox().GetLeft()) for d in edges)
miny = min(pcbnew.ToMM(d.GetBoundingBox().GetTop()) for d in edges)
maxx = max(pcbnew.ToMM(d.GetBoundingBox().GetRight()) for d in edges)
maxy = max(pcbnew.ToMM(d.GetBoundingBox().GetBottom()) for d in edges)
print(minx, miny, maxx, maxy)
""")
    return tuple(float(v) for v in out.strip().splitlines()[-1].split())


def export_and_patch_dsn(src_path, dsn_path):
    run_py(f"""
import pcbnew
b = pcbnew.LoadBoard({src_path!r})
ok = pcbnew.ExportSpecctraDSN(b, {dsn_path!r})
assert ok, "ExportSpecctraDSN failed"
""")
    content = open(dsn_path).read()
    m = re.search(r"Via\[0-1\]_(\d+):(\d+)_um", content)
    if not m:
        sys.exit("could not find via padstack in exported DSN")
    old_dia = m.group(1)
    via_pad_um = int(VIA_PAD_MM * 1000)
    via_drill_um = int(VIA_DRILL_MM * 1000)
    content = content.replace(m.group(0), f"Via[0-1]_{via_pad_um}:{via_drill_um}_um")
    content = content.replace(f"(circle F.Cu {old_dia})", f"(circle F.Cu {via_pad_um})")
    content = content.replace(f"(circle B.Cu {old_dia})", f"(circle B.Cu {via_pad_um})")
    content = content.replace("(width 200)", f"(width {int(TRACK_WIDTH_MM * 1000)})")
    content = content.replace("(clearance 200)", f"(clearance {int(CLEARANCE_MM * 1000)})")
    content = _split_power_class(content, via_pad_um, via_drill_um)
    open(dsn_path, "w").write(content)


def _dsn_token(net):
    # Specctra DSN quotes any net name containing characters that aren't
    # plain identifier chars (Kicad's own exporter already does this for
    # the member lists being patched here - matched, not reinvented).
    return f'"{net}"' if re.search(r"[^A-Za-z0-9_+/-]", net) else net


def _find_matching_paren(content, open_pos):
    """content[open_pos] must be '(' - return the index just past its
    matching ')'."""
    depth = 0
    for i in range(open_pos, len(content)):
        if content[i] == "(":
            depth += 1
        elif content[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    sys.exit("unbalanced parens scanning DSN class block")


def _split_power_class(content, via_pad_um, via_drill_um):
    # Pull POWER_NETS out of kicad_default's member list into their own
    # class with a wider (rule (width ...)) - a class-level rule is what
    # Freerouting actually routes to; patching the global width after
    # export (like the plain TRACK_WIDTH_MM case above) can't give some
    # nets a different width than others.
    start = content.find("(class kicad_default")
    if start == -1:
        sys.exit("could not find kicad_default class in exported DSN")
    end = _find_matching_paren(content, start)
    block = content[start:end]

    members_m = re.search(r"\(class kicad_default((?:.|\n)*?)\(circuit", block)
    members = members_m.group(1)
    trimmed = members
    for net in POWER_NETS:
        token = _dsn_token(net)
        trimmed, n = re.subn(r"\s+" + re.escape(token) + r"(?=\s)", "", trimmed,
                              count=1)
        if not n:
            sys.exit(f"power net {net!r} not found in kicad_default class - "
                      f"check it's actually present on this board")
    block = block.replace(f"(class kicad_default{members}(circuit",
                          f"(class kicad_default{trimmed}(circuit", 1)

    power_members = " ".join(_dsn_token(n) for n in POWER_NETS)
    power_width_um = int(POWER_TRACK_WIDTH_MM * 1000)
    power_class = (
        f"\n    (class power_nets {power_members}\n"
        f"      (circuit\n"
        f'        (use_via "Via[0-1]_{via_pad_um}:{via_drill_um}_um")\n'
        f"      )\n"
        f"      (rule\n"
        f"        (width {power_width_um})\n"
        f"        (clearance {int(CLEARANCE_MM * 1000)})\n"
        f"      )\n"
        f"    )"
    )
    # Insert the new class right after kicad_default's own closing paren -
    # still inside the enclosing (network ...) block, as a sibling class,
    # not after it (that would be a syntax error Freerouting can't parse).
    return content[:start] + block + power_class + content[end:]


def run_freerouting(dsn_path, ses_path, passes):
    if not os.path.exists(FREEROUTING_JAR):
        sys.exit(f"Freerouting jar not found at {FREEROUTING_JAR}")
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", FREEROUTING_JAR,
            "-de", dsn_path, "-do", ses_path, "-mp", str(passes),
        ],
        capture_output=True, text=True, timeout=300,
    )
    log = result.stdout + result.stderr
    print(log[-1500:])
    m = re.findall(r"(\d+) unrouted and (\d+) violations", log)
    if not m or m[-1] != ("0", "0"):
        sys.exit("Freerouting did not fully complete - see log above")


def import_ses_and_zone(clean_path, ses_path, out_path):
    out = run_py(f"""
import pcbnew

b = pcbnew.LoadBoard({clean_path!r})
ok = pcbnew.ImportSpecctraSES(b, {ses_path!r})
assert ok, "ImportSpecctraSES failed"

# Freerouting's own SMD-pin fanout stage (escaping a surface-mount pad
# onto the routing grid) doesn't reliably respect the DSN width rule -
# checked directly (see conversation, U1's TO-263-5 swap): 3 short stub
# segments came back at 0.375mm against this board's 0.5mm netclass
# floor. Width is a floor-only fix (never narrows a wider, intentional
# power-net segment - see POWER_TRACK_WIDTH_MM above - only ever raises
# a too-thin one up to the base minimum).
min_width = pcbnew.FromMM({TRACK_WIDTH_MM})
widened = 0
for t in b.Tracks():
    if t.Type() == pcbnew.PCB_TRACE_T and t.GetWidth() < min_width:
        t.SetWidth(min_width)
        widened += 1
if widened:
    print(f"widened {{widened}} undersized fanout stub(s) to {TRACK_WIDTH_MM}mm")

# Same fanout stage sometimes leaves a via that only ever touches copper
# (track or filled zone) on ONE of its two spanned layers - provably not
# completing a layer transition (also checked directly: one such via
# had 2 F.Cu tracks and zero B.Cu tracks). Safe to remove: if it were
# carrying the net across layers, the other layer would show it.
def _touches_layer(b, pos, net, layer_name):
    for t in b.Tracks():
        if (t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == net
                and t.GetLayerName() == layer_name
                and (min((t.GetStart() - pos).EuclideanNorm(),
                         (t.GetEnd() - pos).EuclideanNorm()) < 1000)):
            return True
    layer_id = pcbnew.F_Cu if layer_name == "F.Cu" else pcbnew.B_Cu
    for zone in b.Zones():
        if (not zone.GetIsRuleArea() and zone.IsOnLayer(layer_id)
                and zone.GetNetname() == net
                and zone.HitTestFilledArea(layer_id, pos)):
            return True
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if (pad.GetNetname() == net
                    and layer_id in pad.GetLayerSet().Seq()
                    and (pad.GetPosition() - pos).EuclideanNorm() < 1000):
                return True
    return False

dangling = [v for v in list(b.Tracks()) if v.Type() == pcbnew.PCB_VIA_T
            and not (_touches_layer(b, v.GetPosition(), v.GetNetname(), "F.Cu")
                     and _touches_layer(b, v.GetPosition(), v.GetNetname(), "B.Cu"))]
for v in dangling:
    b.Remove(v)
if dangling:
    print(f"removed {{len(dangling)}} dangling via(s) touching only one copper layer")

b.Save({out_path!r})
n_tracks = sum(1 for t in b.Tracks() if t.Type() == pcbnew.PCB_TRACE_T)
n_vias = sum(1 for t in b.Tracks() if t.Type() == pcbnew.PCB_VIA_T)
print(n_tracks, n_vias)
""")
    n_tracks, n_vias = out.strip().splitlines()[-1].split()
    print(f"Routed: {{n_tracks}} tracks, {{n_vias}} vias".format(n_tracks=n_tracks, n_vias=n_vias))

    minx, miny, maxx, maxy = board_outline_mm(out_path)
    m = BOARD_MARGIN_MM
    x0, y0, x1, y1 = minx + m, miny + m, maxx - m, maxy - m

    run_py(f"""
import pcbnew
import math
b = pcbnew.LoadBoard({out_path!r})

# Keepouts first, so the GND pour fill below already avoids them on its
# one and only fill pass - order matters, filler.Fill() runs once at the
# end of this block.
mounting_holes = [fp.GetPosition() for fp in b.GetFootprints()
                  if str(fp.GetFPID().GetLibItemName()).startswith("MountingHole")]
r = pcbnew.FromMM({MOUNTING_HOLE_KEEPOUT_MM} / 2)
for i, hpos in enumerate(mounting_holes):
    zone = pcbnew.ZONE(b)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layers)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(False)  # else it flags the mounting hole's own NPTH pad
    zone.SetZoneName(f"mounting_hole_keepout_{{i}}")
    outline = zone.Outline()
    outline.NewOutline()
    for seg in range(32):
        ang = 2 * math.pi * seg / 32
        outline.Append(int(hpos.x + r * math.cos(ang)), int(hpos.y + r * math.sin(ang)))
    b.Add(zone)

for layer, name in [(pcbnew.F_Cu, "GND_POUR"), (pcbnew.B_Cu, "GND_POUR_B")]:
    zone = pcbnew.ZONE(b)
    zone.SetLayer(layer)
    zone.SetNetCode(b.GetNetcodeFromNetname("GND"))
    zone.SetZoneName(name)
    outline = zone.Outline()
    outline.NewOutline()
    for px, py in [({x0}, {y0}), ({x1}, {y0}), ({x1}, {y1}), ({x0}, {y1})]:
        outline.Append(int(pcbnew.FromMM(px)), int(pcbnew.FromMM(py)))
    zone.SetIsFilled(False)
    zone.SetLocalClearance(pcbnew.FromMM({ZONE_CLEARANCE_MM}))
    zone.SetThermalReliefGap(pcbnew.FromMM({ZONE_THERMAL_GAP_MM}))
    # keep disconnected fill fragments (deliberate: cheaper to mill solid
    # copper than bare board carved out of the same area)
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    b.Add(zone)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
b.Save({out_path!r})
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=10, help="Freerouting max passes")
    args = ap.parse_args()

    pro_backup = None
    if os.path.exists(PRO_PATH):
        pro_backup = PRO_PATH + ".reroute-backup"
        shutil.copy2(PRO_PATH, pro_backup)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            check_overlaps(PCB_PATH)

            clean_path = os.path.join(tmp, "clean.kicad_pcb")
            strip_routing(PCB_PATH, clean_path)

            print(f"Routing {board_outline_mm(clean_path)} board...")

            dsn_path = os.path.join(tmp, "route.dsn")
            ses_path = os.path.join(tmp, "route.ses")
            export_and_patch_dsn(clean_path, dsn_path)

            run_freerouting(dsn_path, ses_path, args.passes)

            import_ses_and_zone(clean_path, ses_path, PCB_PATH)
            print(f"Saved {PCB_PATH}")
    finally:
        if pro_backup:
            shutil.move(pro_backup, PRO_PATH)
            print(f"Restored {PRO_PATH} (pcbnew's Save() calls can clobber it - see comment at top)")

    print("Run `kicad-cli pcb drc --severity-all desk.kicad_pcb` from schematics/ to verify.")


if __name__ == "__main__":
    main()
