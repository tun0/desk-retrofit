#!/usr/bin/env python3
"""Strip routing from ../desk.kicad_pcb and re-route it from scratch.

For experimenting with placement: drag footprints around in KiCad's PCB
editor (or move them via the pcbnew API), save, then run this script. It
throws away all existing tracks/vias/zones, re-routes with Freerouting,
and refills both ground pours - the same manual sequence this session
used for every placement change, now in one command.

Does NOT touch footprint positions, the board outline, or anything else -
only tracks, vias, and the two GND zones. Re-run after every placement
change you want to test.

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

ZONE_CLEARANCE_MM = 0.4
ZONE_THERMAL_GAP_MM = 0.3
BOARD_MARGIN_MM = 2.0


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
    open(dsn_path, "w").write(content)


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
b = pcbnew.LoadBoard({out_path!r})

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
