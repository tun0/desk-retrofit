#!/usr/bin/env python3
"""Patch a raw FlatCAM G-code file with the header Snapmaker's controller
requires to load it at all.

Without this header (specifically the ;thumbnail: line), the Snapmaker
touchscreen crashes on load rather than just failing to open the file - see
conversation and github.com/tommy-vaux/Snapmaker_2_PCB_Milling_Process,
which documents the procedure by hand. This script computes every field
that procedure asks you to fill in yourself (line count, X/Y bounds, work
speed) directly from the G-code, and reuses tommy-vaux's own generic
thumbnail (extracted from their proven-working example output) rather than
generating a real one - the Snapmaker UI only needs *a* valid PNG there,
not one that actually depicts this job.

estimated_time is a genuine estimate (distance/feedrate per move, no
accel/decel modelling) - tommy-vaux's own process describes this field as
"insert your guess" for the same reason: the machine tracks real progress
itself once running, this number is just what the screen shows before that.

Usage: python3 snapmaker_header.py <input.nc> <output.nc>
"""
import re
import sys

# Extracted verbatim from tommy-vaux/Snapmaker_2_PCB_Milling_Process's own
# Example_Gcode/isolationRouting_v2_1.cnc - a real, working thumbnail, not
# a generated placeholder. Not this project's board; that doesn't matter,
# see module docstring.
GENERIC_THUMBNAIL = (
    'data:image/png;base64,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'
)


def parse_bounds(lines):
    """Track modal X/Y state through G0/G1 moves to find real min/max."""
    x, y = 0.0, 0.0
    xs, ys = [], []
    move = re.compile(r"^[gG]0?[01]\b")
    coord = re.compile(r"([XY])(-?\d+\.?\d*)")
    for line in lines:
        if not move.match(line.strip()):
            continue
        for axis, val in coord.findall(line):
            if axis == "X":
                x = float(val)
            else:
                y = float(val)
        xs.append(x)
        ys.append(y)
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), max(xs), min(ys), max(ys)


def estimate_seconds(lines):
    """Distance/feedrate per move, no accel/decel - a rough estimate is
    all this field needs, see module docstring."""
    x, y, f = 0.0, 0.0, 1000.0  # mm/min, generic default until F seen
    total_s = 0.0
    move = re.compile(r"^[gG]0?[01]\b")
    coord = re.compile(r"([XYF])(-?\d+\.?\d*)")
    for line in lines:
        if not move.match(line.strip()):
            continue
        nx, ny = x, y
        for axis, val in coord.findall(line):
            if axis == "X":
                nx = float(val)
            elif axis == "Y":
                ny = float(val)
            elif axis == "F":
                f = float(val)
        dist = ((nx - x) ** 2 + (ny - y) ** 2) ** 0.5
        if f > 0:
            total_s += dist / f * 60.0
        x, y = nx, ny
    return int(round(total_s))


def most_common_feedrate(lines, default=60.0):
    from collections import Counter
    feeds = Counter()
    coord = re.compile(r"F(-?\d+\.?\d*)")
    for line in lines:
        m = coord.search(line)
        if m:
            feeds[float(m.group(1))] += 1
    return feeds.most_common(1)[0][0] if feeds else default


def build_header(body_lines):
    xmin, xmax, ymin, ymax = parse_bounds(body_lines)
    est_s = estimate_seconds(body_lines)
    work_speed = most_common_feedrate(body_lines)
    total_lines = len(body_lines) + 16  # +16 = this header's own line count
    return "\n".join([
        ";Header Start",
        ";header_type: cnc",
        ";renderMethod: line",
        f";file_total_lines: {total_lines}",
        f";thumbnail: {GENERIC_THUMBNAIL}",
        f";estimated_time(s): {est_s}",
        f";max_x(mm): {xmax:.3f}",
        f";max_y(mm): {ymax:.3f}",
        ";max_z(mm): 0",
        f";min_x(mm): {xmin:.3f}",
        f";min_y(mm): {ymin:.3f}",
        ";min_z(mm): 0",
        f";work_speed(mm/minute): {work_speed:.0f}",
        ";jog_speed(mm/minute): 1500",
        ";power(%): 0",
        ";Header End",
    ]) + "\n"


def main():
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <input.nc> <output.nc>")
    src, dst = sys.argv[1], sys.argv[2]

    with open(src) as f:
        raw = f.readlines()

    # Snapmaker's own required header replaces everything FlatCAM put
    # before the job actually starts cutting (first M03) - see
    # tommy-vaux's documented procedure.
    for i, line in enumerate(raw):
        if re.match(r"^\s*M0?3\b", line, re.IGNORECASE):
            body = raw[i:]
            break
    else:
        sys.exit("No M03 found - is this really a FlatCAM G-code file?")

    header = build_header(body)
    with open(dst, "w") as f:
        f.write(header)
        f.writelines(body)
    print(f"wrote {dst} ({len(body)} body lines + header)")


if __name__ == "__main__":
    main()
