#!/usr/bin/env python3
"""Detect a horizontal wire crossing a vertical one without a junction
at the crossing point. Kicad only merges two wires electrically where a
junction dot is actually drawn - an unmarked crossing looks connected on
screen but isn't, which is a silent (and easy to miss) wiring bug.
T-junctions, where the crossing point is an endpoint of both segments,
are not flagged: those are a normal corner/tee, not a crossing.

Usage: python3 find_crossings.py
"""
import _trace as t


def _classify(s):
    x1, y1, x2, y2 = s
    if abs(x1 - x2) < 0.01 and abs(y1 - y2) < 0.01:
        return None
    if abs(x1 - x2) < 0.01:
        return ("v", x1, min(y1, y2), max(y1, y2))
    if abs(y1 - y2) < 0.01:
        return ("h", y1, min(x1, x2), max(x1, x2))
    return None


def main():
    items = [(s, c) for s in t.segs if (c := _classify(s))]

    bad = []
    for i in range(len(items)):
        sa, a = items[i]
        for j in range(i + 1, len(items)):
            sb, b = items[j]
            if a[0] == b[0]:
                continue
            h, v = (a, b) if a[0] == "h" else (b, a)
            _, hy, hx0, hx1 = h
            _, vx, vy0, vy1 = v
            if not (hx0 - 0.01 <= vx <= hx1 + 0.01 and
                    vy0 - 0.01 <= hy <= vy1 + 0.01):
                continue
            # Pure touching endpoints (a T-junction/corner) don't count -
            # only a crossing through the middle of one or both segments.
            touches_h_end = abs(vx - hx0) < 0.01 or abs(vx - hx1) < 0.01
            touches_v_end = abs(hy - vy0) < 0.01 or abs(hy - vy1) < 0.01
            if touches_h_end and touches_v_end:
                continue
            bad.append((sa, sb))

    print(f"{len(bad)} crossings")
    for a, b in bad:
        print(a, b)


if __name__ == "__main__":
    main()
