"""Shared symbol library for the desk schematics.

Extracted from the symbol-definition preamble common to sch_simple.py and
sch_inline.py (originally `_sym_preamble.py`, exec'd from a path that only
existed in the session that produced this repo and was never committed).
sch_inline.py still carries its own copy of this block inline; this module
exists so sch_simple.py has one to import.
"""
from schlib import Schematic, Sym, poly, circ, rect, stext, NOFILL, BGFILL  # noqa: F401

P, I, O, PWI, PWO = "passive", "input", "output", "power_in", "power_out"

GNDS = Sym("GND", "#PWR", [("1", "GND", PWI, 0, 0, 270, 0)],
           [poly([(0, 0), (0, -1.27)]),
            poly([(-1.9, -1.27), (1.9, -1.27), (0, -3.4), (-1.9, -1.27)])],
           ref_dy=0.0, val_dy=-5.5)


def _rail(name):
    return Sym(f"RAIL_{name.strip('+')}", "#PWR",
               [("1", name, PWI, 0, 0, 90, 0)],
               [poly([(0, 0), (0, 1.27)]),
                poly([(-1.4, 1.27), (1.4, 1.27), (0, 2.8), (-1.4, 1.27)],
                     BGFILL)], ref_dy=0.0, val_dy=4.6)


RAILS = {}

R_ = Sym("R", "R", [("1", "1", P, 0, 3.81, 270, 1.27),
                    ("2", "2", P, 0, -3.81, 90, 1.27)],
         [rect(-1.02, 2.54, 1.02, -2.54, NOFILL)],
         ref_dy=1.6, val_dy=-2.8, ref_dx=3.4, val_dx=3.4)
RH = Sym("R_H", "R", [("1", "1", P, -3.81, 0, 0, 1.27),
                      ("2", "2", P, 3.81, 0, 180, 1.27)],
         [rect(-2.54, 1.02, 2.54, -1.02, NOFILL)],
         ref_dy=3.4, val_dy=-3.4)
C_ = Sym("C", "C", [("1", "1", P, 0, 3.81, 270, 2.54),
                    ("2", "2", P, 0, -3.81, 90, 2.54)],
         [poly([(-2.54, 1.27), (2.54, 1.27)]),
          poly([(-2.54, -1.27), (2.54, -1.27)])],
         ref_dy=1.6, val_dy=-2.8, ref_dx=4.4, val_dx=4.4)
F_ = Sym("FUSE", "F", [("1", "1", P, -6.35, 0, 0, 2.54),
                       ("2", "2", P, 6.35, 0, 180, 2.54)],
         [rect(-3.81, 1.27, 3.81, -1.27, NOFILL),
          poly([(-3.81, 0), (3.81, 0)])], ref_dy=4.4, val_dy=-4.4)
DH = Sym("D_H", "D", [("1", "K", P, -6.35, 0, 0, 3.81),
                      ("2", "A", P, 6.35, 0, 180, 3.81)],
         [poly([(2.54, 2.54), (2.54, -2.54), (-2.54, 0), (2.54, 2.54)],
               BGFILL), poly([(-2.54, 2.54), (-2.54, -2.54)])],
         ref_dy=4.4, val_dy=-4.4)
DV = Sym("D_V", "D", [("1", "K", P, 0, 6.35, 270, 3.81),
                      ("2", "A", P, 0, -6.35, 90, 3.81)],
         [poly([(-2.54, -2.54), (2.54, -2.54), (0, 2.54), (-2.54, -2.54)],
               BGFILL), poly([(-2.54, 2.54), (2.54, 2.54)])],
         ref_dy=1.6, val_dy=-2.8, ref_dx=4.4, val_dx=4.4)
TVS = Sym("TVS", "D", [("1", "1", P, 0, 6.35, 270, 3.81),
                       ("2", "2", P, 0, -6.35, 90, 3.81)],
          [poly([(-2.54, 0.5), (2.54, 0.5), (0, 3.4), (-2.54, 0.5)], BGFILL),
           poly([(-2.54, -0.5), (2.54, -0.5), (0, -3.4), (-2.54, -0.5)],
                BGFILL)], ref_dy=1.6, val_dy=-2.8, ref_dx=4.4, val_dx=4.4)
NMOS = Sym("NMOS", "Q", [("1", "G", I, -7.62, 0, 0, 5.08),
                         ("2", "D", P, 0, 7.62, 270, 5.08),
                         ("3", "S", P, 0, -7.62, 90, 5.08)],
           [poly([(-2.54, 2.54), (-2.54, -2.54)]),
            poly([(-1.27, 2.54), (-1.27, 1.27)]),
            poly([(-1.27, 0.64), (-1.27, -0.64)]),
            poly([(-1.27, -1.27), (-1.27, -2.54)]),
            poly([(-1.27, 1.9), (0, 1.9), (0, 2.54)]),
            poly([(-1.27, -1.9), (0, -1.9), (0, -2.54)]),
            poly([(-1.27, 0), (0, 0), (0, -1.9)]),
            circ(0, 0, 4.4, NOFILL)], ref_dy=6.0, val_dy=-6.0, ref_dx=6.5,
           val_dx=6.5)
MOT = Sym("MOTOR", "M", [("1", "+", P, -10.16, 0, 0, 5.08),
                         ("2", "-", P, 10.16, 0, 180, 5.08)],
          [circ(0, 0, 5.08, BGFILL), stext("M", -1.3, -0.9, 2.0)],
          ref_dy=7.4, val_dy=-7.4)
LIM = Sym("LIMIT", "SW", [("1", "A", P, -7.62, 0, 0, 3.81),
                          ("2", "B", P, 7.62, 0, 180, 3.81)],
          [circ(-3.81, 0, 0.5, BGFILL), circ(3.81, 0, 0.5, BGFILL),
           poly([(-3.81, 0), (3.81, 0)]), poly([(0, 0), (0, 2.2)])],
          ref_dy=4.4, val_dy=-4.4)
RLY = Sym("RELAY", "K",
          [("1", "C+", P, -15.24, 5.08, 0, 5.08),
           ("2", "C-", P, -15.24, -5.08, 0, 5.08),
           ("3", "COM", P, 15.24, 0, 180, 5.08),
           ("4", "NC", P, 15.24, 7.62, 180, 5.08),
           ("5", "NO", P, 15.24, -7.62, 180, 5.08)],
          [rect(-10.16, 6.35, -5.08, -6.35, NOFILL),
           poly([(-10.16, 5.08), (-10.16, 5.08)]),
           poly([(-5.08, 0), (-2.0, 0)]), poly([(-2.0, 0), (-2.0, 3.2)]),
           circ(10.16, 0, 0.5, BGFILL), circ(10.16, 7.62, 0.5, BGFILL),
           circ(10.16, -7.62, 0.5, BGFILL),
           poly([(10.16, 0), (7.6, 6.9)])],
          ref_dy=11.5, val_dy=-11.5)


def box(name, prefix, left, right, w=25.4):
    n = max(len(left), len(right))
    h = max(n * 2.54 + 5.08, 12.7)
    top = h / 2 - 3.81
    pins = []
    for i, (num, nm, et) in enumerate(left):
        pins.append((num, nm, et, -w / 2 - 5.08, top - i * 2.54, 0, 5.08))
    for i, (num, nm, et) in enumerate(right):
        pins.append((num, nm, et, w / 2 + 5.08, top - i * 2.54, 180, 5.08))
    return Sym(name, prefix, pins,
               [rect(-w / 2, h / 2, w / 2, -h / 2, BGFILL)],
               hide_names=False, ref_dy=h / 2 + 2.6, val_dy=-h / 2 - 2.6)


BUCK = box("BUCK", "U", [("1", "VIN", PWI), ("2", "GND", PWI)],
           [("3", "VOUT", PWO)], 30.48)
MCU = box("MCU", "U",
          [("1", "5V", PWI), ("2", "GND", PWI), ("3", "3V3", PWO)],
          [("4", "DIR_A", O), ("5", "DIR_B", O), ("6", "PWM", O),
           ("7", "MODE", O), ("8", "KICK", O), ("9", "ISENSE", I),
           ("10", "SDA", P), ("11", "SCL", P), ("12", "SW_UP", I),
           ("13", "SW_DN", I)], 33.02)
MONO = box("MONO", "U",
           [("1", "VCC", PWI), ("2", "GND", PWI), ("3", "A", I),
            ("4", "B", I), ("5", "CLR", I), ("6", "REXT", P),
            ("7", "CEXT", P)], [("8", "Q", O)], 30.48)
AND2 = box("AND", "U", [("1", "A", I), ("2", "B", I)], [("3", "Y", O)], 20.32)
DRVX = box("GATEDRV", "U", [("1", "VCC", PWI), ("2", "GND", PWI),
                            ("3", "IN", I)], [("4", "OUT", O)], 25.4)
ACS = box("ACS724", "U",
          [("1", "VCC", PWI), ("2", "GND", PWI), ("3", "IP+", P)],
          [("4", "IP-", P), ("5", "OUT", O)], 27.94)
CONN = box("CONN4", "J", [("1", "1", P), ("2", "2", P), ("3", "3", P),
                          ("4", "4", P)], [], 17.78)
PSUB = box("PSU", "PS", [], [("1", "+29V", PWO), ("2", "0V", PWO)], 25.4)
