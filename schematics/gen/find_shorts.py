#!/usr/bin/env python3
"""Detect candidate short circuits: two collinear wire segments, on the
same axis, whose spans overlap. Real shorts show up this way when two
different nets' wires run down the same stretch of grid instead of
meeting at a single point - something Kicad's own ERC does not catch,
since electrically the overlap just looks like extra junctions on one
net, not two nets touching.

Usage: python3 find_shorts.py
"""
import _trace as t


def _norm(seg):
    x1, y1, x2, y2 = seg
    if abs(x1 - x2) < 0.01:
        return ("v", round(x1, 2), min(y1, y2), max(y1, y2))
    elif abs(y1 - y2) < 0.01:
        return ("h", round(y1, 2), min(x1, x2), max(x1, x2))
    return None


def main():
    normed = [(i, _norm(s)) for i, s in enumerate(t.segs)]
    normed = [(i, n) for i, n in normed if n]

    bad = []
    for i in range(len(normed)):
        ai, (ta, ka, lo_a, hi_a) = normed[i]
        for j in range(i + 1, len(normed)):
            aj, (tb, kb, lo_b, hi_b) = normed[j]
            if ta != tb or ka != kb:
                continue
            if hi_a < lo_b - 0.05 or hi_b < lo_a - 0.05:
                continue
            overlap = min(hi_a, hi_b) - max(lo_a, lo_b)
            if overlap > 0.05:
                bad.append((t.segs[ai], t.segs[aj], overlap))

    print(f"{len(bad)} candidate shorts")
    for a, b, ov in bad:
        print(a, b, f"overlap={ov:.2f}")


if __name__ == "__main__":
    main()
