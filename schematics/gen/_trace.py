"""Shared tracing for the schematic-quality checkers (find_*.py).

Monkeypatches Schematic.wire()/place() before importing sch (which lays
out and wires the whole design as a side effect of import), so every
checker sees exactly the segments/placements wire()/place() actually
draw - no separate parsing step that could drift from what they really
do. Import this, not sch, from a checker.
"""
import schlib

segs = []
places = []

_orig_wire = schlib.Schematic.wire


def _wire(self, *pts):
    # Snap here too, the same way the real wire() does internally -
    # otherwise this records the raw pre-snap arguments callers pass in,
    # which can look diagonal/misaligned even when the actual drawn
    # geometry (post-snap) is perfectly orthogonal.
    snapped = [schlib._snap_pt(p) for p in pts]
    for (x1, y1), (x2, y2) in zip(snapped, snapped[1:]):
        segs.append((x1, y1, x2, y2))
    return _orig_wire(self, *pts)


schlib.Schematic.wire = _wire

_orig_place = schlib.Schematic.place


def _place(self, sym, ref, value, x, y, *a, **kw):
    places.append((ref, sym, x, y))
    return _orig_place(self, sym, ref, value, x, y, *a, **kw)


schlib.Schematic.place = _place

import sch  # noqa: E402  (side effect: populates segs/places above)
