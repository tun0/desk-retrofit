#!/usr/bin/env python3
"""desk_simple - the stripped version.

No transfer relay and no in-place fallback. The box sits in the 4-core
cable and permanently owns the winding; the handset is permanently fed
3V3 and its rockers are plain inputs.

Reverting is physical: motor - box - handset  becomes  motor - handset.
"""
from symbols import (Schematic, GNDS, RAILS, _rail, R_, RH, C_, F_, DH, DV,  # noqa: E402
                     TVS, NMOS, MOT, LIM, RLY, box, BUCK, MCU, MONO, AND2,
                     DRVX, ACS, CONN, PSUB)

s = Schematic("desk_simple", "Slangerup desk - simple in-line drive",
              "Box owns the winding; unplug it to revert", paper="A1")

_n = [0]


def _uref():
    _n[0] += 1
    return f"#PWR{_n[0]:03d}"


def gnd_tap(x, y):
    s.place(GNDS, _uref(), "GND", x, y + 1.0, hide_ref=True, hide_val=True)
    s.wire((x, y), (x, y + 1.0))


def tap(x, y, name):
    if name not in RAILS:
        RAILS[name] = _rail(name)
    s.place(RAILS[name], _uref(), name, x, y - 1.0, hide_ref=True)
    s.wire((x, y), (x, y - 1.0))


V5, VS, V3 = "+5V", "VSW", "+3V3"

# ============================================================== supply ====
s.note("SUPPLY", 55, 80, 2.8)
s.place(PSUB, "PS1", "29V 1.8A 52W  (via motor housing)", 80, 110)
s.place(F_, "F1", "2A slow-blow", 135, 105)
s.wire(s.pin("PS1", "1"), s.pin("F1", "1"))
s.wire(s.pin("PS1", "2"), (105, 118), (105, 145))
gnd_tap(105, 145)
s.place(TVS, "D1", "33V bidir", 165, 118)
s.wire(s.pin("F1", "2"), (165, 105), s.pin("D1", "1"))
s.junction((165, 105))
s.wire(s.pin("D1", "2"), (165, 140))
gnd_tap(165, 140)
s.place(C_, "C1", "220u 50V", 192, 118)
s.wire((165, 105), (192, 105), s.pin("C1", "1"))
s.junction((192, 105))
s.wire(s.pin("C1", "2"), (192, 140))
gnd_tap(192, 140)
s.wire((192, 105), (218, 105))
tap(218, 105, VS)

s.place(BUCK, "U1", "LM2596HV 29V-5V", 130, 190)
s.wire(s.pin("U1", "1"), (100, 190))
tap(100, 190, VS)
s.wire(s.pin("U1", "2"), (95, 193), (95, 222))
gnd_tap(95, 222)
s.place(C_, "C2", "220u 10V", 190, 198)
s.wire(s.pin("U1", "3"), (190, 190), s.pin("C2", "1"))
s.junction((190, 190))
s.wire(s.pin("C2", "2"), (190, 222))
gnd_tap(190, 222)
s.wire((190, 190), (218, 190))
tap(218, 190, V5)

# ========================================================== connectors ====
s.note("CABLE", 55, 262, 2.8)
s.place(CONN, "J2", "to motor housing", 90, 285)
for i, nm in enumerate(["VSW", "GND", "MOT_A", "MOT_B"]):
    p = s.pin("J2", str(i + 1))
    s.wire(p, (p[0] - 18, p[1]))
    if nm == "GND":
        gnd_tap(p[0] - 18, p[1])
    elif nm == "VSW":
        tap(p[0] - 18, p[1], VS)
    else:
        s.glabel(nm, p[0] - 18, p[1], 180)

s.place(CONN, "J3", "to handset", 90, 345)
for i, nm in enumerate(["+3V3", "GND", "HND_A", "HND_B"]):
    p = s.pin("J3", str(i + 1))
    s.wire(p, (p[0] - 18, p[1]))
    if nm == "GND":
        gnd_tap(p[0] - 18, p[1])
    elif nm == "+3V3":
        tap(p[0] - 18, p[1], V3)
    else:
        s.glabel(nm, p[0] - 18, p[1], 180)
s.note("handset sees 3V3 only - 29V never reaches it", 55, 372, 1.7)

# rocker inputs: dry contacts, no clamps needed
for i, (rs, rp, src, dst) in enumerate(
        [("R11", "R13", "HND_A", "SW_UP"),
         ("R14", "R15", "HND_B", "SW_DN")]):
    y = 400 + i * 45
    s.place(RH, rs, "4k7", 110, y)
    s.wire(s.pin(rs, "1"), (85, y))
    s.glabel(src, 85, y, 180)
    s.wire(s.pin(rs, "2"), (150, y))
    s.place(R_, rp, "100k", 150, y - 18)
    s.wire(s.pin(rp, "2"), (150, y))
    s.junction((150, y))
    s.wire(s.pin(rp, "1"), (150, y - 30))
    tap(150, y - 30, V3)
    s.wire((150, y), (195, y))
    s.glabel(dst, 195, y)

# ========================================================== controller ====
s.note("CONTROLLER", 285, 80, 2.8)
s.place(MCU, "U2", "ESP32 + display", 320, 150)
s.wire(s.pin("U2", "1"), (285, 132))
tap(285, 132, V5)
s.wire(s.pin("U2", "2"), (280, 135), (280, 190))
gnd_tap(280, 190)
s.wire(s.pin("U2", "3"), (275, 138))
tap(275, 138, V3)

OUT = {"4": "DIR_A", "5": "DIR_B", "6": "PWM", "7": None, "8": "KICK",
       "9": "ISENSE", "10": "SDA", "11": "SCL", "12": "SW_UP",
       "13": "SW_DN"}
pins = {k: s.pin("U2", k) for k in OUT}

for i, (num, ref) in enumerate([("4", "R1"), ("5", "R2"), ("6", "R6")]):
    p = pins[num]
    x = 385 + i * 18
    s.place(R_, ref, "10k", x, 232)
    s.wire((x, p[1]), (x, 228))
    s.junction((x, p[1]))
    s.wire(s.pin(ref, "2"), (x, 254))
    gnd_tap(x, 254)
s.note("hold drive lines safe before boot", 380, 268, 1.7)

for num in ("4", "5", "6", "8"):
    s.wire(pins[num], (450, pins[num][1]))
p7 = pins["7"]
s.wire(p7, (p7[0] + 8, p7[1]))
s.note("spare", p7[0] + 10, p7[1] + 1.4, 1.4)
for num in ("9", "10", "11", "12", "13"):
    p = pins[num]
    s.wire(p, (p[0] + 14, p[1]))
    s.glabel(OUT[num], p[0] + 14, p[1])

# ===================================================== watchdog + gating ==
s.note("WATCHDOG + GATING", 480, 80, 2.8)
s.place(MONO, "U3", "74HC123 250ms", 530, 130)
s.wire(s.pin("U3", "1"), (495, 112))
tap(495, 112, V5)
s.wire(s.pin("U3", "2"), (490, 115), (490, 175))
gnd_tap(490, 175)
pa3 = s.pin("U3", "3")
s.wire((450, pins["8"][1]), (450, pa3[1]), pa3)
p4, p5 = s.pin("U3", "4"), s.pin("U3", "5")
s.wire(p4, (476, p4[1]), (476, p5[1]), p5)
s.junction((476, p5[1]))
s.wire((476, p4[1]), (476, 106))
tap(476, 106, V5)
p6, p7b = s.pin("U3", "6"), s.pin("U3", "7")
s.wire(p6, (468, p6[1]), (468, p7b[1]), p7b)
s.junction((468, p7b[1]))
s.place(R_, "R3", "100k", 456, 110)
s.wire(s.pin("R3", "2"), (456, p7b[1]), (468, p7b[1]))
s.wire(s.pin("R3", "1"), (456, 100))
tap(456, 100, V5)
s.place(C_, "C3", "2u2", 442, 140)
s.wire(s.pin("C3", "1"), (442, p7b[1]), (456, p7b[1]))
s.junction((456, p7b[1]))
s.wire(s.pin("C3", "2"), (442, 172))
gnd_tap(442, 172)

WDX = 508.0
pq = s.pin("U3", "8")
s.wire(pq, (566, pq[1]), (566, 190), (WDX, 190), (WDX, 300))
s.label("WDOG", WDX + 2, 194)

for ref, src, y in (("U8", "4", 215), ("U9", "5", 255), ("U6", "6", 292)):
    s.place(AND2, ref, "74HC08", 540, y)
    pa, pb = s.pin(ref, "1"), s.pin(ref, "2")
    s.wire((450, pins[src][1]), (450, pa[1]), pa)
    s.wire((WDX, pb[1]), pb)
    s.junction((WDX, pb[1]))
s.note("three gates of one 74HC08", 508, 318, 1.7)

s.place(DRVX, "U7", "TC4427", 540, 350)
s.wire(s.pin("U7", "1"), (505, 342))
tap(505, 342, V5)
s.wire(s.pin("U7", "2"), (500, 345), (500, 378))
gnd_tap(500, 378)
pu6 = s.pin("U6", "3")
s.wire(pu6, (578, pu6[1]), (578, 332), (512, 332),
       (512, s.pin("U7", "3")[1]), s.pin("U7", "3"))

# =============================================================== drive ====
s.note("DRIVE", 625, 80, 2.8)
for ref, gate_ref, y in (("Q2", "U8", 215), ("Q3", "U9", 255)):
    s.place(NMOS, ref, "2N7002", 625, y + 14)
    pg = s.pin(ref, "1")
    pgy = s.pin(gate_ref, "3")
    s.wire(pgy, (pg[0] - 22, pgy[1]), (pg[0] - 22, pg[1]), pg)
    s.wire(s.pin(ref, "3"), (625, y + 48))
    gnd_tap(625, y + 48)

s.place(NMOS, "Q1", "IRLB8721", 625, 370)
pgd = s.pin("U7", "4")
s.wire(pgd, (s.pin("Q1", "1")[0] - 16, pgd[1]),
       (s.pin("Q1", "1")[0] - 16, s.pin("Q1", "1")[1]), s.pin("Q1", "1"))
s.wire(s.pin("Q1", "3"), (625, 402))
gnd_tap(625, 402)
MRETX = 752.0
s.wire(s.pin("Q1", "2"), (625, 344), (MRETX, 344))
s.place(DV, "D5", "SB560", 700, 322)
s.wire(s.pin("D5", "2"), (700, 344))
s.junction((700, 344))
s.wire(s.pin("D5", "1"), (700, 306))
tap(700, 306, VS)

for ref, val, y in (("K1", "UP  (raises desk)", 120),
                    ("K2", "DOWN  (lowers desk)", 185)):
    s.place(RLY, ref, val, 720, y)
    pcp = s.pin(ref, "1")
    s.wire(pcp, (672, pcp[1]))
    s.junction((672, pcp[1]))
s.wire((672, s.pin("K1", "1")[1]), (672, s.pin("K2", "1")[1]))
tap(672, s.pin("K1", "1")[1], V5)

for qref, kref, dref in (("Q2", "K1", "D2"), ("Q3", "K2", "D6")):
    pd = s.pin(qref, "2")
    pc = s.pin(kref, "2")
    s.wire(pd, (pd[0], pc[1]), pc)
    ymid = (s.pin(kref, "1")[1] + pc[1]) / 2
    s.place(DV, dref, "flyback", 688, ymid)
    s.wire(s.pin(dref, "1"), (688, s.pin(kref, "1")[1]))
    s.junction((688, s.pin(kref, "1")[1]))
    s.wire(s.pin(dref, "2"), (688, pc[1]))
    s.junction((688, pc[1]))

for ref in ("K1", "K2"):
    p = s.pin(ref, "5")
    s.wire(p, (MRETX, p[1]))
    s.junction((MRETX, p[1]))
s.wire((MRETX, s.pin("K1", "5")[1]), (MRETX, 344))
s.label("MRET", MRETX + 2, 338)

VSF = 782.0
for ref in ("K1", "K2"):
    p = s.pin(ref, "4")
    s.wire(p, (VSF, p[1]))
    s.junction((VSF, p[1]))
s.wire((VSF, s.pin("K1", "4")[1]), (VSF, s.pin("K2", "4")[1]))
tap(VSF, s.pin("K1", "4")[1], VS)

# current sense sits in the motor leg
s.place(ACS, "U5", "ACS724-5AB", 720, 265)
s.wire(s.pin("U5", "1"), (685, 247))
tap(685, 247, V5)
s.wire(s.pin("U5", "2"), (680, 250), (680, 292))
gnd_tap(680, 292)
pk1 = s.pin("K1", "3")
s.wire(pk1, (742, pk1[1]), (742, 232), (660, 232),
       (660, s.pin("U5", "3")[1]), s.pin("U5", "3"))
s.label("DRV_UP", 744, pk1[1] - 2)
pio = s.pin("U5", "4")
s.wire(pio, (pio[0] + 16, pio[1]))
s.glabel("MOT_B", pio[0] + 16, pio[1])
pk2 = s.pin("K2", "3")
s.wire(pk2, (pk2[0] + 16, pk2[1]))
s.glabel("MOT_A", pk2[0] + 16, pk2[1])

s.place(R_, "R4", "10k", 790, 265)
s.wire(s.pin("U5", "5"), (790, s.pin("U5", "5")[1]), (790, 261))
s.place(R_, "R5", "20k", 790, 292)
s.wire(s.pin("R4", "2"), s.pin("R5", "1"))
s.wire((790, 281), (812, 281))
s.junction((790, 281))
s.glabel("ISENSE", 812, 281)
s.wire(s.pin("R5", "2"), (790, 314))
gnd_tap(790, 314)

# ================================================================= leg ====
s.note("LEG (unmodified)", 285, 400, 2.8)
s.box(276, 412, 436, 470)
s.place(LIM, "SW3", "top limit", 326, 428)
s.place(DH, "D3", "allows down", 326, 455)
s.wire((308, 428), (308, 455))
s.wire((308, 428), s.pin("SW3", "1"))
s.wire((308, 455), s.pin("D3", "1"))
s.wire((346, 428), (346, 455))
s.wire(s.pin("SW3", "2"), (346, 428))
s.wire(s.pin("D3", "2"), (346, 455))
s.wire((308, 441), (291, 441))
s.junction((308, 441))
s.glabel("MOT_A", 291, 441, 180)
s.place(MOT, "M1", "2R5 winding", 371, 441)
s.wire((346, 441), s.pin("M1", "1"))
s.junction((346, 441))
s.place(LIM, "SW4", "bottom limit", 411, 428)
s.place(DH, "D4", "allows up", 411, 455)
s.wire((393, 428), (393, 455))
s.wire((393, 428), s.pin("SW4", "1"))
s.wire((393, 455), s.pin("D4", "2"))
s.wire((431, 428), (431, 455))
s.wire(s.pin("SW4", "2"), (431, 428))
s.wire(s.pin("D4", "1"), (431, 455))
s.wire(s.pin("M1", "2"), (393, 441))
s.junction((393, 441))
s.wire((431, 441), (450, 441))
s.junction((431, 441))
s.glabel("MOT_B", 450, 441)

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
        s.note(t, 55, 500 + i * 5.8, 1.7)

open("desk_simple.kicad_sch", "w").write(s.render())
print("wrote desk_simple.kicad_sch")
