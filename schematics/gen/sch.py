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
                     JP4)

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


def pigtail_break(pin, net_name, note, dx1, dy, dx2):
    # J2/J3 (the board-side Mini-Fits) aren't drawn (see symbols.py) - the
    # pigtail that used to mate with them is real, off-board wire, so
    # TB1-4 and J1/J4 need an actual net link across that gap, not just
    # the prose that used to be the only connection (see conversation).
    # A matching glabel is the standard KiCad way to say "this net
    # continues somewhere else on the page" - dx1 first (perpendicular
    # to whatever axis the pin's own existing wire already uses, so this
    # new branch can never be mistaken for a continuation of it), then
    # dy to clear the local clutter, then dx2 into the label itself so
    # every label in this file keeps the same horizontal-approach shape
    # (angle 0/180 - see RIGHT_SIDE/LEFT_SIDE above).
    #
    # Two pins of the same 2-pin part share one x column (only their y
    # differs, by the part's own pitch). Calling this on both with the
    # same dx1 puts both rises on that exact column - dy (8+) dwarfs a
    # 2.54 pitch, so the two rises don't just run parallel nearby, they
    # overlap on the SAME line: a dead short between two different
    # nets, not a visual nicety fixed by matching dy. dx1 must differ
    # between the two calls (0 and something else entirely) so the two
    # rises are never on the same column in the first place.
    x0, y0 = pin
    x1 = x0 + dx1
    y1 = y0 - dy
    x2 = x1 + dx2
    s.wire((x0, y0), (x1, y0), (x1, y1), (x2, y1))
    ang = 0 if dx2 >= 0 else 180
    s.glabel(net_name, x2, y1, angle=ang)
    if note:
        nx = x2 + 1 if dx2 >= 0 else x2 - 1 - 0.9 * len(note)
        s.note(note, nx, y1 - 2.5, 1.0)


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
s.place(MCU, "U1", "ESP32", 90, 150)
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
mcu_5v, mcu_gnd, mcu_3v3 = (s.pin("U1", MCU_5V), s.pin("U1", MCU_GND),
                            s.pin("U1", MCU_3V3))
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
               "SDA": 38, "SCL": 41, "DIR_A": 39, "DIR_B": 40, "PWM": 42}
# SDA/SCL moved from GPIO12/13 (physical pins 18/19) to GPIO38/41
# (physical pins 35/38) - see conversation. Not a firmware-arbitrary
# choice: pins 18/19 sit in a part of U2's real footprint where the PCB
# is already at copper capacity (confirmed by both Freerouting and
# careful manual attempts failing to route out from there at all), while
# 35/38 sit immediately next to DIR_A/DIR_B/PWM (pins 36/37/39) - GPIOs
# that already route successfully from that exact neighborhood. Neither
# is strapping/PSRAM-reserved/native-USB (same constraints as before).
PIN = {sig: GPIO_PIN[g] for sig, g in SIGNAL_GPIO.items()}

OUT = {PIN["DIR_A"]: "DIR_A", PIN["DIR_B"]: "DIR_B", PIN["PWM"]: "PWM",
       PIN["MODE"]: None, PIN["KICK"]: "KICK", PIN["ISENSE"]: "ISENSE",
       PIN["SDA"]: "SDA", PIN["SCL"]: "SCL", PIN["SW_UP"]: "SW_UP",
       PIN["SW_DN"]: "SW_DN"}
pins = {k: s.pin("U1", k) for k in OUT}

# Every direct breakout off U2's own body gets the SAME stub length and
# a glabel with its signal's name - that's the whole connection on this
# end. JPDRV below (and its destination-side counterpart near
# WATCHDOG+GATING), plus the rocker/current-sense circuitry in HANDSET
# INTERFACE, pick these up purely by matching label, the same mechanism
# WDOG already uses. Length
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
# ISENSE isn't in this list - see the current-sense divider below, which
# wires straight to U2's own pin instead of a uniform stub+label.
RIGHT_SIDE = (PIN["KICK"], PIN["SW_UP"], PIN["SW_DN"],
              PIN["SDA"])
# SCL (GPIO41/pin38) is drawn on the symbol's LEFT side (checked directly
# against MCU.pins_by_unit, same as the DIR_A/DIR_B/PWM warning above -
# SDA's new pin (35) is still RIGHT_SIDE, SCL's isn't, they don't have to
# match each other).
LEFT_SIDE = (PIN["DIR_A"], PIN["DIR_B"], PIN["PWM"], PIN["SCL"])
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

# Current-sense divider (R4/R5), moved here next to U2's own ISENSE pin
# and wired to it with a literal wire - like the original, single-board
# schematic had it, before any of the off-board/pigtail experiments.
# U5 (the ACS current sensor) stays behind in SUPPLY/DRIVE, next to the
# current it's actually measuring - only VIOUT, its raw analog output,
# needs to cross the sheet now, so that end gets the matching label
# instead (the same swap made for every other signal that crosses a
# long distance on this sheet).
isense_pin = pins[PIN["ISENSE"]]
RX = isense_pin[0] + 35
# Standing (compact vertical) footprint, not this design's usual R_
# default - PCB-side only (the schematic symbol doesn't care about
# mounting style). Checked directly: on the real board these two sit in
# the K1-to-K2 corridor, which is only wide enough for U5's DIP-8 socket
# once R4/R5 stop taking up ~12mm of vertical run each for their leads.
FOOTPRINT_VERT_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"
s.place(R_, "R1", "10k", RX, isense_pin[1] - 6.35, footprint=FOOTPRINT_VERT_R)
s.place(R_, "R2", "20k", RX, isense_pin[1] + 6.35, footprint=FOOTPRINT_VERT_R)
r4_top, r4_bot = s.pin("R1", "1"), s.pin("R1", "2")
r5_top, r5_bot = s.pin("R2", "1"), s.pin("R2", "2")
s.wire(r4_bot, r5_top)
# R4/R5 are centred on ISENSE's own row (isense_pin[1] == the midpoint
# of r4_bot/r5_top below), so the tap wire back to U2 is a single
# straight line, no jog needed.
tap_y = (r4_bot[1] + r5_top[1]) / 2
s.wire(isense_pin, (RX, tap_y))
s.junction((RX, tap_y))
s.wire(r4_top, (r4_top[0] + 12, r4_top[1]))
s.glabel("VIOUT", r4_top[0] + 12, r4_top[1])
gnd_y = r5_bot[1] + 5
s.wire(r5_bot, (RX, gnd_y))
gnd_tap(RX, gnd_y)


# U2 PIGTAILS block removed (long-shot experiment: U2 is back on this
# board directly - see its own placement above). JP1/JP2/JP3 used to be
# U2's off-board stand-in; now U2 IS the board-side part, so they'd just
# be duplicate symbols carrying labels U2 already carries on its own
# pins. JP4 and JP6 (the sense/power pigtails that used to mate with
# those, back when U2 was a separate off-board DevKitC) are dropped for
# the same reason: U2 is on this board directly now, so there's no cable
# run between it and the rest of this sheet any more - SW_UP/SW_DN/
# ISENSE and +5V/+3V3/GND already reach wherever they're needed as
# matching global labels off U2's own pins above, the same mechanism
# WDOG/KICK use.

# HANDSET INTERFACE: rocker dividers + J3 (to handset). Placed above
# the "HANDSET (unmodified)" reference block below it, not just any
# free gap - this is the section that actually feeds that connector,
# so the two read as one visual unit.
s.note("HANDSET INTERFACE", 520, 300, 2.8)
# SW_UP/SW_DN/ISENSE arrive here as matching global labels off U2's own
# pins (see CONTROLLER above) - no physical pigtail connector in between
# any more now that U2 is on this board directly (JP4, the "sense
# pigtail" that used to sit here, is gone - see the note above). The
# column/rows below match where JP4's own pins used to land, purely so
# R11/R13/R14/R15/TB3/TB4 below don't have to move.
NODEX = {PIN["SW_UP"]: 540.0, PIN["SW_DN"]: 550.0}
SENSE_X0 = 524.51
SENSE_Y = {PIN["SW_UP"]: 339.09, PIN["SW_DN"]: 341.63}
jpsns2_pins = {}
for num in (PIN["SW_UP"], PIN["SW_DN"]):
    y = SENSE_Y[num]
    p = (SENSE_X0, y)
    # Wire from here to NODEX is drawn below, in the R11/R14 loop - not
    # here too, which would just double-draw the same segment.
    s.glabel(OUT[num], SENSE_X0, y, angle=180)
    jpsns2_pins[num] = p
# ISENSE has no business in this section at all - it was only ever here
# because it shared JP4's physical connector with SW_UP/SW_DN, not
# because it's logically part of the handset interface. It connects
# straight to U2 now (see CONTROLLER), so there's nothing to draw here.
# J3 (the board-side Mini-Fit to the handset) is dropped from this sheet
# - see symbols.py. Two 2-position screw terminals (handset signal pair,
# handset power pair) take its place, at the exact spot its two pin
# columns used to occupy, so the rest of this section doesn't need to
# change. TB3 pins point left toward the resistor dividers next to U2 -
# HND_A/HND_B go there. TB4 pins point right, so +3V3/GND tap off to its
# right instead (no README circuit-number constraint here like TB1/TB2
# have, so sides are assigned for routing, not to match an external
# reference). Same row as SW_UP/R11 (pin 1 shares the 2.54mm pitch too),
# so no vertical nudge is needed to land it exactly.
s.place(TERM2, "TB1", "signal pair", 584.14, jpsns2_pins[PIN["SW_UP"]][1])
# mirror="y": TB4's wire goes right (to +3V3/GND), not left - unmirrored,
# its pins (and so its body) would sit on the wrong side, putting that
# wire through TB4 itself instead of clear of it. Moved right of where
# J3's own pin 3/4 column used to be, same reasoning as TB2.
s.place(TERM2, "TB2", "power pair", 599.59, jpsns2_pins[PIN["SW_UP"]][1],
        mirror="y")
for num, rs, tref, jn in ((PIN["SW_UP"], "R3", "TB1", "1"),
                          (PIN["SW_DN"], "R4", "TB1", "2")):
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
for num, rp in ((PIN["SW_UP"], "R5"), (PIN["SW_DN"], "R6")):
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

# W2: the handset pigtail - same reasoning as W1's own J2 (see SUPPLY):
# a real Mini-Fit Jr plug (J3), crimped onto the pigtail, is a distinct
# part from J4's fixed receptacle in the handset, and belongs on the
# page. TB3 (signal pair) feeds pins 1/2 from the left, matching their
# own exit side; TB4 (power pair) feeds pins 3/4 from the right, same
# as TB2/J2.
J3X, J3Y = 590.0, 305.0
s.place(CONN, "J1", "on pigtail\nplug crimped here, mates with J4",
        J3X, J3Y, val_at=(J3X, J3Y - 8.5), on_board=False)
j3p_a, j3p_b = s.pin("J1", "1"), s.pin("J1", "2")
j3p_3v3, j3p_gnd = s.pin("J1", "3"), s.pin("J1", "4")

hnd_a, hnd_b = s.pin("TB1", "1"), s.pin("TB1", "2")
# Jog to J3's own column first, THEN rise - arriving vertically, not
# horizontally, so the outgoing label below (also leaving left) can't
# retrace this same span (it did, the first time this was written).
# J3's pins 1/2 (and 3/4) share one x column, 2.54mm apart - see J2's
# own note above (SUPPLY) for why each pin gets its own distinct jog
# column instead of one going straight in.
s.wire(hnd_a, (j3p_a[0] + 2.54, hnd_a[1]), (j3p_a[0] + 2.54, j3p_a[1]), j3p_a)
s.wire(hnd_b, (j3p_b[0] + 1.27, hnd_b[1]), (j3p_b[0] + 1.27, j3p_b[1]), j3p_b)

j3_3v3, j3_gnd = s.pin("TB2", "1"), s.pin("TB2", "2")
s.wire(j3_3v3, (j3_3v3[0] + 6, j3_3v3[1]))
tap(j3_3v3[0] + 6, j3_3v3[1], V3)
s.wire(j3_gnd, (j3_gnd[0] + 6, j3_gnd[1]))
gnd_tap(j3_gnd[0] + 6, j3_gnd[1])
s.wire(j3_3v3, (j3p_3v3[0] - 2.54, j3_3v3[1]), (j3p_3v3[0] - 2.54, j3p_3v3[1]), j3p_3v3)  # see hnd_a
s.wire(j3_gnd, (j3p_gnd[0] - 1.27, j3_gnd[1]), (j3p_gnd[0] - 1.27, j3p_gnd[1]), j3p_gnd)

s.wire(j3p_a, (j3p_a[0] - 6, j3p_a[1]))
s.glabel("HND_A", j3p_a[0] - 6, j3p_a[1], angle=180)
s.wire(j3p_b, (j3p_b[0] - 6, j3p_b[1]))
s.glabel("HND_B", j3p_b[0] - 6, j3p_b[1], angle=180)
s.wire(j3p_3v3, (j3p_3v3[0] + 6, j3p_3v3[1]))
s.glabel("+3V3", j3p_3v3[0] + 6, j3p_3v3[1])
# Left, not right - gnd's own incoming wire above jogs in from the
# right (its escape column), so a rightward label here would retrace
# part of that same span rather than continuing past it.
# Right, not left - gnd's own jog above arrives moving rightward (same
# direction as 3v3's), so a leftward label here would retrace it.
s.wire(j3p_gnd, (j3p_gnd[0] + 6, j3p_gnd[1]))
s.glabel("GND", j3p_gnd[0] + 6, j3p_gnd[1])
s.note("W2: pigtail, 4-cond, bare wire into TB3/TB4", j3p_a[0] - 6, J3Y - 14, 1.0)
# Centered under TB3/TB4 (note() anchors text at its left edge, so
# offset by half the estimated string width), a bit below their own
# row - clear of TB3/TB4's bodies but still inside the HANDSET
# INTERFACE section above the "HANDSET (unmodified)" box below it.
NOTE_TEXT = "handset sees 3V3 only - 29V never reaches it"
j3_cx = (s.pin("TB1", "1")[0] + s.pin("TB2", "1")[0]) / 2
note_y = jpsns2_pins[PIN["SW_UP"]][1] + 20
s.note(NOTE_TEXT, j3_cx - len(NOTE_TEXT) * 1.7 * 0.6 / 2, note_y, 1.7)

# ============================================ tof sensor prep (phase 2) ==
# Not a real connection yet - Phase 2 (README 8) isn't started. This just
# breaks SDA/SCL out to a screw terminal now, while the board is being
# built anyway, so adding the VL53L1X later doesn't need a re-spin.
# +3V3/GND for it are NOT a separate terminal (was TB6, dropped - see
# conversation): TB4 right above already carries +3V3/GND to the
# handset, and the plan is to land a second wire under each of TB4's own
# two screws for the ToF sensor instead of adding another connector.
# Only reason this needed its own terminal at all rather than also
# sharing TB3: SDA/SCL are a distinct signal pair with nowhere existing
# to splice into. Same TERM2 part as TB1-4 (already bought in bulk for
# those), same x column as TB3/TB4 above for visual consistency
# (unmirrored, like TB3 - no J-connector forcing a side here).
TOF_Y = note_y + 20
s.place(TERM2, "TB3", "ToF signal pair", 584.14, TOF_Y)
# SDA/SCL connect purely by matching label name to U2's own stub above
# (see CONTROLLER) - same mechanism as every other U2 breakout on this
# sheet, no physical wire needs to reach that far.
tof_sda, tof_scl = s.pin("TB3", "1"), s.pin("TB3", "2")
s.wire(tof_sda, (tof_sda[0] + 6, tof_sda[1]))
s.glabel("SDA", tof_sda[0] + 6, tof_sda[1])
s.wire(tof_scl, (tof_scl[0] + 6, tof_scl[1]))
s.glabel("SCL", tof_scl[0] + 6, tof_scl[1])

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
s.place(MONO, "U2", "74HC123 250ms", U3X, u3_y, unit=1)
# Unit 3 (shared VCC/GND) sits beside unit 1 now, same row, instead of
# above it - default ref/value placement (beside, not above) already
# suits a power-only unit with no body room above.
s.place(MONO, "U2", "74HC123 250ms", U3X + 21.59, u3_y, unit=3)

pa = s.pin("U2", "1", unit=1)
# KICK arrives here via JPDRV2, the destination half of JPDRV's pigtail
# (see the MCU-side placement above) - wired together with DIR_A/DIR_B/
# PWM below, once their own gate-input points exist too.

# B and Clr share ONE +5V flag now (this design never retriggers or
# clears, so both just need to sit high) - a single vertical bus feeds
# both pins off the same flag instead of each getting its own local tap.
pb = s.pin("U2", "2", unit=1)
pclr = s.pin("U2", "3", unit=1)
BX = 280.67
b_bend = (BX, pb[1])
s.wire(pb, b_bend)
s.wire(b_bend, (BX, 108.95))
tap(BX, 108.95, V5)
s.wire(b_bend, (BX, pclr[1]))
s.wire((BX, pclr[1]), pclr)
s.junction(b_bend)

pvcc = s.pin("U2", "16", unit=3)
s.wire(pvcc, (pvcc[0], 108.95))
tap(pvcc[0], 108.95, V5)
pgnd = s.pin("U2", "8", unit=3)
s.wire(pgnd, (pgnd[0], 147.32))
gnd_tap(pgnd[0], 147.32)

# Cext/RCext tied together (per the 74HC123 R/C timing configuration),
# feeding in from a shared row to their left instead of reaching back
# across the body. R3 hangs down from its own +5V flag onto that row;
# C3 (now horizontal - rotated 90, was vertical) sits directly on it.
p14, p15 = s.pin("U2", "14", unit=1), s.pin("U2", "15", unit=1)
ROW_Y = (p14[1] + p15[1]) / 2
s.wire((p14[0], ROW_Y), p14)
s.wire((p14[0], ROW_Y), p15)
s.junction((p14[0], ROW_Y))

R3X = 265.43
s.place(R_, "R7", "100k", R3X, ROW_Y - 3.81)
r3_hi, r3_lo = s.pin("R7", "1"), s.pin("R7", "2")
s.wire(r3_hi, (r3_hi[0], 108.95))
tap(r3_hi[0], 108.95, V5)
s.wire(r3_lo, (p14[0], ROW_Y))

C3X = 257.81
s.place(C_, "C1", "2u2", C3X, ROW_Y, angle=90)
c3_l, c3_r = s.pin("C1", "1"), s.pin("C1", "2")
s.wire(c3_r, r3_lo)

GNDX = 248.92
s.wire(c3_l, (GNDX, ROW_Y))
gnd_tap(GNDX, ROW_Y)

# Real part: all three gates are units of ONE 74LS08 package (ref "U3"),
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
GATES = ((1, PIN["DIR_A"], "R8", 215), (2, PIN["DIR_B"], "R9", 255),
         (3, PIN["PWM"], "R10", 292))
# Q sits on the right, same side as the AND gates - it clears the body's
# height first before jogging to the shared WDOG column, same reasoning
# as before (jogging left immediately at pin height would cut through
# the body). WDX shares BX's column (B/Clr's own +5V bus, above) purely
# for visual tidiness - the two buses don't overlap in Y.
WDX = BX
pq = s.pin("U2", "13", unit=1)
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
    s.place(AND2, "U3", "74HC08", U6X, y, unit=unit)
    p_a, p_b = s.pin("U3", top, unit=unit), s.pin("U3", bottom, unit=unit)
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

# U2 is back on this board (see its own placement note) - DIR_A/DIR_B/
# PWM/KICK reach U3/U6 by matching label straight off U2's own stubs
# now, the same mechanism WDOG already uses, instead of routing to a
# JP5 pigtail connector that no longer represents a real board edge.
targets = [pa, gate_targets[PIN["DIR_A"]], gate_targets[PIN["DIR_B"]],
           gate_targets[PIN["PWM"]]]
labels = ["KICK", "DIR_A", "DIR_B", "PWM"]
for target, label in zip(targets, labels):
    x = target[0] - 8
    s.wire(target, (x, target[1]))
    s.glabel(label, x, target[1], angle=180)

s.note("hold drive lines safe before boot", 250, 300, 1.5)


# unit 5 (shared VCC/GND) - placed below U6C (the last gate) instead of
# above everything, its own local taps same as U3's power unit. Ref/
# value beside it, not above, same reasoning as U3's power unit. Below
# was previously above (y=200), which put its GND stub right through
# U6A's own body (the first gate, at y=215) - moving past the last gate
# instead gives both stubs open space to land in, so they're shorter too.
U6P_Y = 332
s.place(AND2, "U3", "74HC08", U6X, U6P_Y, unit=5,
        ref_at=(U6X + 6.35, U6P_Y - 1.27),
        val_at=(U6X + 6.35, U6P_Y + 1.27), justify="left")
u6_vcc, u6_gnd = s.pin("U3", "14", unit=5), s.pin("U3", "7", unit=5)
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
pu6 = s.pin("U3", GATE_PINS[3][2], unit=3)
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
s.place(BJT_NPN, "Q1", "BC337", BJT_X, q4_y)
s.place(BJT_PNP, "Q2", "BC327", BJT_X, q5_y, mirror="x")

q4_c, q4_b, q4_e = s.pin("Q1", "1"), s.pin("Q1", "2"), s.pin("Q1", "3")
q5_c, q5_b, q5_e = s.pin("Q2", "1"), s.pin("Q2", "2"), s.pin("Q2", "3")

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
s.place(R_, "R11", "1k", r7_x, pu6[1], angle=90)
s.wire(pu6, s.pin("R11", "1"))
s.wire(s.pin("R11", "2"), q4_b)

# =============================================================== drive ====
s.note("DRIVE", 395, 80, 2.8)
# Q2/Q3 are placed level with their own gate (U6 units 1/2) - gate pin
# and NMOS gate pin are both offset 0 from centre, so this turns each
# gate-to-transistor connection into one straight line.
for ref, gate_unit in (("Q3", 1), ("Q4", 2)):
    pgy = s.pin("U3", GATE_PINS[gate_unit][2], unit=gate_unit)
    s.place(NMOS, ref, "2N7000", DRAIN_X - NMOS_DX, pgy[1])
    s.wire(pgy, s.pin(ref, "1"))
    ps = s.pin(ref, "3")
    s.wire(ps, (DRAIN_X, ps[1] + 15))
    gnd_tap(DRAIN_X, ps[1] + 15)

s.place(NMOS, "Q5", "IRLZ44N", Q1_X, Q1_Y,
        footprint="Package_TO_SOT_THT:TO-220-3_Vertical")
q1_drain, q1_source = s.pin("Q5", "2"), s.pin("Q5", "3")
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
s.place(DH, "D1", "SB560", DRAIN_X, q1_drain[1] - D5_GAP - 3.81, angle=270,
        footprint="Diode_THT:D_DO-201AD_P12.70mm_Horizontal")
d5_bottom = s.pin("D1", "2")
s.wire(q1_drain, (DRAIN_X, d5_bottom[1]), (MRETX, d5_bottom[1]))
s.junction(d5_bottom)
d5_top = s.pin("D1", "1")
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
        ("K1", "energized = UP (raises desk)", "Q3", "D2"),
        ("K2", "energized = DOWN (lowers desk)", "Q4", "D3"))):
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
# above. FILTER (pin 6) gets its own cap to GND below (C5) - see there.
# Underneath J2 (same x) leaves ample room on every side, clear of
# MRETX (now on the far side of K1/K2, to their left) and clear of the
# relay bodies too.
U5X = 560.0
# Y chosen so IP- lands exactly on K1's own COM row (now pointing right
# after the rotation above) - straight wire instead of a jog.
U5Y = s.pin("K1", "11")[1] - 5.08
s.place(ACS, "U4", "ACS712ELCTR-05B", U5X, U5Y)
p_vcc, p_gnd = s.pin("U4", "8"), s.pin("U4", "5")
s.wire(p_vcc, (p_vcc[0], p_vcc[1] - 6))
tap(p_vcc[0], p_vcc[1] - 6, V5)
s.wire(p_gnd, (p_gnd[0], p_gnd[1] + 6))
gnd_tap(p_gnd[0], p_gnd[1] + 6)

# C4/C5: the Pololu carrier this design used to sit on populated both
# of these (a 0.1uF VCC bypass, a 1nF FILTER-to-GND cap - confirmed
# against Allegro's own ACS712/ACS724 application circuit, conversation)
# - with the bare chip on a generic adapter neither exists anymore, so
# both move onto this board. Same "shunt to ground" pattern D1 uses on
# the +29V rail: splice into the pin's own wire, drop the other leg to
# a GND row of its own.
C4X = p_vcc[0] + 30  # clear of both the VIOUT and FILTER stubs below
# +3.81 (not -3.81): pin1 sits 3.81 *above* the symbol's own placement
# point (local +y flips to absolute -y - see ACS pin-layout comment
# above), so placing 3.81 *below* the target y lands pin1 exactly on
# it. Getting this backwards once put C4's pin2 (GND) on top of the
# VCC branch point instead - a dead short between the two rails.
s.place(C_, "C2", "100n", C4X, p_vcc[1] + 3.81)
s.wire(p_vcc, (C4X, p_vcc[1]))
s.junction(p_vcc)
c4_bot = s.pin("C2", "2")
s.wire(c4_bot, (c4_bot[0], c4_bot[1] + 8))
gnd_tap(c4_bot[0], c4_bot[1] + 8)

p_filter = s.pin("U4", "6")
C5X = p_filter[0] + 10
s.place(C_, "C3", "1n", C5X, p_filter[1] + 3.81)
s.wire(p_filter, (C5X, p_filter[1]))
c5_bot = s.pin("C3", "2")
s.wire(c5_bot, (c5_bot[0], c5_bot[1] + 8))
gnd_tap(c5_bot[0], c5_bot[1] + 8)

pk1 = (COMX["K1"], s.pin("K1", "11")[1])
ip_minus = s.pin("U4", "3")
# pk1 and ip_minus already share a y (U5Y is chosen for exactly this),
# so a straight 2-point wire - a 3-point version with a now-coincident
# middle waypoint produced an invisible zero-length first segment.
s.wire(pk1, ip_minus)
s.label("DRV_UP", COMX["K1"], pk1[1])
ip_plus = s.pin("U4", "1")
pk2 = (COMX["K2"], s.pin("K2", "11")[1])

# J2 (the board-side Mini-Fit to the motor housing) is dropped from this
# sheet - see symbols.py. In its place, two 2-position screw terminals
# (motor pair, supply pair) are placed so their pins land exactly where
# J2's own two pin columns used to be, so nothing downstream needs to
# change: same reasoning J2 always had for sitting here (above and to
# the right of U5, ample room, MOT_A/MOT_B each get their own column on
# the way up).
s.place(TERM2, "TB4", "motor pair", 559.74, 119.05)
# mirror="y": TB2's wire goes right (into the SUPPLY chain), not left -
# unmirrored, its pins (and so its body) would sit on the wrong side,
# putting that wire through TB2 itself instead of clear of it. Moved
# right of where J2's own pin 3/4 column used to be (12.7mm from TB1,
# same as a single 2x2 connector's own column spacing) for clearance -
# no longer one physical part, no reason to sit that close.
s.place(TERM2, "TB5", "supply pair", 574.59, 119.05, mirror="y")
# MOT_A/MOT_B order on pin 1/2 is still provisional - MOT_A is defined by
# function (README 1.6: whichever conductor raises the desk), so if
# bring-up shows this backwards, the fix is relabelling here, not
# rewiring anything.
j2_mota, j2_motb = s.pin("TB4", "1"), s.pin("TB4", "2")
j2_vsw, j2_gnd = s.pin("TB5", "1"), s.pin("TB5", "2")
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

# W1: the motor pigtail - 4-conductor, bare wire at this end (into
# TB1/TB2), a real Mini-Fit Jr plug (J2) at the other, crimped on
# rather than soldered to the board (see conversation - J2/J3 were
# dropped from the sheet entirely at first, on the reasoning that the
# net-link to J1/J4 was the only thing missing; it isn't - the plug
# itself is a real part, distinct from J1's own fixed receptacle in
# the motor housing, and belongs on the page like J1/J4 already are).
J2X, J2Y = 566.0, 90.0
s.place(CONN, "J2", "on pigtail\nplug crimped here, mates with J1",
        J2X, J2Y, val_at=(J2X, J2Y - 8.5), on_board=False)
j2p_mota, j2p_motb = s.pin("J2", "1"), s.pin("J2", "2")
j2p_vsw, j2p_gnd = s.pin("J2", "3"), s.pin("J2", "4")

# J2's pins 1/2 (and 3/4) share one x column, 2.54mm apart - rising
# either one of a pair straight into its own pin means that rise's
# column passes right through the OTHER pin's position too (not just
# near it: J2's own pin spacing is tiny next to the rise's height, so
# the sibling pin always ends up sitting partway along the same
# line). Both pins in a pair get their own jog column instead, clear
# of the shared pin column and of each other, so neither rise runs
# right over the sibling pin's own point - each still leaves a single
# T-touch where the far pin's own label stub crosses the near pin's
# rise (unavoidable at this pitch with a simple two-bend path; no
# junction drawn there, so no short - same kind of crossing already
# accepted elsewhere on this sheet, see find_crossings.py's baseline).
s.wire(j2_mota, (j2p_mota[0] + 2.54, j2_mota[1]), (j2p_mota[0] + 2.54, j2p_mota[1]), j2p_mota)
s.wire(j2_motb, (j2p_motb[0] + 1.27, j2_motb[1]), (j2p_motb[0] + 1.27, j2p_motb[1]), j2p_motb)

s.wire(j2_vsw, (j2p_vsw[0] - 2.54, j2_vsw[1]), (j2p_vsw[0] - 2.54, j2p_vsw[1]), j2p_vsw)
s.wire(j2_gnd, (j2p_gnd[0] - 1.27, j2_gnd[1]), (j2p_gnd[0] - 1.27, j2p_gnd[1]), j2p_gnd)

# J2's own pins carry the pigtail onward to J1 (see LEG) with the same
# matching-glabel mechanism as before - now attached to the plug
# itself, not to the board's screw terminals.
s.wire(j2p_mota, (j2p_mota[0] - 6, j2p_mota[1]))
s.glabel("MOT_A", j2p_mota[0] - 6, j2p_mota[1], angle=180)
s.wire(j2p_motb, (j2p_motb[0] - 6, j2p_motb[1]))
s.glabel("MOT_B", j2p_motb[0] - 6, j2p_motb[1], angle=180)
s.wire(j2p_vsw, (j2p_vsw[0] + 6, j2p_vsw[1]))
s.glabel("+29V_RAW", j2p_vsw[0] + 6, j2p_vsw[1])
s.wire(j2p_gnd, (j2p_gnd[0] + 6, j2p_gnd[1]))  # see j3p_gnd, HANDSET
s.glabel("GND", j2p_gnd[0] + 6, j2p_gnd[1])
s.note("W1: pigtail, 4-cond, bare wire into TB1/TB2", j2p_mota[0] - 6, J2Y - 14, 1.0)

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

# JP6 (power pigtail, the mate for U2's now-removed off-board power
# feed) removed - see the note above CONTROLLER. It only ever re-tapped
# +5V/+3V3/GND onto already-global rails with no other job, so nothing
# takes its place: those rails are already reachable everywhere via
# plain tap()/gnd_tap() calls, same as before.

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
# angle=270: TVS's real symbol has horizontal pins natively (see
# symbols.py) - rotated here so pin 1 lands on the SY rail and pin 2
# drops straight to GND_Y, same shunt-to-ground topology as before.
s.place(TVS, "D4", "33V bidir", D1X, SY + 3.81, angle=270)
s.wire(j2_vsw, s.pin("D4", "1"))

C1X = D1X + GAP
s.place(C_, "C4", "220u 50V", C1X, SY + 3.81,
        footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm")

U1X = C1X + GAP + 12.7  # VIN sits 12.7mm left of centre
s.place(BUCK, "U5", "LM2576HVS-5.0 29V-5V", U1X, SY + 2.54)
fb_x = U1X + 12.7  # FB sits 12.7mm right of centre, same y as VIN

C2X = fb_x + GAP
s.place(C_, "C5", "220u 10V", C2X, SY + 3.81,
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

d1_lo = s.pin("D4", "2")
s.wire(d1_lo, (d1_lo[0], GND_Y))
gnd_tap(d1_lo[0], GND_Y)

s.wire(s.pin("D4", "1"), s.pin("C4", "1"))
c1_hi = s.pin("C4", "1")

c1_lo = s.pin("C4", "2")
s.wire(c1_lo, (c1_lo[0], GND_Y))
gnd_tap(c1_lo[0], GND_Y)

s.wire(c1_hi, s.pin("U5", "1"))

u1_out = s.pin("U5", "2")
u1_gnd = s.pin("U5", "3")
u1_fb = s.pin("U5", "4")
u1_onoff = s.pin("U5", "5")

s.wire(u1_gnd, (u1_gnd[0], GND_Y))
gnd_tap(u1_gnd[0], GND_Y)

# ~ON/OFF floating is not a valid state - tied low for always-on.
s.wire(u1_onoff, (u1_onoff[0], GND_Y))
gnd_tap(u1_onoff[0], GND_Y)

# FB must sense VOUT externally even on this fixed-5V part - FB and
# C2's own top pin land on the same y (both = SY) already, so that's
# one straight line; OUT (below both) taps up into it with its own
# short stub instead of overlapping that line with a second wire.
c2_hi = s.pin("C5", "1")
s.wire(u1_fb, c2_hi)
s.wire(u1_out, (u1_out[0], u1_fb[1]))
s.junction((u1_out[0], u1_fb[1]))
s.junction(c2_hi)
tap(c2_hi[0], c2_hi[1], V5)

c2_lo = s.pin("C5", "2")
s.wire(c2_lo, (c2_lo[0], GND_Y))
gnd_tap(c2_lo[0], GND_Y)

# R4/R5 (the current-sense divider) moved next to U2's own ISENSE pin
# in CONTROLLER, wired there with a literal wire instead of a matching
# label - see that section. VIOUT (this pin) just needs a dead-end stub
# of its own now, matching label, same mechanism WDOG uses.
p_out = s.pin("U4", "7")
s.wire(p_out, (p_out[0] + 12, p_out[1]))
s.glabel("VIOUT", p_out[0] + 12, p_out[1])


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

# J1 - the far end of the motor pigtail (J2, see SUPPLY, is the near
# end - same Molex Mini-Fit Jr, same Conn_02x02_Top_Bottom part, see
# symbols.py), sitting where it actually is: inside the leg, wired
# straight to this section's own motor leads and to the PSU below,
# instead of a same-named-label match that was never actually connected
# to anything ("global" only means "matches by text anywhere on THIS
# sheet" - see NETLIST.md, this is what fixed J1-to-M1). J1-to-J2 is a
# real, separate piece of off-board cable, not something a wire could
# legitimately be drawn across, so that hop is a label-match instead
# (see SUPPLY/DRIVE, J2's own pins).
J1X, J1Y = 420.0, 476.0
# val_at pushed further down than the library's own default (5.08) - two
# lines now, and the default clearance was tuned for one, sitting right
# against the body.
s.place(CONN, "J3", "in motor housing\nmates with board pigtail (TB1/TB2)",
        J1X, J1Y, val_at=(J1X, J1Y + 6.5), on_board=False)
j1_mota, j1_motb = s.pin("J3", "1"), s.pin("J3", "2")
j1_vsw, j1_gnd = s.pin("J3", "3"), s.pin("J3", "4")
# Pins 1/2's own wire down to SW3/SW4 arrives vertically (last segment),
# so this branch escapes sideways (dx1) before rising - going straight
# up would run back along that same column. Pins 3/4's wire from PSU1
# arrives horizontally, so no escape needed there.
# Escaping right (toward vsw/gnd) put both stubs inside J1's own body
# outline (its rectangle starts right at the pin edge) - left is clear
# all the way past SW3/D3 (their own wire leaves at a different y, not
# this one), so both escape that way instead.
pigtail_break(j1_mota, "MOT_A", "W1 (cont'd): from J2, elsewhere on this sheet",
              -6, 12, -6)
pigtail_break(j1_motb, "MOT_B", None, -10, 12, -6)

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

s.place(LIM, "SW1", "top limit", SWX, m1_plus[1] - EXTRA, on_board=False)
s.place(DH, "D5", "allows down", SWX, m1_plus[1] - EXTRA - GAP, mirror="y",
        on_board=False)
sw3_l, sw3_r = s.pin("SW1", "1"), s.pin("SW1", "2")
d3_k, d3_a = s.pin("D5", "1"), s.pin("D5", "2")
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

s.place(LIM, "SW2", "bottom limit", SWX, m1_minus[1] + EXTRA, on_board=False)
s.place(DH, "D6", "allows up", SWX, m1_minus[1] + EXTRA + GAP, mirror="y",
        on_board=False)
sw4_l, sw4_r = s.pin("SW2", "1"), s.pin("SW2", "2")
d4_k, d4_a = s.pin("D6", "1"), s.pin("D6", "2")
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
pigtail_break(j1_vsw, "+29V_RAW", None, 0, 16, 6)
pigtail_break(j1_gnd, "GND", None, 0, -16, 6)  # see j2_gnd, SUPPLY

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

s.place(ROCKER, "SW3", "DOWN rocker", DOWN_X, SWY, on_board=False)
s.place(ROCKER, "SW4", "UP rocker", UP_X, SWY, mirror="y", on_board=False)
down_a, down_com, down_c = s.pin("SW3", "1"), s.pin("SW3", "2"), s.pin("SW3", "3")
up_a, up_com, up_c = s.pin("SW4", "1"), s.pin("SW4", "2"), s.pin("SW4", "3")
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

# W2 (cont'd) - see TB3/TB4's own side. j4_1's own wire in is horizontal
# (up_com, straight in) so no escape needed; j4_2/j4_3/j4_4 all arrive
# vertically (BOTY_COM/TOPY/BOTY_C dropping straight down into the pin),
# so each needs the sideways escape first, same reasoning as J1 above.
# mid_a/mid_c -> +3V3/GND pairing is provisional, like MOT_A/MOT_B's own
# order (see SUPPLY) - README doesn't pin down which OEM throw (NC vs
# NO) is which conductor; swap the two glabels below if bring-up shows
# the dry-contact reading inverted, nothing else needs to change.
pigtail_break(j4_1, "HND_A", None, 0, 8, 6)
# Note placed separately, further left - the auto position (right next
# to the label) lands under J4.3/J4.4's own labels in this corner, close
# enough to visually overlap them (no wire crossing, just crowded text).
s.note("W2 (cont'd): from J3, elsewhere on this sheet", j4_1[0] - 45, j4_1[1] - 20.5, 1.0)
pigtail_break(j4_2, "HND_B", None, 2, -8, 6)  # up (like every other
                                               # pigtail break here) runs
                                               # into up_com's own wire AND
                                               # J4's own pin-tip bbox in
                                               # this one narrow corner -
                                               # down clears both instead,
                                               # same "rise the other way"
                                               # fix as the GND pins above
pigtail_break(j4_3, "+3V3", None, 4, 13, 6)
pigtail_break(j4_4, "GND", None, 9, 13, 6)

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
