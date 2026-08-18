#!/usr/bin/env python3
"""desk - Jysk Slangerup desk retrofit, in-line drive.

No transfer relay and no in-place fallback. The box sits in the 4-core
cable and permanently owns the winding; the handset is permanently fed
3V3 and its rockers are plain inputs.

Reverting is physical: motor - box - handset  becomes  motor - handset.
"""
import sys  # noqa: E402

from symbols import (Schematic, GNDS, RAILS, _rail, R_, C_, DH,  # noqa: E402
                     TVS, NMOS, MOT, LIM, RLY, BUCK, MCU, GPIO_PIN,
                     MCU_5V, MCU_GND, MCU_3V3, MONO, AND2,
                     BJT_NPN, BJT_PNP, ACS, CONN, PSU, AC_FLAG, ROCKER, TERM2,
                     JP3, JP4)

s = Schematic("desk", "Slangerup desk retrofit - in-line drive",
              "Box owns the winding; unplug it to revert", paper="A1")

_n = [0]


def _uref():
    _n[0] += 1
    return f"#PWR{_n[0]:03d}"


def gnd_tap(x, y):
    # Nudge is a full grid step (1.27), not 1mm - snap() rounds both
    # endpoints to the nearest grid point, and a 1mm nudge sometimes
    # rounds to the SAME point as its own start (whenever y falls in the
    # part of its grid cell where +1mm doesn't cross the rounding
    # boundary), producing an invisible zero-length wire. Adding exactly
    # one grid step always lands one step over, never the same point.
    s.place(GNDS, _uref(), "GND", x, y + 1.27, hide_ref=True, hide_val=True)
    s.wire((x, y), (x, y + 1.27))


def tap(x, y, name):
    if name not in RAILS:
        RAILS[name] = _rail(name)
    s.place(RAILS[name], _uref(), name, x, y - 1.27, hide_ref=True)
    s.wire((x, y), (x, y - 1.27))


V5, VS, V3 = "+5V", "VSW", "+3V3"

# ========================================================== controller ====
# Shifted 230mm left of where this whole CONTROLLER-through-DRIVE block
# used to sit, to make room for SUPPLY to move to the right instead (next
# to J2, which it now wires to directly - see SUPPLY section and
# conversation).
s.note("CONTROLLER", 55, 80, 2.8)
# Off-board: U2's own 2x22 header is a genuine copper-layer capacity
# wall on this PCB (see JP2/JP3/JP4 in symbols.py) - it lives elsewhere
# as a free-standing DevKitC, wired in over JST-XH pigtails instead of
# a footprint here.
s.place(MCU, "U2", "ESP32", 90, 150, on_board=False)
# U2 has no footprint on this board at all any more (see the on_board
# note above), so NONE of its pins connect by drawn PCB-shaped wiring -
# every one of them reaches the rest of the circuit either as a plain
# power-rail tap (5V/3V3/GND - already global nets, nothing pigtail-
# specific needed) or via a matching schematic label picked up by one
# of three small JST-XH connectors below, grouped by function: power,
# the four drive outputs, and the rocker/current-sense inputs. Which
# physical DevKitC pin carries which signal still matters for firmware
# (SIGNAL_GPIO below) and for wiring the real pigtail harness later,
# but no longer for PCB routing - there's no PCB copper here to route.
mcu_5v, mcu_gnd, mcu_3v3 = (s.pin("U2", MCU_5V), s.pin("U2", MCU_GND),
                            s.pin("U2", MCU_3V3))
s.wire(mcu_5v, (mcu_5v[0], mcu_5v[1] - 10))
tap(mcu_5v[0], mcu_5v[1] - 10, V5)
s.wire(mcu_gnd, (mcu_gnd[0], mcu_gnd[1] + 10))
gnd_tap(mcu_gnd[0], mcu_gnd[1] + 10)
s.wire(mcu_3v3, (mcu_3v3[0], mcu_3v3[1] - 14))
tap(mcu_3v3[0], mcu_3v3[1] - 14, V3)

# Constraints on the GPIO choice (firmware-side, unaffected by U2 no
# longer being on this PCB): avoid strapping (0/3/45/46), avoid this
# module's flash/PSRAM-reserved range (22-37 - wider than usual since
# this is an N16R8/octal-PSRAM part), avoid native USB (19/20), keep
# ISENSE on an ADC1-capable pin.
SIGNAL_GPIO = {"KICK": 4, "ISENSE": 2, "MODE": 8, "SW_UP": 9, "SW_DN": 10,
               "SDA": 12, "SCL": 13, "DIR_A": 39, "DIR_B": 40, "PWM": 42}
PIN = {sig: GPIO_PIN[g] for sig, g in SIGNAL_GPIO.items()}

OUT = {PIN["DIR_A"]: "DIR_A", PIN["DIR_B"]: "DIR_B", PIN["PWM"]: "PWM",
       PIN["MODE"]: None, PIN["KICK"]: "KICK", PIN["ISENSE"]: "ISENSE",
       PIN["SDA"]: "SDA", PIN["SCL"]: "SCL", PIN["SW_UP"]: "SW_UP",
       PIN["SW_DN"]: "SW_DN"}
pins = {k: s.pin("U2", k) for k in OUT}

# Every direct breakout off U2's own body gets the SAME stub length and
# a glabel with its signal's name - that's the whole connection on this
# end. JPDRV/JPSNS below (and their destination-side counterparts near
# WATCHDOG+GATING and the rocker/current-sense circuitry) pick these up
# purely by matching label, the same mechanism WDOG already uses. Length
# is purely cosmetic (there's no PCB copper to route here, so it's never
# routing-constrained the way a real stub would be) - one shared length
# keeps every label lined up in a single column per side instead of the
# ragged mix that piled up as signals were added one at a time.
#
# KICK/ISENSE/SW_UP/SW_DN/SDA/SCL exit U2's RIGHT side, DIR_A/DIR_B/PWM
# its LEFT side (the real symbol's own pin layout, checked directly
# against MCU.pins_by_unit - do not swap without rechecking). Routing a
# "left" pin's stub off to the right - as an earlier version of this did
# - drags the wire back across the entire 44-pin body, where it can run
# straight through another pin's own connection point and short onto
# whatever THAT pin carries (that's what happened to DIR_A/+5V and
# SW_DN/+3V3 here: a short ERC didn't have geometry to flag as
# "overlapping", since it's a wire passing through a pin tip, not two
# collinear segments). Each stub must exit on its pin's own side, and
# each label's anchor tip must face back along the wire it terminates -
# glabel's angle=180 puts the tip on the right and grows the text left
# (the mirror of its left-side default), matching a stub that arrives
# from the right. Without it the wire runs into the label's flat back
# edge instead of its point.
STUB_LEN = 20.0
RIGHT_SIDE = (PIN["KICK"], PIN["ISENSE"], PIN["SW_UP"], PIN["SW_DN"],
              PIN["SDA"], PIN["SCL"])
LEFT_SIDE = (PIN["DIR_A"], PIN["DIR_B"], PIN["PWM"])
for num in RIGHT_SIDE:
    p = pins[num]
    x = p[0] + STUB_LEN
    s.wire(p, (x, p[1]))
    s.glabel(OUT[num], x, p[1])
for num in LEFT_SIDE:
    p = pins[num]
    x = p[0] - STUB_LEN
    s.wire(p, (x, p[1]))
    s.glabel(OUT[num], x, p[1], angle=180)

# MODE is unused, same as most of this part's other 30-odd pins - no
# stub or "spare" label, that only made sense when this pin was one of
# a handful the hand-drawn box even had.


# U2 PIGTAILS: JP1/JP2/JP3 grouped in their own boxed-off block, same
# convention as LEG/HANDSET below - these three are the actual physical
# boundary of this sheet (U2 itself is off-board, see its own on_board
# note), so they deserve the same "this is a distinct unit" treatment,
# not just whatever gap happened to be free. Previously placed at
# x=780/820/860 - past this A1 sheet's own 841mm width, off the visible
# page entirely (unnoticed because nothing here has a PCB net to check
# against, only ERC/labels, which don't care where the paper edge is).
# Mirrored so all three exit RIGHT, toward their labels/taps, instead
# of left into the box's own empty margin - each pin then just runs a
# single straight wire to its label instead of the pigtail_stub jog
# (fanning out per-pin columns to dodge each other's stubs), since a
# plain horizontal run at each pin's own row never crosses its
# neighbours in the first place.
s.note("U2 PIGTAILS", 680, 435, 2.8)
s.box(680, 440, 805, 513)

# JPDRV: the pigtail plug for the four drive outputs. Placed below U2's
# own symbol - position here is purely cosmetic now (no PCB copper to
# route on this end), so it's not aligned to anything in particular.
JPDRV_X, JPDRV_Y = 695.0, 485.0
s.place(JP4, "JP1", "drive pigtail", JPDRV_X, JPDRV_Y, mirror="y",
        on_board=False)
for i, sig in enumerate(("KICK", "DIR_A", "DIR_B", "PWM")):
    p = s.pin("JP1", str(i + 1))
    x = p[0] + 20
    s.wire(p, (x, p[1]))
    s.glabel(sig, x, p[1])

# JPSNS: the pigtail plug for the two rocker inputs plus current sense.
JPSNS_X, JPSNS_Y = 735.0, 485.0
s.place(JP3, "JP2", "sense pigtail", JPSNS_X, JPSNS_Y, mirror="y",
        on_board=False)
for i, sig in enumerate(("SW_UP", "SW_DN", "ISENSE")):
    p = s.pin("JP2", str(i + 1))
    x = p[0] + 20
    s.wire(p, (x, p[1]))
    s.glabel(sig, x, p[1])

# JPPWR: the power pigtail - 5V in to U2, 3V3 back out to the rest of
# this board (R13/R15/TB4), GND common. Just three more taps onto the
# same global rails everything else already uses; no label needed.
# GND (pin 3) shares its column with +3V3 (pin 2) instead of getting
# its own - one goes up from pin 2's row, the other down from pin 3's,
# so their spans never overlap (same reasoning as KICK/PWM sharing a
# column back at JP5).
JPPWR_X, JPPWR_Y = 775.0, 485.0
s.place(JP3, "JP3", "power pigtail", JPPWR_X, JPPWR_Y, mirror="y",
        on_board=False)
p5 = s.pin("JP3", "1")
col5 = p5[0] + 10
s.wire(p5, (col5, p5[1]), (col5, p5[1] - 8))
tap(col5, p5[1] - 8, V5)
p3 = s.pin("JP3", "2")
col3g = p3[0] + 15
s.wire(p3, (col3g, p3[1]), (col3g, p3[1] - 8))
tap(col3g, p3[1] - 8, V3)
pg = s.pin("JP3", "3")
s.wire(pg, (col3g, pg[1]), (col3g, pg[1] + 8))
gnd_tap(col3g, pg[1] + 8)

# HANDSET INTERFACE: rocker dividers + J3 (to handset). Placed above
# the "HANDSET (unmodified)" reference block below it, not just any
# free gap - this is the section that actually feeds that connector,
# so the two read as one visual unit instead of this one floating
# unlabelled above CONTROLLER (where it used to sit, left over from
# when U2 was still on this board and JP4 didn't exist yet).
s.note("HANDSET INTERFACE", 520, 300, 2.8)
# SW_UP/SW_DN/ISENSE all arrive here via JPSNS2 (the destination half
# of JPSNS's pigtail, up by U2 - see above) instead of a direct wire,
# now that U2 isn't on this board - one 3-pin connector, matching JP2
# bundling all three onto one physical plug on the other end (a
# separate JP6 near R4/R5 used to take ISENSE alone, which implied a
# second cable/connector that was never actually drawn - ISENSE now
# leaves this connector like its other two pins and just carries the
# label over to R4/R5 the same way WDOG does).
NODEX = {PIN["SW_UP"]: 540.0, PIN["SW_DN"]: 550.0}
JPSNS2_X = 520.0
# Pin 1's offset from its own symbol origin is -2.54 (see JP3.offset) -
# this Y puts pin 1 exactly on R11's row and, since TB3/R11/R14 already
# share that same 2.54mm pitch, pin 2 lands on R14's row too.
JPSNS2_Y = 342.0
s.place(JP3, "JP4", "sense pigtail", JPSNS2_X, JPSNS2_Y, mirror="y",
        val_at=(JPSNS2_X, JPSNS2_Y - 15.24))
jpsns2_pins = {}
# Mirrored so pins exit RIGHT, toward R11/R14/TB3, instead of left into
# open space - the old left-exit layout needed a "drop down 8mm, jog
# right" detour just to turn around, which both crossed pin 2's own
# approach wire (the ordering fix that used to live here) and left the
# SW_UP/SW_DN/ISENSE labels dangling off to the side instead of sitting
# on the wire they name. With pins already facing the right way and
# pin 1/pin 2 landing directly on R11's/R14's rows, each label can just
# sit inline on a single straight wire per signal.
# SW_UP/SW_DN's own labels branch off a junction on the main wire
# instead of sitting inline on it - inline put the wire to R11/R14
# visibly through the label (nothing wrong with it electrically, a
# label doesn't interrupt a wire, but it reads as if the wire pierces
# the label rather than the label just naming it) and crowded R13's own
# junction dot since the label's rendered width reached past it. Each
# stub is short and points away from its nearest neighbour row (up for
# the topmost signal, down for the bottommost) so it doesn't cross
# another row's own wire on the way to open space; the middle signal's
# stub sits past ISENSE's own wire end instead, for the same reason.
BRANCHX = {PIN["SW_UP"]: 530.0, PIN["SW_DN"]: 556.0}
BRANCHDY = {PIN["SW_UP"]: -2.54, PIN["SW_DN"]: 2.54}
for i, num in enumerate((PIN["SW_UP"], PIN["SW_DN"])):
    p = s.pin("JP4", str(i + 1))
    bx = BRANCHX[num]
    s.junction((bx, p[1]))
    s.wire((bx, p[1]), (bx, p[1] + BRANCHDY[num]))
    s.glabel(OUT[num], bx, p[1] + BRANCHDY[num])
    jpsns2_pins[num] = p
# ISENSE has nowhere local to continue on to (R4/R5 are elsewhere on
# the sheet - see below), so its wire is a plain dead-end stub with the
# label right at its tip, same as KICK/ISENSE back at U2.
isense_p = s.pin("JP4", "3")
s.wire(isense_p, (isense_p[0] + 12, isense_p[1]))
s.glabel(OUT[PIN["ISENSE"]], isense_p[0] + 12, isense_p[1])
# J3 (the board-side Mini-Fit to the handset) is dropped from this sheet
# - see symbols.py. Two 2-position screw terminals (handset signal pair,
# handset power pair) take its place, at the exact spot its two pin
# columns used to occupy, so the rest of this section doesn't need to
# change. TB3 pins point left toward the resistor dividers next to U2 -
# HND_A/HND_B go there. TB4 pins point right, so +3V3/GND tap off to its
# right instead (no README circuit-number constraint here like TB1/TB2
# have, so sides are assigned for routing, not to match an external
# reference). Same row as JP4/R11 (pin 1 shares the 2.54mm pitch too),
# so no vertical nudge is needed to land it exactly.
s.place(TERM2, "TB3", "signal pair", 584.14, jpsns2_pins[PIN["SW_UP"]][1])
# mirror="y": TB4's wire goes right (to +3V3/GND), not left - unmirrored,
# its pins (and so its body) would sit on the wrong side, putting that
# wire through TB4 itself instead of clear of it. Moved right of where
# J3's own pin 3/4 column used to be, same reasoning as TB2.
s.place(TERM2, "TB4", "power pair", 599.59, jpsns2_pins[PIN["SW_UP"]][1],
        mirror="y")
for num, rs, tref, jn in ((PIN["SW_UP"], "R11", "TB3", "1"),
                          (PIN["SW_DN"], "R14", "TB3", "2")):
    p = jpsns2_pins[num]
    nx = NODEX[num]
    s.wire(p, (nx, p[1]))
    s.junction((nx, p[1]))
    s.place(R_, rs, "4k7", nx + 25, p[1], angle=90)
    s.wire((nx, p[1]), s.pin(rs, "1"))
    # R14's own pin2 lands exactly on TB3's pin here (25mm centres was
    # tuned for R11's own gap, not this one) - wire() itself drops a
    # zero-length segment like this rather than drawing an invisible
    # stub between two already-coincident points. R11's own pin2 does
    # NOT land on TB3's row - jog vertically at R11's own column first
    # (not TB3's: that column is already R14's own wire down to TB3
    # pin 2, and landing a second wire on it would overlap that run)
    # rather than drawing a straight diagonal between the two.
    r2, tb = s.pin(rs, "2"), s.pin(tref, jn)
    if r2[0] == tb[0] or r2[1] == tb[1]:
        s.wire(r2, tb)
    else:
        s.wire(r2, (r2[0], tb[1]), tb)

# R13/R15 share R13's row (SW_UP's) instead of each sitting on its own
# signal's row - SW_UP/SW_DN are only 2.54mm apart, so R15 at SW_DN's
# own height would put its body right in SW_UP's horizontal wire above.
# R15 drops its own short stub down to SW_DN's row instead. Shifted up
# an extra 8mm from a plain -3.81 (just clearing the row below) so the
# +3V3 tap wire above isn't stretched so much longer than the drop to
# the row below - was a 16.83mm run up vs. under 8mm down.
pullup_y = jpsns2_pins[PIN["SW_UP"]][1] - 3.81 - 8
for num, rp in ((PIN["SW_UP"], "R13"), (PIN["SW_DN"], "R15")):
    nx = NODEX[num]
    s.place(R_, rp, "100k", nx, pullup_y)
    # rtop (pin 1) sits ABOVE pin 2 (smaller y) - the +3V3 tap must go
    # further up (smaller y still), not down past y=80: a wire from pin
    # 1 down through pin 2's own coordinate would short the resistor out
    # (pin 2 sitting exactly on that wire's path) and tie +3V3 straight
    # onto the SW_UP/SW_DN node - which is exactly the short ERC found.
    rtop = s.pin(rp, "1")
    s.wire(rtop, (rtop[0], 315))
    tap(nx, 315, V3)
    rbot = s.pin(rp, "2")
    junc_y = jpsns2_pins[num][1]
    if rbot[1] != junc_y:
        s.wire(rbot, (rbot[0], junc_y))
    s.junction((nx, junc_y))

j3_3v3, j3_gnd = s.pin("TB4", "1"), s.pin("TB4", "2")
s.wire(j3_3v3, (j3_3v3[0] + 6, j3_3v3[1]))
tap(j3_3v3[0] + 6, j3_3v3[1], V3)
s.wire(j3_gnd, (j3_gnd[0] + 6, j3_gnd[1]))
gnd_tap(j3_gnd[0] + 6, j3_gnd[1])
# Centered under TB3/TB4 (note() anchors text at its left edge, so
# offset by half the estimated string width), a bit below their own
# row - clear of TB3/TB4's bodies but still inside the HANDSET
# INTERFACE section above the "HANDSET (unmodified)" box below it.
NOTE_TEXT = "handset sees 3V3 only - 29V never reaches it"
j3_cx = (s.pin("TB3", "1")[0] + s.pin("TB4", "1")[0]) / 2
note_y = jpsns2_pins[PIN["SW_UP"]][1] + 20
s.note(NOTE_TEXT, j3_cx - len(NOTE_TEXT) * 1.7 * 0.6 / 2, note_y, 1.7)

# ===================================================== watchdog + gating ==
s.note("WATCHDOG + GATING", 250, 80, 2.8)
# U3 is the real 74LS123 now (see symbols.py) - unit 1 (A/B/Clr/Cext/
# RCext/Q, the half this design actually uses) kept at KICK's height
# purely for layout tidiness now (KICK arrives via a hand-soldered
# pigtail into JP2, not a drawn wire, so this is no longer load-bearing
# for a straight line - just a reasonable row to put U3 on). Unit 3
# (shared VCC/GND) is a separate placement above it, Kicad's convention
# for multi-unit parts.
U3X = 300.0
_, a_py = MONO.offset("1", unit=1)
u3_y = pins[PIN["KICK"]][1] + a_py
s.place(MONO, "U3", "74HC123 250ms", U3X, u3_y, unit=1)
# Unit 3 (shared VCC/GND) sits beside unit 1 now, same row, instead of
# above it - default ref/value placement (beside, not above) already
# suits a power-only unit with no body room above.
s.place(MONO, "U3", "74HC123 250ms", U3X + 21.59, u3_y, unit=3)

pa = s.pin("U3", "1", unit=1)
# KICK arrives here via JPDRV2, the destination half of JPDRV's pigtail
# (see the MCU-side placement above) - wired together with DIR_A/DIR_B/
# PWM below, once their own gate-input points exist too.

# B and Clr share ONE +5V flag now (this design never retriggers or
# clears, so both just need to sit high) - a single vertical bus feeds
# both pins off the same flag instead of each getting its own local tap.
pb = s.pin("U3", "2", unit=1)
pclr = s.pin("U3", "3", unit=1)
BX = 280.67
b_bend = (BX, pb[1])
s.wire(pb, b_bend)
s.wire(b_bend, (BX, 108.95))
tap(BX, 108.95, V5)
s.wire(b_bend, (BX, pclr[1]))
s.wire((BX, pclr[1]), pclr)
s.junction(b_bend)

pvcc = s.pin("U3", "16", unit=3)
s.wire(pvcc, (pvcc[0], 108.95))
tap(pvcc[0], 108.95, V5)
pgnd = s.pin("U3", "8", unit=3)
s.wire(pgnd, (pgnd[0], 147.32))
gnd_tap(pgnd[0], 147.32)

# Cext/RCext tied together (per the 74HC123 R/C timing configuration),
# feeding in from a shared row to their left instead of reaching back
# across the body. R3 hangs down from its own +5V flag onto that row;
# C3 (now horizontal - rotated 90, was vertical) sits directly on it.
p14, p15 = s.pin("U3", "14", unit=1), s.pin("U3", "15", unit=1)
ROW_Y = (p14[1] + p15[1]) / 2
s.wire((p14[0], ROW_Y), p14)
s.wire((p14[0], ROW_Y), p15)
s.junction((p14[0], ROW_Y))

R3X = 265.43
s.place(R_, "R3", "100k", R3X, ROW_Y - 3.81)
r3_hi, r3_lo = s.pin("R3", "1"), s.pin("R3", "2")
s.wire(r3_hi, (r3_hi[0], 108.95))
tap(r3_hi[0], 108.95, V5)
s.wire(r3_lo, (p14[0], ROW_Y))

C3X = 257.81
s.place(C_, "C3", "2u2", C3X, ROW_Y, angle=90)
c3_l, c3_r = s.pin("C3", "1"), s.pin("C3", "2")
s.wire(c3_r, r3_lo)

GNDX = 248.92
s.wire(c3_l, (GNDX, ROW_Y))
gnd_tap(GNDX, ROW_Y)

# Real part: all three gates are units of ONE 74LS08 package (ref "U6"),
# not three separate ICs the way the old hand-drawn symbol modelled them
# - "three gates of one 74HC08" was already true before, this just makes
# the schematic say so instead of the note off to the side saying it.
# Pin numbers per unit (top input, bottom input, output) aren't in unit
# order (unit 3 draws pins 9/10/8, not 7/8/9) since they're the real
# package's own numbering, not something chosen for this layout.
GATE_PINS = {1: ("1", "2", "3"), 2: ("4", "5", "6"), 3: ("9", "10", "8")}
# Which SIGNAL drives which unit is NOT arbitrary, despite the gates
# being electrically identical: unit 1's output is hardwired below to
# Q2 (-> K1 = up, so it must carry DIR_A), unit 2's to Q3 (-> K2 = down,
# DIR_B), and unit 3's to the Q4/Q5 push-pull -> Q1 (the PWM FET, so it
# must carry PWM) - see the Q2/Q3 loop and `pu6 = ...unit=3` below. (An
# earlier version of this reassignment tried swapping which row units 2
# and 3 are drawn on instead of picking different MCU pins - don't: Q3's
# and Q4/Q5's own placement are each derived from their driving unit's
# row, so that swap dragged those parts 37mm into each other and
# reintroduced shorts elsewhere. Leave this tuple's row values matching
# unit-number order.)
GATES = ((1, PIN["DIR_A"], "R1", 215), (2, PIN["DIR_B"], "R2", 255),
         (3, PIN["PWM"], "R6", 292))
# Q sits on the right, same side as the AND gates - it clears the body's
# height first before jogging to the shared WDOG column, same reasoning
# as before (jogging left immediately at pin height would cut through
# the body). WDX shares BX's column (B/Clr's own +5V bus, above) purely
# for visual tidiness - the two buses don't overlap in Y.
WDX = BX
pq = s.pin("U3", "13", unit=1)
# WDOG wires to the top input pin below, not the bottom one - swapped
# from the name-matches-position default so WDOG (fed from a column left
# of everything) lands on top instead of bottom - so the bus needs that
# pin's offset, same for every unit (all three sit at the same py).
_, top_py = AND2.offset("1", unit=1)
last_a_y = GATES[-1][3] - top_py
s.wire(pq, (pq[0], pq[1] + 20), (WDX, pq[1] + 20), (WDX, last_a_y))
s.label("WDOG", WDX, pq[1] + 26)

# DIR_A/DIR_B/PWM all arrive here via a hand-soldered pigtail from U2's
# own header pins (see the MCU-side glabels above) now - stash their
# gate-input points during the loop and wire JP5 to them, plus KICK's
# `pa` from above, once it's placed below.
gate_targets = {}
U6X = 310.0
for i, (unit, src, rref, y) in enumerate(GATES):
    top, bottom, out = GATE_PINS[unit]
    s.place(AND2, "U6", "74HC08", U6X, y, unit=unit)
    p_a, p_b = s.pin("U6", top, unit=unit), s.pin("U6", bottom, unit=unit)
    gate_targets[src] = p_b
    s.wire((WDX, p_a[1]), p_a)
    if i < len(GATES) - 1:
        s.junction((WDX, p_a[1]))
    # boot-safe pulldown, tapped right at this gate's own bottom pin
    # instead of back near the MCU - keeps its column local to one
    # gate's height, so it never crosses another gate's approach line.
    # Runs down from there, away from this gate's own top pin 2.54mm
    # above, rather than up into it.
    rx = p_b[0] - 6
    s.place(R_, rref, "10k", rx, p_b[1] + 3.81)
    s.junction((rx, p_b[1]))
    r_bot = s.pin(rref, "2")
    s.wire(r_bot, (rx, r_bot[1] + 12))
    gnd_tap(rx, r_bot[1] + 12)

# JP5: the connector end of JPDRV's pigtail (U2's own pins are the
# other end, see the MCU-side glabels above - no PCB copper or
# connector there). One pin each for KICK/DIR_A/DIR_B/PWM, each with
# its own matching label. Placed in the open block left of U3/U6
# (below the "handset sees 3V3 only" note, above U6A) instead of
# pinned to pa's own row - anywhere near pa or the gates themselves
# put the connector's body right on top of U3's own symbol (its pins,
# reference and value text all landed inside U3's own footprint - not
# just visually crowded, actually overlapping other components' pins).
# Genuinely empty ground here means no target lines up with any pin
# for a "free" direct wire, so every pin jogs through its own column.
JP5_X, JP5_Y = 200.0, 180.0
s.place(JP4, "JP5", "drive pigtail", JP5_X, JP5_Y, mirror="y")
jp5_pins = [s.pin("JP5", str(i + 1)) for i in range(4)]
targets = [pa, gate_targets[PIN["DIR_A"]], gate_targets[PIN["DIR_B"]],
           gate_targets[PIN["PWM"]]]
labels = ["KICK", "DIR_A", "DIR_B", "PWM"]
# Each pin gets its own column (not target[0] directly) - landing two
# on the same x would short their vertical runs together, UNLESS (as
# with KICK/PWM here) their spans never overlap in y: KICK's run only
# exists between its own row and pa above it, PWM's only between its
# own row and U6C below - sharing a column is free reuse, not a risk,
# when one signal's whole vertical lives strictly above the shared
# row and the other's strictly below.  DIR_A/DIR_B stay left of WDOG's
# own column (280.67) and are nested by target depth (DIR_B's gate is
# further down, so it gets the outer/left column; DIR_A's is nearer,
# so it gets the inner/right one) - the same reasoning as JP4's pin
# ordering earlier: the run that has to pass the other's gate row on
# its way down needs to do it on a column outside that gate's own
# final approach, or its vertical crosses that horizontal into the
# gate.
JP5COL = (273.05, 278.13, 275.59, 273.05)
for jp_pin, target, label, col in zip(jp5_pins, targets, labels, JP5COL):
    s.wire(jp_pin, (col, jp_pin[1]), (col, target[1]), target)
    s.glabel(label, jp_pin[0], jp_pin[1])

s.note("hold drive lines safe before boot", 250, 300, 1.5)


# unit 5 (shared VCC/GND) - placed below U6C (the last gate) instead of
# above everything, its own local taps same as U3's power unit. Ref/
# value beside it, not above, same reasoning as U3's power unit. Below
# was previously above (y=200), which put its GND stub right through
# U6A's own body (the first gate, at y=215) - moving past the last gate
# instead gives both stubs open space to land in, so they're shorter too.
U6P_Y = 332
s.place(AND2, "U6", "74HC08", U6X, U6P_Y, unit=5,
        ref_at=(U6X + 6.35, U6P_Y - 1.27),
        val_at=(U6X + 6.35, U6P_Y + 1.27), justify="left")
u6_vcc, u6_gnd = s.pin("U6", "14", unit=5), s.pin("U6", "7", unit=5)
s.wire(u6_vcc, (u6_vcc[0], u6_vcc[1] - 4))
tap(u6_vcc[0], u6_vcc[1] - 4, V5)
s.wire(u6_gnd, (u6_gnd[0], u6_gnd[1] + 4))
gnd_tap(u6_gnd[0], u6_gnd[1] + 4)

# Discrete push-pull gate driver instead of a driver IC (see symbols.py):
# Q4 (BC337 NPN) sources from +5V, Q5 (BC327 PNP, mirrored so its
# collector points down instead of up) sinks to GND. Q4 is placed so its
# base (offset 0 from centre) lands on U6 unit 3's output height, turning
# that connection into a single straight line instead of a jog through a
# resistor. Q5 sits a short gap below, its own emitter aligning with
# Q4's once mirrored; the shared emitter then runs down to Q1's gate
# (Q1 isn't placed yet at this point in the file, but its position is
# fixed, so the offset is computed against that future position rather
# than reordering the file to place it earlier).
pu6 = s.pin("U6", GATE_PINS[3][2], unit=3)
# The real NMOS part's drain/source sit 2.54mm off centre (unlike the old
# hand-drawn symbol, which had them on the same vertical line as the
# part's own placement point) - every NMOS below is placed 2.54mm left
# of its drain/source's intended column (625) so those pins land exactly
# on it, keeping the vertical runs below straight instead of jogged.
NMOS_DX, _ = NMOS.offset("2")
DRAIN_X = 395.0  # shared column for Q1/Q2/Q3's drain/source stack
Q1_X, Q1_Y = DRAIN_X - NMOS_DX, 330.0
gate_px, gate_py = NMOS.offset("1")
q1_gate = (Q1_X + gate_px, Q1_Y - gate_py)
BJT_GAP = 4.0
_, npn_e_py = BJT_NPN.offset("3")
q4_y = pu6[1]
q5_y = q4_y - 2 * npn_e_py + BJT_GAP
BJT_X = 355.0
s.place(BJT_NPN, "Q4", "BC337", BJT_X, q4_y)
s.place(BJT_PNP, "Q5", "BC327", BJT_X, q5_y, mirror="x")

q4_c, q4_b, q4_e = s.pin("Q4", "1"), s.pin("Q4", "2"), s.pin("Q4", "3")
q5_c, q5_b, q5_e = s.pin("Q5", "1"), s.pin("Q5", "2"), s.pin("Q5", "3")

s.wire(q4_c, (q4_c[0], q4_c[1] - 6))
tap(q4_c[0], q4_c[1] - 6, V5)
s.wire(q5_c, (q5_c[0], q5_c[1] + 6))
gnd_tap(q5_c[0], q5_c[1] + 6)

s.wire(q4_b, q5_b)
s.junction(q4_b)
s.wire(q4_e, q5_e)
s.junction(q4_e)
mid_x = q4_e[0] + 6
s.wire(q4_e, (mid_x, q4_e[1]), (mid_x, q1_gate[1]), q1_gate)

# base resistor, straight in line with U6C's output and Q4's base.
r7_x = (pu6[0] + q4_b[0]) / 2
s.place(R_, "R7", "1k", r7_x, pu6[1], angle=90)
s.wire(pu6, s.pin("R7", "1"))
s.wire(s.pin("R7", "2"), q4_b)

# =============================================================== drive ====
s.note("DRIVE", 395, 80, 2.8)
# Q2/Q3 are placed level with their own gate (U6 units 1/2) - gate pin
# and NMOS gate pin are both offset 0 from centre, so this turns each
# gate-to-transistor connection into one straight line.
for ref, gate_unit in (("Q2", 1), ("Q3", 2)):
    pgy = s.pin("U6", GATE_PINS[gate_unit][2], unit=gate_unit)
    s.place(NMOS, ref, "2N7000", DRAIN_X - NMOS_DX, pgy[1])
    s.wire(pgy, s.pin(ref, "1"))
    ps = s.pin(ref, "3")
    s.wire(ps, (DRAIN_X, ps[1] + 15))
    gnd_tap(DRAIN_X, ps[1] + 15)

s.place(NMOS, "Q1", "IRLZ44N", Q1_X, Q1_Y,
        footprint="Package_TO_SOT_THT:TO-220-3_Vertical")
q1_drain, q1_source = s.pin("Q1", "2"), s.pin("Q1", "3")
# Gate already wired to the Q4/Q5 push-pull output above.
GND_GAP = 8.0
s.wire(q1_source, (DRAIN_X, q1_source[1] + GND_GAP))
gnd_tap(DRAIN_X, q1_source[1] + GND_GAP)

MRETX = 450.0
# D5 sits directly above Q1 (same x) instead of off to the side, close
# enough that the gaps here (Q1 to D5, D5 to the VSW tap) are short
# rather than stretched out - its pin 2 lands exactly on the corner
# already in Q1's drain wire above, so it taps in with a junction
# instead of its own separate run over.
D5_GAP = 8.0
s.place(DH, "D5", "SB560", DRAIN_X, q1_drain[1] - D5_GAP - 3.81, angle=270,
        footprint="Diode_THT:D_DO-201AD_P12.70mm_Horizontal")
d5_bottom = s.pin("D5", "2")
s.wire(q1_drain, (DRAIN_X, d5_bottom[1]), (MRETX, d5_bottom[1]))
s.junction(d5_bottom)
d5_top = s.pin("D5", "1")
VS_GAP = 8.0
s.wire(d5_top, (DRAIN_X, d5_top[1] - VS_GAP))
tap(DRAIN_X, d5_top[1] - VS_GAP, VS)

# K1/K2 rotated 90 from the real part's default orientation - coil
# (A1/A2) on the bottom row, switch (NC/NO/COM) on top, instead of
# coil-left/switch-right. NC and NO both end up on the top-left now, so
# VSW and MRET (which sit to the left) reach them directly instead of
# needing a jog on one side and a reach-around on the other; COM ends
# up top-right, reaching U5/J2 (also to the right) the same way.
# A1 (bottom-left) is closer to the FET than A2 is at this rotation, so
# it's the driven pin now (was A2) - the flyback diode's cathode still
# faces whichever pin is tied to +5V (A2 now), same rule as before,
# just the two coil pins have swapped roles.
A1_OFF = 5.08  # A1's own y offset from centre at this rotation
COMX = {}
for i, (ref, val, qref, dref) in enumerate((
        ("K1", "energized = UP (raises desk)", "Q2", "D2"),
        ("K2", "energized = DOWN (lowers desk)", "Q3", "D6"))):
    drain_y = s.pin(qref, "2")[1]
    k_y = drain_y - A1_OFF
    # ref/value beside the body (half-width 10.16 + 1.27, left-justified),
    # not above it - matches Kicad's own placement for this part.
    s.place(RLY, ref, val, 490, k_y, angle=90,
            ref_at=(490 + 11.43, k_y - 1.27),
            val_at=(490 + 11.43, k_y + 1.27), justify="left")
    c_drive, c_5v = s.pin(ref, "A1"), s.pin(ref, "A2")
    s.wire(s.pin(qref, "2"), c_drive)

    # D2/D6 sit below the coil row now (were beside it) - centred on
    # the relay's own x so both pins land clear of the body's left/
    # right edges, at the body's own bottom edge so neither connecting
    # wire needs to travel far to clear it.
    # mirror="y" (not a 180 rotation - flips the reference/value text
    # upside down, mirror doesn't) gets the same K-right/A-left pins.
    s.place(DH, dref, "flyback", 490, k_y + 15.24, mirror="y")
    d_k, d_a = s.pin(dref, "1"), s.pin(dref, "2")

    top_tap_y = c_5v[1] - 4
    s.wire(c_5v, (c_5v[0], top_tap_y))
    tap(c_5v[0], top_tap_y, V5)
    s.wire(c_5v, (c_5v[0], d_k[1]), d_k)
    s.junction(c_5v)

    s.wire(c_drive, (c_drive[0], d_a[1]), d_a)
    s.junction(c_drive)

    # NC ties to VSW to the left - straight, no jog, same idea as
    # before just rotated: it already points that way, clear of the
    # body.
    nc = s.pin(ref, "12")
    s.wire(nc, (nc[0] - 4, nc[1]))
    tap(nc[0] - 4, nc[1], VS)

    # NO ties to the shared MRET column, also to the left.
    no = s.pin(ref, "14")
    s.wire(no, (MRETX, no[1]))
    s.junction((MRETX, no[1]))

    # COM points right now (was down) - K1's goes straight to U5 (see
    # below), K2's needs its own column up to J2, each still on its own
    # x so the two runs can't end up coincident.
    com = s.pin(ref, "11")
    comx = 515.0 + i * 10
    s.wire(com, (comx, com[1]))
    COMX[ref] = comx

s.wire((MRETX, s.pin("K1", "14")[1]), (MRETX, d5_bottom[1]))
# exactly on the vertical run (was offset +2 in x, off the wire and
# thus not actually connected to the net it names).
s.label("MRET", MRETX, d5_bottom[1] - 6)

# current sense sits to the right of K1 and below J2, clear of both,
# instead of sandwiched between them - real part puts VCC/GND top/
# bottom and IP+/IP- stacked on the left (see symbols.py), unlike the
# old placeholder's left/right split, so the wiring here is rerouted to
# match rather than forcing the part into the old layout. IP+/IP- are
# interchangeable for this design (README 4.4 - either leg works,
# current direction isn't used) - IP- (the lower pin) goes to K1 since
# K1 sits below; IP+ (the upper pin) goes to J2's MOT_B since J2 sits
# above. FILTER (pin 6) is left unconnected - the datasheet shows it
# tied to GND through a cap for noise filtering, not fitted here; out
# of scope for this migration, worth revisiting.
# Underneath J2 (same x) leaves ample room on every side, clear of
# MRETX (now on the far side of K1/K2, to their left) and clear of the
# relay bodies too.
U5X = 560.0
# Y chosen so IP- lands exactly on K1's own COM row (now pointing right
# after the rotation above) - straight wire instead of a jog.
U5Y = s.pin("K1", "11")[1] - 5.08
s.place(ACS, "U5", "ACS724xLCTR-05AB", U5X, U5Y)
p_vcc, p_gnd = s.pin("U5", "8"), s.pin("U5", "5")
s.wire(p_vcc, (p_vcc[0], p_vcc[1] - 6))
tap(p_vcc[0], p_vcc[1] - 6, V5)
s.wire(p_gnd, (p_gnd[0], p_gnd[1] + 6))
gnd_tap(p_gnd[0], p_gnd[1] + 6)

pk1 = (COMX["K1"], s.pin("K1", "11")[1])
ip_minus = s.pin("U5", "3")
# pk1 and ip_minus already share a y (U5Y is chosen for exactly this),
# so a straight 2-point wire - a 3-point version with a now-coincident
# middle waypoint produced an invisible zero-length first segment.
s.wire(pk1, ip_minus)
s.label("DRV_UP", COMX["K1"], pk1[1])
ip_plus = s.pin("U5", "1")
pk2 = (COMX["K2"], s.pin("K2", "11")[1])

# J2 (the board-side Mini-Fit to the motor housing) is dropped from this
# sheet - see symbols.py. In its place, two 2-position screw terminals
# (motor pair, supply pair) are placed so their pins land exactly where
# J2's own two pin columns used to be, so nothing downstream needs to
# change: same reasoning J2 always had for sitting here (above and to
# the right of U5, ample room, MOT_A/MOT_B each get their own column on
# the way up).
s.place(TERM2, "TB1", "motor pair", 559.74, 119.05)
# mirror="y": TB2's wire goes right (into the SUPPLY chain), not left -
# unmirrored, its pins (and so its body) would sit on the wrong side,
# putting that wire through TB2 itself instead of clear of it. Moved
# right of where J2's own pin 3/4 column used to be (12.7mm from TB1,
# same as a single 2x2 connector's own column spacing) for clearance -
# no longer one physical part, no reason to sit that close.
s.place(TERM2, "TB2", "supply pair", 574.59, 119.05, mirror="y")
# MOT_A/MOT_B order on pin 1/2 is still provisional - MOT_A is defined by
# function (README 1.6: whichever conductor raises the desk), so if
# bring-up shows this backwards, the fix is relabelling here, not
# rewiring anything.
j2_mota, j2_motb = s.pin("TB1", "1"), s.pin("TB1", "2")
j2_vsw, j2_gnd = s.pin("TB2", "1"), s.pin("TB2", "2")
s.wire(pk2, (pk2[0], j2_mota[1]), j2_mota)
s.wire(ip_plus, (ip_plus[0], j2_motb[1]), j2_motb)
# GND_Y (defined properly below, with the rest of SUPPLY's grounds) is
# used here too so TB2's own GND symbol lines up with that whole row
# instead of sitting at its own, different height.
GND_Y = j2_vsw[1] + 16.0
# Straight diagonal before (different x AND y, no bend) - now a proper
# jog: across first, then down.
s.wire(j2_gnd, (j2_gnd[0] + 6, j2_gnd[1]), (j2_gnd[0] + 6, GND_Y))
gnd_tap(j2_gnd[0] + 6, GND_Y)

# ============================================================== supply ====
# Moved here (next to TB2) instead of its own block elsewhere on the
# sheet, and wired to TB2.1 with a literal wire instead of a same-named
# VSW tap - this is the actual, physical entry point for the incoming
# supply, so drawing it as a real connection is more accurate than an
# abstract label match (used everywhere else VSW is needed, which is
# still the right call there - this is the one spot that's the source,
# not just another consumer). One flattened chain, left to right, all on
# the same rail y (TB2.1's own height) so the whole 29V-to-5V path is a
# single straight line, no jogs. Horizontal spacing standardized to GAP
# between facing pins (not component centres, which would leave visibly
# uneven gaps given how much each part's own width differs).
s.note("SUPPLY", j2_vsw[0] + 15, 80, 2.8)

# JP6: the mate for JP3's power pigtail (U2 PIGTAILS block) - the +5V
# this board's own buck converter makes below, and the +3V3 U2's
# onboard regulator feeds back for the rest of this board, meet here.
# Previously JP3 had no destination at all (just floating taps onto
# already-global rails, with nothing to show where the physical wires
# actually land) - placed in the open gap between this heading and the
# main 29V-to-5V row rather than tacked onto either. GND (pin 3) shares
# its column with +3V3 (pin 2), same reasoning as JP3 itself: their
# spans run opposite directions from adjacent rows and never overlap.
JP6_X, JP6_Y = 650.0, 100.0
s.place(JP3, "JP6", "power pigtail", JP6_X, JP6_Y)
jp6_p5 = s.pin("JP6", "1")
s.wire(jp6_p5, (jp6_p5[0], jp6_p5[1] - 8))
tap(jp6_p5[0], jp6_p5[1] - 8, V5)
jp6_p3 = s.pin("JP6", "2")
jp6_col3g = jp6_p3[0] - 5
s.wire(jp6_p3, (jp6_col3g, jp6_p3[1]), (jp6_col3g, jp6_p3[1] - 8))
tap(jp6_col3g, jp6_p3[1] - 8, V3)
jp6_pg = s.pin("JP6", "3")
s.wire(jp6_pg, (jp6_col3g, jp6_pg[1]), (jp6_col3g, jp6_pg[1] + 8))
gnd_tap(jp6_col3g, jp6_pg[1] + 8)

SY = j2_vsw[1]
GAP = 25.0
# F1 (fuse) removed entirely - the wall supply already current-limits
# (CLAUDE.md's own hard invariant: that limit is the desk's only
# collision protection, already relied on elsewhere in this design), so
# a fuse adds little on top of it while being one more embedded part to
# replace if it ever blows. The OEM desk never had one either. PS1 (the
# wall-supply/AC-DC module) itself now lives in the LEG section - it's
# physically inside the motor housing, not on this board.
D1X = j2_vsw[0] + GAP
s.place(TVS, "D1", "33V bidir", D1X, SY + 6.35)
s.wire(j2_vsw, s.pin("D1", "1"))

C1X = D1X + GAP
s.place(C_, "C1", "220u 50V", C1X, SY + 3.81,
        footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")

U1X = C1X + GAP + 12.7  # VIN sits 12.7mm left of centre
s.place(BUCK, "U1", "LM2596HV 29V-5V", U1X, SY + 2.54)
fb_x = U1X + 12.7  # FB sits 12.7mm right of centre, same y as VIN

C2X = fb_x + GAP
s.place(C_, "C2", "220u 10V", C2X, SY + 3.81,
        footprint="Capacitor_THT:CP_Radial_D8.0mm_P3.50mm")

# Every ground drop in this section (GND_Y, set above with J2's own)
# lands on the same row - still its own symbol per drop, not a shared
# bus (see conversation) - purely so they visually line up instead of
# ending at whatever y each component's own pin happens to be at. It's
# below every pin that drops to it (the lowest, D1's, sits at SY+12.7)
# so every drop wire approaches from above - the direction gnd_tap()'s
# own short continuation expects; a row above any of these pins would
# backtrack into the wire just drawn (KiCad sees that as a second,
# overlapping segment).

d1_lo = s.pin("D1", "2")
s.wire(d1_lo, (d1_lo[0], GND_Y))
gnd_tap(d1_lo[0], GND_Y)

s.wire(s.pin("D1", "1"), s.pin("C1", "1"))
c1_hi = s.pin("C1", "1")

c1_lo = s.pin("C1", "2")
s.wire(c1_lo, (c1_lo[0], GND_Y))
gnd_tap(c1_lo[0], GND_Y)

s.wire(c1_hi, s.pin("U1", "1"))

u1_out = s.pin("U1", "2")
u1_gnd = s.pin("U1", "3")
u1_fb = s.pin("U1", "4")
u1_onoff = s.pin("U1", "5")

s.wire(u1_gnd, (u1_gnd[0], GND_Y))
gnd_tap(u1_gnd[0], GND_Y)

# ~ON/OFF floating is not a valid state - tied low for always-on.
s.wire(u1_onoff, (u1_onoff[0], GND_Y))
gnd_tap(u1_onoff[0], GND_Y)

# FB must sense VOUT externally even on this fixed-5V part - FB and
# C2's own top pin land on the same y (both = SY) already, so that's
# one straight line; OUT (below both) taps up into it with its own
# short stub instead of overlapping that line with a second wire.
c2_hi = s.pin("C2", "1")
s.wire(u1_fb, c2_hi)
s.wire(u1_out, (u1_out[0], u1_fb[1]))
s.junction((u1_out[0], u1_fb[1]))
s.junction(c2_hi)
tap(c2_hi[0], c2_hi[1], V5)

c2_lo = s.pin("C2", "2")
s.wire(c2_lo, (c2_lo[0], GND_Y))
gnd_tap(c2_lo[0], GND_Y)

# R4/R5 sit below U5's VIOUT pin now (were above) - U5 sits underneath
# J2 with nothing below it, so that's the direction with open space,
# rather than back up past U5's own VCC tap.
p_out = s.pin("U5", "7")
RX = p_out[0] + 5.08
s.place(R_, "R4", "10k", RX, p_out[1] + 6.35)
s.wire(p_out, (RX, p_out[1]), s.pin("R4", "1"))
s.place(R_, "R5", "20k", RX, p_out[1] + 19.05)
s.wire(s.pin("R4", "2"), s.pin("R5", "1"))
isense_y = (s.pin("R4", "2")[1] + s.pin("R5", "1")[1]) / 2
s.wire((RX, isense_y), (RX + 30, isense_y))
s.junction((RX, isense_y))
# No connector here any more - ISENSE now leaves on JP4's own pin 3
# along with SW_UP/SW_DN (one physical plug for all three, see the
# rocker-divider section), so this end just needs the matching label,
# the same mechanism WDOG already uses.
s.glabel("ISENSE", RX + 30, isense_y)
r5_bottom = s.pin("R5", "2")
gnd_y = r5_bottom[1] + 5
s.wire(r5_bottom, (RX, gnd_y))
s.place(GNDS, _uref(), "GND", RX, gnd_y, hide_ref=True, hide_val=True)


# ================================================================= leg ====
# SW3/D3 (top-limit branch) and SW4/D4 (bottom-limit branch) each form a
# tight switch+diode column, halfway between M1 and J1, instead of the
# old side-by-side ladder above/below M1. Both parts in a column are
# horizontal (pins left/right) - M1 is left unrotated too (the "M" in
# its own graphics would render sideways otherwise), so every pin in
# this section points left or right, never up/down.
# Box tightened to actual content (was a lot looser: 330-600 x 385-500)
# and the whole section shifted down and left to make room for HANDSET
# to its right.
s.note("LEG (unmodified)", 358, 435, 2.8)
s.box(358, 440, 475, 513)

s.place(MOT, "M1", "2R5 winding", 366.08, 476, on_board=False)
m1_plus, m1_minus = s.pin("M1", "1"), s.pin("M1", "2")

# J1 - the far end of the board's TB1/TB2 pigtail (same Molex Mini-Fit
# Jr, same Conn_02x02_Top_Bottom part - see symbols.py, J2 itself is no
# longer drawn), sitting where it actually is: inside the leg, wired
# straight to this section's own motor leads and to the PSU below,
# instead of a same-named-label match that was never actually connected
# to anything ("global" only means "matches by text anywhere on THIS
# sheet" - see NETLIST.md, this is what fixes that).
J1X, J1Y = 420.0, 476.0
# val_at pushed further down than the library's own default (5.08) - two
# lines now, and the default clearance was tuned for one, sitting right
# against the body.
s.place(CONN, "J1", "in motor housing\nmates with board pigtail (TB1/TB2)",
        J1X, J1Y, val_at=(J1X, J1Y + 6.5), on_board=False)
j1_mota, j1_motb = s.pin("J1", "1"), s.pin("J1", "2")
j1_vsw, j1_gnd = s.pin("J1", "3"), s.pin("J1", "4")

# SW3/SW4 sit a bit clear of M1's own pin row (EXTRA) instead of right
# on top of it - the M1 wire picks up a small bend to get there instead
# of landing dead straight. D3/D4 stay GAP further out again from their
# own switch, same spacing as before. mirror="y" (not a 180 rotation)
# puts the diode's cathode on the J1 side - a rotation would also flip
# the reference/value text upside down, mirror doesn't.
SWX = 390.0
EXTRA = 8.0
GAP = 12.0
# Each tie's long vertical run sits on a bus 50mil clear of both SWx's
# and Dx's own pins, rather than jogging in right off one of them - a
# short stub connects the bus back to each component's actual pin. M1
# (or J1, on the far side) ties into the same bus point, so each bus/
# row intersection is a real 3-way junction.
OUTSET = 1.27

s.place(LIM, "SW3", "top limit", SWX, m1_plus[1] - EXTRA, on_board=False)
s.place(DH, "D3", "allows down", SWX, m1_plus[1] - EXTRA - GAP, mirror="y",
        on_board=False)
sw3_l, sw3_r = s.pin("SW3", "1"), s.pin("SW3", "2")
d3_k, d3_a = s.pin("D3", "1"), s.pin("D3", "2")
lbus, rbus = sw3_l[0] - OUTSET, sw3_r[0] + OUTSET
sw3_lp, sw3_rp = (lbus, sw3_l[1]), (rbus, sw3_r[1])
s.wire(m1_plus, (m1_plus[0], sw3_lp[1]), sw3_lp)
s.wire(sw3_lp, sw3_l)
s.wire(sw3_lp, (lbus, d3_a[1]), d3_a)
s.junction(sw3_lp)
s.wire(sw3_r, sw3_rp)
s.wire(sw3_rp, (rbus, d3_k[1]), d3_k)
s.wire(sw3_rp, (j1_mota[0], sw3_r[1]), j1_mota)
s.junction(sw3_rp)

s.place(LIM, "SW4", "bottom limit", SWX, m1_minus[1] + EXTRA, on_board=False)
s.place(DH, "D4", "allows up", SWX, m1_minus[1] + EXTRA + GAP, mirror="y",
        on_board=False)
sw4_l, sw4_r = s.pin("SW4", "1"), s.pin("SW4", "2")
d4_k, d4_a = s.pin("D4", "1"), s.pin("D4", "2")
sw4_lp, sw4_rp = (lbus, sw4_l[1]), (rbus, sw4_r[1])
s.wire(m1_minus, (m1_minus[0], sw4_lp[1]), sw4_lp)
s.wire(sw4_lp, sw4_l)
s.wire(sw4_lp, (lbus, d4_a[1]), d4_a)
s.junction(sw4_lp)
s.wire(sw4_r, sw4_rp)
s.wire(sw4_rp, (rbus, d4_k[1]), d4_k)
s.wire(sw4_rp, (j1_motb[0], sw4_r[1]), j1_motb)
s.junction(sw4_rp)

# PSU (see symbols.py) mirrored so its output faces J1 (to its left) and
# mains faces further right/away - 50mil below J1's own Y (not J1Y
# itself, nor j1_vsw's) since that's the one offset, still on-grid,
# that actually lines the two bodies up.
PSUX = j1_vsw[0] + 20
s.place(PSU, "PSU1", "29V 1.8A 52W", PSUX, J1Y + 1.27, mirror="y",
        on_board=False)
# Neither Vout pin lands on its own J1 pin's row (both are 1.27mm off,
# in opposite directions) - each jog bends at the horizontal midpoint
# between the two connectors instead of hugging one end, so both wires
# read the same way.
psu_plus, psu_minus = s.pin("PSU1", "6"), s.pin("PSU1", "3")
midx = (psu_plus[0] + j1_vsw[0]) / 2
s.wire(psu_plus, (midx, psu_plus[1]), (midx, j1_vsw[1]), j1_vsw)
s.wire(psu_minus, (midx, psu_minus[1]), (midx, j1_gnd[1]), j1_gnd)

# Mains L/N - power.kicad_sym's generic "AC" flag reused per instance
# (see symbols.py), same mechanism as this design's own +5V/VSW/GND taps.
# Both flags land on the same row, side by side, instead of stacked
# 5.08mm apart directly above their own pins - at that spacing the two
# flags' own circles overlapped each other. N jogs over to sit next to
# L; the tap()/gnd_tap() convention of ending 1mm short of the flag's
# own placement point (so the wire reaches the pin, not just the
# stub) applies here too - the previous version skipped that last
# 1mm and left both flags actually disconnected.
# AC_FLAG's own pin sits exactly at its placement point (unlike
# GNDS/RAILS' tap()/gnd_tap() convention, which places the flag 1mm
# past the wire's end on purpose) - so the wire's endpoint and the
# flag's placement must be the same point, not offset from each other.
psu_l, psu_n = s.pin("PSU1", "1"), s.pin("PSU1", "2")
FLAGY = psu_l[1] - 7.62
s.wire(psu_l, (psu_l[0], FLAGY))
s.place(AC_FLAG, _uref(), "L", psu_l[0], FLAGY, hide_ref=True)
s.wire(psu_n, (psu_n[0] + 8, psu_n[1]), (psu_n[0] + 8, FLAGY))
s.place(AC_FLAG, _uref(), "N", psu_n[0] + 8, FLAGY, hide_ref=True)

# ============================================================= handset ====
# DOWN/UP rockers as found (README S2.5), side by side the same way the
# real buttons are (down left, up right) - and facing each other, so
# their two shared contacts (pins 1/3, the pair every rocker shares -
# yellow/white in S1.4) tie together with a plain direct wire instead of
# needing a bus/offset column. COM (pin 2, what the box actually reads
# via J3 as a dry contact - see CONTROLLER) ends up facing outward on
# both: DOWN's default orientation already puts it on the left, UP needs
# mirror="y" (not a 180 rotation - flips the reference/value text too)
# to put it on the right, facing J4.
DOWN_X = 545.0
UP_X = 565.0
SWY = 476.0
# Same box size as LEG's (117 x 73) - not just each tightened to its own
# content, matching sizes side by side reads a lot calmer.
s.note("HANDSET (unmodified)", 520, 435, 2.8)
s.box(520, 440, 637, 513)

s.place(ROCKER, "SW1", "DOWN rocker", DOWN_X, SWY, on_board=False)
s.place(ROCKER, "SW2", "UP rocker", UP_X, SWY, mirror="y", on_board=False)
down_a, down_com, down_c = s.pin("SW1", "1"), s.pin("SW1", "2"), s.pin("SW1", "3")
up_a, up_com, up_c = s.pin("SW2", "1"), s.pin("SW2", "2"), s.pin("SW2", "3")
s.wire(down_a, up_a)
s.wire(down_c, up_c)

J4X = UP_X + 45
# val_at pushed further down than the library's own default (5.08), same
# reasoning as J1 - two lines now, not one.
s.place(CONN, "J4", "in handset\nmates with board pigtail (TB3/TB4)",
        J4X, SWY, val_at=(J4X, SWY + 6.5), on_board=False)
j4_1, j4_2, j4_3, j4_4 = (s.pin("J4", str(n)) for n in (1, 2, 3, 4))

# UP's COM is already adjacent to J4 - straight in, no jog needed.
s.wire(up_com, (j4_1[0], up_com[1]), j4_1)

# The shared contacts each branch to J4 from the midpoint of the tie
# between SW1 and SW2 - not from either rocker's own pin - then wrap
# clear around UP's body (one over the top, one under the bottom) to
# reach it, same as DOWN's COM below.
mid_a = ((down_a[0] + up_a[0]) / 2, down_a[1])
mid_c = ((down_c[0] + up_c[0]) / 2, down_c[1])
s.junction(mid_a)
s.junction(mid_c)

TOPY = SWY - 15.0
s.wire(mid_a, (mid_a[0], TOPY), (j4_3[0], TOPY), j4_3)
BOTY_C = SWY + 12.0
s.wire(mid_c, (mid_c[0], BOTY_C), (j4_4[0], BOTY_C), j4_4)

# DOWN's COM has to get past UP's own body to reach J4 too - wraps
# under, further out than the shared-C wire above.
BOTY_COM = SWY + 20.0
s.wire(down_com, (down_com[0], BOTY_COM), (j4_2[0], BOTY_COM), j4_2)

notes = [
    "SIMPLE IN-LINE DRIVE.  The box sits in the 4-core cable and owns the winding permanently.",
    "Reverting is physical:   motor - box - handset   becomes   motor - handset.",
    "",
    "The handset is no longer in the motor circuit.  It is fed 3V3 and its rockers are read as",
    "dry contacts - high at rest through the OEM NC contact, low when pressed.  Because 29V can",
    "never appear on those conductors, no clamp diodes are needed.",
    "",
    "POLARITY (measured on the 4-pin Mini-Fit Jr, circuits numbered on the housing):",
    "    circuit 1 = motor      circuit 3 = supply +",
    "    circuit 2 = motor      circuit 4 = supply -",
    "    circuit 2 positive, circuit 1 negative  =  UP.   Reverse = DOWN.",
    "MOT_A is defined as the conductor that must be POSITIVE to raise the desk",
    "(circuit 2).  MOT_B is circuit 1.",
    "",
    "K1 / K2 reproduce the OEM rest behaviour:",
    "    both off  ->  both winding ends on VSW  =  BRAKE",
    "    K1 on -> MOT_B to return, MOT_A stays positive  =  UP",
    "    K2 on -> MOT_A to return, MOT_B stays positive  =  DOWN",
    "No combination of relay states can short the supply; there is no shoot-through failure mode.",
    "",
    "SEQUENCING: relays change state only with Q1 off and current decayed (~50ms).  On a watchdog",
    "trip Q1 turns off in microseconds while the relays take milliseconds to release, so the",
    "contacts are cold-switched even in a fault.  Loss of drive is coast, which is safe because",
    "the spindle is self-locking and holds the load unpowered.",
    "",
    "U5 sits in the motor leg so it reads current during freewheel as well as during the PWM",
    "on-time, which a low-side shunt would not.  ISENSE must be on ADC1 (ADC2 dies with WiFi).",
    "R1 / R2 / R6 must sit on non-strapping GPIOs.",
]
for i, t in enumerate(notes):
    if t:
        s.note(t, 55, 472 + i * 4.0, 1.7)

# Guarded so the find_*.py checkers (which `import sch` via _trace.py
# purely for its layout side effects, not this file write) don't leave a
# stray desk.kicad_sch behind in this directory every time they run.
if __name__ == "__main__":
    # Output lives one level up (schematics/) - this directory holds only
    # the generator and its dependencies; the .kicad_sch/.pdf/.svg are
    # the human-facing result. Optional path arg lets the Makefile
    # target it there explicitly; a bare `python3 sch.py` still writes
    # alongside the generator for a quick manual check.
    out_path = sys.argv[1] if len(sys.argv) > 1 else "desk.kicad_sch"
    open(out_path, "w").write(s.render())
    print(f"wrote {out_path}")
