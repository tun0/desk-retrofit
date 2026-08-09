#!/usr/bin/env python3
"""desk_original: the desk as found, drawn as a real schematic.

Two SPDT rockers form an H-bridge across the 29V rails; the winding sits
between their commons, in series with a diode-bypassed limit switch at each
end of travel.
"""
from schlib import Schematic, Sym, poly, circ, rect, stext, NOFILL, BGFILL

P = "passive"
PO = "power_out"

# --- symbols ----------------------------------------------------------------
SPDT_R = Sym("SPDT_R", "SW",
             [("1", "COM", P, 7.62, 0, 180, 3.81),
              ("2", "NC", P, 0, 7.62, 270, 2.54),
              ("3", "NO", P, 0, -7.62, 90, 2.54)],
             [circ(0, 5.08, 0.5, BGFILL), circ(0, -5.08, 0.5, BGFILL),
              circ(3.81, 0, 0.5, BGFILL),
              poly([(3.81, 0), (-0.4, 4.4)])])

SPDT_L = Sym("SPDT_L", "SW",
             [("1", "COM", P, -7.62, 0, 0, 3.81),
              ("2", "NC", P, 0, 7.62, 270, 2.54),
              ("3", "NO", P, 0, -7.62, 90, 2.54)],
             [circ(0, 5.08, 0.5, BGFILL), circ(0, -5.08, 0.5, BGFILL),
              circ(-3.81, 0, 0.5, BGFILL),
              poly([(-3.81, 0), (0.4, 4.4)])])

LIMIT = Sym("LIMIT_NC", "SW",
            [("1", "A", P, -7.62, 0, 0, 3.81),
             ("2", "B", P, 7.62, 0, 180, 3.81)],
            [circ(-3.81, 0, 0.5, BGFILL), circ(3.81, 0, 0.5, BGFILL),
             poly([(-3.81, 0), (3.81, 0)]),
             poly([(0, 0), (0, 2.2)])])

DIODE = Sym("DIODE", "D",
            [("1", "K", P, -6.35, 0, 0, 3.81),
             ("2", "A", P, 6.35, 0, 180, 3.81)],
            [poly([(2.54, 2.54), (2.54, -2.54), (-2.54, 0), (2.54, 2.54)],
                  BGFILL),
             poly([(-2.54, 2.54), (-2.54, -2.54)])],
            ref_dy=5.08, val_dy=-5.08)

DIODE_R = Sym("DIODE_R", "D",
              [("1", "A", P, -6.35, 0, 0, 3.81),
               ("2", "K", P, 6.35, 0, 180, 3.81)],
              [poly([(-2.54, 2.54), (-2.54, -2.54), (2.54, 0),
                     (-2.54, 2.54)], BGFILL),
               poly([(2.54, 2.54), (2.54, -2.54)])],
              ref_dy=5.08, val_dy=-5.08)

MOTOR = Sym("MOTOR", "M",
            [("1", "+", P, -10.16, 0, 0, 5.08),
             ("2", "-", P, 10.16, 0, 180, 5.08)],
            [circ(0, 0, 5.08, BGFILL), stext("M", -1.3, -0.9, 2.0)],
            ref_dy=7.62, val_dy=-7.62)

PSU = Sym("PSU", "PS",
          [("1", "+", PO, 0, 10.16, 270, 2.54),
           ("2", "-", PO, 0, -10.16, 90, 2.54)],
          [rect(-8.89, 7.62, 8.89, -7.62, BGFILL),
           stext("PSU", -4.4, 2.0, 1.5),
           stext("29V", -4.0, -1.2, 1.4),
           stext("1.8A", -4.6, -4.2, 1.4)],
          ref_dy=11.43, val_dy=-11.43)

# --- sheet ------------------------------------------------------------------
s = Schematic("desk_original", "Jysk Slangerup desk - as found",
              "Reverse engineered from measurement")

TOP, BOT, MID = 40.0, 140.0, 90.0
LEFT, RIGHT = 50.0, 275.0

# rails
s.wire((LEFT, TOP), (RIGHT, TOP))
s.wire((LEFT, BOT), (RIGHT, BOT))
s.label("V+", LEFT + 2, TOP - 1.5)
s.label("V-", LEFT + 2, BOT - 1.5)

# supply
s.place(PSU, "PS1", "29V 1.8A 52W", 60, MID, ref_at=(74, 84), val_at=(74, 96))
s.wire(s.pin("PS1", "1"), (60, TOP))
s.wire(s.pin("PS1", "2"), (60, BOT))
s.junction((60, TOP), (60, BOT))

# UP rocker
s.place(SPDT_R, "SW1", "UP rocker", 95, MID,
        ref_at=(88, 78), val_at=(88, 104))
s.wire(s.pin("SW1", "2"), (95, TOP))
s.wire(s.pin("SW1", "3"), (95, BOT))
s.junction((95, TOP), (95, BOT))

# DOWN rocker
s.place(SPDT_L, "SW2", "DOWN rocker", 260, MID,
        ref_at=(268, 78), val_at=(268, 104))
s.wire(s.pin("SW2", "2"), (260, TOP))
s.wire(s.pin("SW2", "3"), (260, BOT))
s.junction((260, TOP), (260, BOT))

# --- winding branch: limit switch pairs, motor ------------------------------
UPPER, LOWER = 80.0, 102.0

# top limit + bypass
s.place(LIMIT, "SW3", "top limit", 130, UPPER,
        ref_at=(130, 73), val_at=(130, 85.5))
s.place(DIODE, "D1", "allows down", 130, LOWER,
        ref_at=(130, 96), val_at=(130, 108))
LA, LB = 116.0, 144.0
s.wire((LA, UPPER), (LA, LOWER))
s.wire((LA, UPPER), s.pin("SW3", "1"))
s.wire((LA, LOWER), s.pin("D1", "1"))
s.wire((LB, UPPER), (LB, LOWER))
s.wire(s.pin("SW3", "2"), (LB, UPPER))
s.wire(s.pin("D1", "2"), (LB, LOWER))
s.wire(s.pin("SW1", "1"), (LA, MID))
s.junction((LA, MID))
s.label("MA", LA - 10, MID - 1.5)

# motor
s.place(MOTOR, "M1", "2R5 winding", 172, MID,
        ref_at=(172, 79), val_at=(172, 101))
s.wire((LB, MID), s.pin("M1", "1"))
s.junction((LB, MID))
s.label("N1", LB + 2, MID - 1.5)

# bottom limit + bypass
s.place(LIMIT, "SW4", "bottom limit", 215, UPPER,
        ref_at=(215, 73), val_at=(215, 85.5))
s.place(DIODE_R, "D2", "allows up", 215, LOWER,
        ref_at=(215, 96), val_at=(215, 108))
RA, RB = 201.0, 229.0
s.wire((RA, UPPER), (RA, LOWER))
s.wire((RA, UPPER), s.pin("SW4", "1"))
s.wire((RA, LOWER), s.pin("D2", "1"))
s.wire((RB, UPPER), (RB, LOWER))
s.wire(s.pin("SW4", "2"), (RB, UPPER))
s.wire(s.pin("D2", "2"), (RB, LOWER))
s.wire(s.pin("M1", "2"), (RA, MID))
s.junction((RA, MID))
s.label("N2", RA - 10, MID - 1.5)
s.wire((RB, MID), s.pin("SW2", "1"))
s.junction((RB, MID))
s.label("MB", RB + 2, MID - 1.5)

# --- annotation -------------------------------------------------------------
s.box(110, 68, 236, 116)
s.note("inside the leg", 112, 67, 1.4)

notes = [
    "As found. There are no control electronics anywhere in this desk.",
    "SW1 and SW2 together ARE the H-bridge. At rest both commons sit on",
    "their NC contacts, tying both winding ends to V+ - dynamic braking.",
    "",
    "Measured: 29V rail, 2.5 ohm winding, and a 0.6V / open-circuit",
    "asymmetry across the winding pair at each end of travel, which is",
    "what identifies the diode-bypassed limit switches.",
    "",
    "The exact position of SW3 and SW4 within the leg is inferred from",
    "behaviour; the leg was not opened.",
]
for i, t in enumerate(notes):
    if t:
        s.note(t, 50, 160 + i * 5.5, 1.4)

open("desk_original.kicad_sch", "w").write(s.render())
print("wrote desk_original.kicad_sch")
