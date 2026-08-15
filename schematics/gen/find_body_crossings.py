#!/usr/bin/env python3
"""Detect a wire running through a symbol's own body instead of around
it - purely cosmetic (no electrical effect), but reads as if the wire
terminates inside the part rather than passing behind it.

Each symbol's bounding box comes from its own pin tips, shrunk inward by
PAD: pins extend past the drawn body outline by roughly one stub length,
so using the raw pin bbox would flag every wire that legitimately
approaches a pin.

Usage: python3 find_body_crossings.py
"""
import _trace as t

PAD = 0.3


def _bbox(sym, x, y):
    pins = [(p[3], p[4]) for p in sym.pins]
    if not pins:
        return None
    xs, ys = zip(*pins)
    x0, x1 = min(xs) + x, max(xs) + x
    y0, y1 = min(ys) + y, max(ys) + y
    return (x0 + PAD, x1 - PAD, y0 + PAD, y1 - PAD)


def _touches_box(x1, y1, x2, y2, box):
    x0, x1b, y0, y1b = box
    if abs(x1 - x2) < 0.01:
        if x1 <= x0 or x1 >= x1b:
            return False
        lo, hi = min(y1, y2), max(y1, y2)
        return not (hi <= y0 or lo >= y1b)
    if abs(y1 - y2) < 0.01:
        if y1 <= y0 or y1 >= y1b:
            return False
        lo, hi = min(x1, x2), max(x1, x2)
        return not (hi <= x0 or lo >= x1b)
    return False


def main():
    boxes = []
    for ref, sym, x, y in t.places:
        b = _bbox(sym, x, y)
        if b and b[0] < b[1] and b[2] < b[3]:
            boxes.append((ref, b))

    bad = []
    for s in t.segs:
        x1, y1, x2, y2 = s
        for ref, box in boxes:
            if _touches_box(x1, y1, x2, y2, box):
                bad.append((s, ref))

    print(f"{len(bad)} wire-through-body candidates")
    for s, ref in bad:
        print(s, "->", ref)


if __name__ == "__main__":
    main()
