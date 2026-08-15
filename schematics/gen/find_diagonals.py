#!/usr/bin/env python3
"""Detect non-orthogonal wire segments. wire() is meant to draw only
horizontal/vertical runs - a diagonal means two points were passed that
don't share an x or a y, which almost always means a missing bend point
rather than an intentional diagonal (Kicad wires are orthogonal by
convention; a real diagonal renders fine but reads as a mistake here).

Usage: python3 find_diagonals.py
"""
import _trace as t


def main():
    bad = [s for s in t.segs if abs(s[0] - s[2]) > 0.01 and abs(s[1] - s[3]) > 0.01]
    print(f"{len(bad)} diagonal segments")
    for s in bad:
        print(s)


if __name__ == "__main__":
    main()
