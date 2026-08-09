#!/usr/bin/env python3
"""desk_inline, wired rather than labelled.

Real horizontal power rails with taps, and the control chain
(MCU -> gating -> coil drivers -> relays -> contacts) drawn as wires.
Global labels are kept only for genuine long hauls across the sheet.
"""
from schlib import Schematic, Sym, poly, circ, rect, stext, NOFILL, BGFILL

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

s = Schematic("desk_inline", "Slangerup desk - in-line interceptor",
              "Handset unmodified; board sits in the 4-core cable",
              paper="A1")

V5Y, VSY, V3Y, GNY = "+5V", "VSW", "+3V3", "GND"
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

# ============================================================== supply ====
s.note("SUPPLY", 48, 74, 2.6)
s.place(PSUB, "PS1", "29V 1.8A 52W", 70, 100)
s.place(F_, "F1", "2A slow-blow", 120, 95)
s.wire(s.pin("PS1", "1"), s.pin("F1", "1"))
s.wire(s.pin("PS1", "2"), (95, 108), (95, 140))
gnd_tap(95, 140)
s.place(TVS, "D1", "33V bidir", 145, 108)
s.wire(s.pin("F1", "2"), (145, 95), s.pin("D1", "1"))
s.junction((145, 95))
s.wire(s.pin("D1", "2"), (145, 130))
gnd_tap(145, 130)
s.place(C_, "C1", "220u 50V", 170, 108)
s.wire((145, 95), (170, 95), s.pin("C1", "1"))
s.junction((170, 95))
s.wire(s.pin("C1", "2"), (170, 130))
gnd_tap(170, 130)
s.wire((170, 95), (195, 95))
tap(195, 95, VSY)

s.place(BUCK, "U1", "LM2596HV", 110, 175)
s.wire(s.pin("U1", "1"), (85, 175))
tap(85, 175, VSY)
s.wire(s.pin("U1", "2"), (80, 178), (80, 210))
gnd_tap(80, 210)
s.place(C_, "C2", "220u 10V", 165, 183)
s.wire(s.pin("U1", "3"), (165, 175), s.pin("C2", "1"))
s.junction((165, 175))
s.wire(s.pin("C2", "2"), (165, 210))
gnd_tap(165, 210)
s.wire((165, 175), (190, 175))
tap(190, 175, V5Y)

s.place(CONN, "J3", "to handset", 70, 255)
for i, nm in enumerate(["HND_V", "GND", "HND_A", "HND_B"]):
    p = s.pin("J3", str(i + 1))
    s.wire(p, (p[0] - 16, p[1]))
    if nm == "GND":
        gnd_tap(p[0] - 16, p[1])
    else:
        s.glabel(nm, p[0] - 16, p[1], 180)
s.place(CONN, "J2", "to motor housing", 70, 310)
for i, nm in enumerate(["VSW", "GND", "MOT_A", "MOT_B"]):
    p = s.pin("J2", str(i + 1))
    s.wire(p, (p[0] - 16, p[1]))
    if nm == "GND":
        gnd_tap(p[0] - 16, p[1])
    elif nm == "VSW":
        tap(p[0] - 16, p[1], VSY)
    else:
        s.glabel(nm, p[0] - 16, p[1], 180)

s.note("ROCKER SENSE  (dry contacts in board mode)", 48, 358, 2.0)
for i, (rs, dc, rp, src, dst) in enumerate(
        [("R11", "D8", "R13", "HND_A", "SW_UP"),
         ("R14", "D9", "R15", "HND_B", "SW_DN")]):
    y = 382 + i * 55
    s.place(RH, rs, "4k7", 95, y)
    s.wire(s.pin(rs, "1"), (72, y))
    s.glabel(src, 72, y, 180)
    s.wire(s.pin(rs, "2"), (135, y))
    s.place(DV, dc, "BAT54", 135, y - 16)
    s.wire(s.pin(dc, "2"), (135, y))
    s.junction((135, y))
    s.wire(s.pin(dc, "1"), (135, y - 30))
    s.place(R_, rp, "100k", 168, y - 16)
    s.wire(s.pin(rp, "2"), (168, y), (135, y))
    s.junction((168, y))
    s.wire(s.pin(rp, "1"), (168, y - 30), (135, y - 30))
    s.junction((135, y - 30))
    tap(135, y - 30, V3Y)
    s.wire((168, y), (200, y))
    s.glabel(dst, 200, y)

# ========================================================== controller ====
s.note("CONTROLLER", 250, 74, 2.6)
s.place(MCU, "U2", "ESP32 + display", 290, 140)
s.wire(s.pin("U2", "1"), (255, 122))
tap(255, 122, V5Y)
s.wire(s.pin("U2", "2"), (250, 125), (250, 178))
gnd_tap(250, 178)
s.wire(s.pin("U2", "3"), (245, 128))
tap(245, 128, V3Y)

MCU_OUT = {"4": "DIR_A", "5": "DIR_B", "6": "PWM", "7": "MODE",
           "8": "KICK", "9": "ISENSE", "10": "SDA", "11": "SCL",
           "12": "SW_UP", "13": "SW_DN"}
pins = {k: s.pin("U2", k) for k in MCU_OUT}

for i, (num, ref) in enumerate([("4", "R1"), ("5", "R2"), ("6", "R6"),
                                ("7", "R12")]):
    p = pins[num]
    x = 345 + i * 17
    s.place(R_, ref, "10k", x, 220)
    s.wire((x, p[1]), (x, 216))
    s.junction((x, p[1]))
    s.wire(s.pin(ref, "2"), (x, 240))
    gnd_tap(x, 240)
s.note("hold drive lines safe before boot", 340, 256, 1.6)

for num in ("4", "5", "6", "7", "8"):
    s.wire(pins[num], (415, pins[num][1]))
for num in ("9", "10", "11", "12", "13"):
    p = pins[num]
    s.wire(p, (p[0] + 14, p[1]))
    s.glabel(MCU_OUT[num], p[0] + 14, p[1])

# ===================================================== watchdog + gating ==
s.note("WATCHDOG + GATING", 440, 74, 2.6)
s.place(MONO, "U3", "74HC123 250ms", 490, 120)
s.wire(s.pin("U3", "1"), (455, 102))
tap(455, 102, V5Y)
s.wire(s.pin("U3", "2"), (450, 105), (450, 165))
gnd_tap(450, 165)
pa3 = s.pin("U3", "3")
s.wire((415, pins["8"][1]), (415, pa3[1]), pa3)
p4, p5 = s.pin("U3", "4"), s.pin("U3", "5")
s.wire(p4, (438, p4[1]), (438, p5[1]), p5)
s.junction((438, p5[1]))
s.wire((438, p4[1]), (438, 96))
tap(438, 96, V5Y)
p6, p7 = s.pin("U3", "6"), s.pin("U3", "7")
s.wire(p6, (430, p6[1]), (430, p7[1]), p7)
s.junction((430, p7[1]))
s.place(R_, "R3", "100k", 420, 100)
s.wire(s.pin("R3", "2"), (420, p7[1]), (430, p7[1]))
s.wire(s.pin("R3", "1"), (420, 90))
tap(420, 90, V5Y)
s.place(C_, "C3", "2u2", 408, 130)
s.wire(s.pin("C3", "1"), (408, p7[1]), (420, p7[1]))
s.junction((420, p7[1]))
s.wire(s.pin("C3", "2"), (408, 160))
gnd_tap(408, 160)

WDX = 472.0
pq = s.pin("U3", "8")
s.wire(pq, (525, pq[1]), (525, 178), (WDX, 178), (WDX, 335))
s.label("WDOG", WDX + 2, 182)

GATES = [("U8", "4", 205), ("U9", "5", 245), ("U12", "7", 285),
         ("U6", "6", 325)]
for ref, src, y in GATES:
    s.place(AND2, ref, "74HC08", 500, y)
    pa, pb, py = s.pin(ref, "1"), s.pin(ref, "2"), s.pin(ref, "3")
    s.wire((415, pins[src][1]), (415, pa[1]), pa)
    s.wire((WDX, pb[1]), pb)
    s.junction((WDX, pb[1]))
s.note("one 74HC08, four gates", 472, 352, 1.6)

s.place(DRVX, "U7", "TC4427", 500, 385)
s.wire(s.pin("U7", "1"), (465, 377))
tap(465, 377, V5Y)
s.wire(s.pin("U7", "2"), (460, 380), (460, 415))
gnd_tap(460, 415)
pu6 = s.pin("U6", "3")
s.wire(pu6, (536, pu6[1]), (536, 366), (472, 366),
       (472, s.pin("U7", "3")[1]), s.pin("U7", "3"))

# =============================================================== drive ====
s.note("DRIVE", 580, 74, 2.6)
for ref, gate_ref, y in (("Q2", "U8", 205), ("Q3", "U9", 245),
                         ("Q4", "U12", 285)):
    s.place(NMOS, ref, "2N7002", 580, y + 12)
    pg = s.pin(ref, "1")
    pgy = s.pin(gate_ref, "3")
    s.wire(pgy, (pg[0] - 20, pgy[1]), (pg[0] - 20, pg[1]), pg)
    s.wire(s.pin(ref, "3"), (580, y + 45))
    gnd_tap(580, y + 45)

s.place(NMOS, "Q1", "IRLB8721", 580, 405)
pgd = s.pin("U7", "4")
s.wire(pgd, (s.pin("Q1", "1")[0] - 14, pgd[1]),
       (s.pin("Q1", "1")[0] - 14, s.pin("Q1", "1")[1]), s.pin("Q1", "1"))
s.wire(s.pin("Q1", "3"), (580, 440))
gnd_tap(580, 440)
MRETX = 712.0
s.wire(s.pin("Q1", "2"), (580, 378), (MRETX, 378))
s.place(DV, "D5", "SB560", 660, 356)
s.wire(s.pin("D5", "2"), (660, 378))
s.junction((660, 378))
s.wire(s.pin("D5", "1"), (660, 340))
tap(660, 340, VSY)

RY = [("K1", "direction A", 105), ("K2", "direction B", 160),
      ("K3", "transfer A", 215), ("K4", "transfer B", 270),
      ("K5", "handset rail", 325)]
V5F, VSF = 632.0, 758.0
for ref, val, y in RY:
    s.place(RLY, ref, val, 680, y)
    pcp = s.pin(ref, "1")
    s.wire(pcp, (V5F, pcp[1]))
    s.junction((V5F, pcp[1]))
s.wire((V5F, s.pin("K1", "1")[1]), (V5F, s.pin("K5", "1")[1]))
tap(V5F, s.pin("K1", "1")[1], V5Y)

for qref, kref, dref in (("Q2", "K1", "D2"), ("Q3", "K2", "D6"),
                         ("Q4", "K3", "D7")):
    pd = s.pin(qref, "2")
    pc = s.pin(kref, "2")
    s.wire(pd, (pd[0], pc[1]), pc)
    ymid = (s.pin(kref, "1")[1] + pc[1]) / 2
    s.place(DV, dref, "flyback", 648, ymid)
    s.wire(s.pin(dref, "1"), (648, s.pin(kref, "1")[1]))
    s.junction((648, s.pin(kref, "1")[1]))
    s.wire(s.pin(dref, "2"), (648, pc[1]))
    s.junction((648, pc[1]))

k3c = s.pin("K3", "2")
for kref in ("K4", "K5"):
    pc = s.pin(kref, "2")
    s.wire((640, k3c[1]), (640, pc[1]), pc)
s.junction((640, k3c[1]))

DRVAX, DRVBX = 706.0, 730.0
s.wire(s.pin("K1", "3"), (DRVAX, s.pin("K1", "3")[1]),
       (DRVAX, s.pin("K3", "5")[1]), s.pin("K3", "5"))
s.label("DRV_A", DRVAX + 2, s.pin("K1", "3")[1] - 2)
s.wire(s.pin("K2", "3"), (DRVBX, s.pin("K2", "3")[1]),
       (DRVBX, s.pin("K4", "5")[1]), s.pin("K4", "5"))
s.label("DRV_B", DRVBX + 2, s.pin("K2", "3")[1] - 2)
for ref in ("K1", "K2"):
    p = s.pin(ref, "5")
    s.wire(p, (MRETX, p[1]))
    s.junction((MRETX, p[1]))
s.wire((MRETX, s.pin("K1", "5")[1]), (MRETX, 378))
s.label("MRET", MRETX + 2, 372)

for ref in ("K1", "K2", "K5"):
    p = s.pin(ref, "4")
    s.wire(p, (VSF, p[1]))
    s.junction((VSF, p[1]))
s.wire((VSF, s.pin("K1", "4")[1]), (VSF, s.pin("K5", "4")[1]))
tap(VSF, s.pin("K1", "4")[1], VSY)
p = s.pin("K5", "5")
s.wire(p, (775, p[1]))
tap(775, p[1], V3Y)
for ref, num, net in (("K3", "4", "HND_A"), ("K4", "4", "HND_B"),
                      ("K5", "3", "HND_V"), ("K4", "3", "MOT_B")):
    p = s.pin(ref, num)
    s.wire(p, (p[0] + 16, p[1]))
    s.glabel(net, p[0] + 16, p[1])

s.place(ACS, "U5", "ACS724-5AB", 680, 445)
s.wire(s.pin("U5", "1"), (645, 427))
tap(645, 427, V5Y)
s.wire(s.pin("U5", "2"), (640, 430), (640, 480))
gnd_tap(640, 480)
pk3 = s.pin("K3", "3")
s.wire(pk3, (700, pk3[1]), (700, 408), (618, 408),
       (618, s.pin("U5", "3")[1]), s.pin("U5", "3"))
s.label("TRAN_A", 702, pk3[1] - 2)
pio = s.pin("U5", "4")
s.wire(pio, (pio[0] + 16, pio[1]))
s.glabel("MOT_A", pio[0] + 16, pio[1])
s.place(R_, "R4", "10k", 745, 445)
s.wire(s.pin("U5", "5"), (745, s.pin("U5", "5")[1]), (745, 441))
s.place(R_, "R5", "20k", 745, 473)
s.wire(s.pin("R4", "2"), s.pin("R5", "1"))
s.wire((745, 462), (770, 462))
s.junction((745, 462))
s.glabel("ISENSE", 770, 462)
s.wire(s.pin("R5", "2"), (745, 495))
gnd_tap(745, 495)

# ================================================================= leg ====
s.note("LEG (unmodified)", 250, 400, 2.6)
s.box(240, 412, 400, 470)
s.place(LIM, "SW3", "top limit", 290, 428)
s.place(DH, "D3", "allows down", 290, 455)
s.wire((272, 428), (272, 455))
s.wire((272, 428), s.pin("SW3", "1"))
s.wire((272, 455), s.pin("D3", "1"))
s.wire((310, 428), (310, 455))
s.wire(s.pin("SW3", "2"), (310, 428))
s.wire(s.pin("D3", "2"), (310, 455))
s.wire((272, 441), (255, 441))
s.junction((272, 441))
s.glabel("MOT_A", 255, 441, 180)
s.place(MOT, "M1", "2R5 winding", 335, 441)
s.wire((310, 441), s.pin("M1", "1"))
s.junction((310, 441))
s.place(LIM, "SW4", "bottom limit", 375, 428)
s.place(DH, "D4", "allows up", 375, 455)
s.wire((357, 428), (357, 455))
s.wire((357, 428), s.pin("SW4", "1"))
s.wire((357, 455), s.pin("D4", "2"))
s.wire((395, 428), (395, 455))
s.wire(s.pin("SW4", "2"), (395, 428))
s.wire(s.pin("D4", "1"), (395, 455))
s.wire(s.pin("M1", "2"), (357, 441))
s.junction((357, 441))
s.wire((395, 441), (414, 441))
s.junction((395, 441))
s.glabel("MOT_B", 414, 441)

notes = [
    "IN-LINE INTERCEPTOR.  The handset keeps its factory wiring and still switches motor current in OEM mode.",
    "This board cuts into the 4-core cable between handset and motor housing; unplug it and rejoin the cable",
    "to return the desk to stock.",
    "",
    "K3 / K4 / K5 share one coil node and act as a 3-pole transfer:",
    "    de-energised  ->  handset sees VSW and drives the winding   (STOCK BEHAVIOUR)",
    "    energised     ->  handset sees +3V3 and is isolated from the winding",
    "Power loss or a watchdog timeout drops the transfer and hands the desk back to the rockers.",
    "",
    "K1 / K2 give brake at rest exactly as the OEM rockers do.  Both off -> both winding ends on VSW.",
    "No combination of relay states can short the supply; there is no shoot-through failure mode.",
    "",
    "SEQUENCING: relays change state only with Q1 off and current decayed.  On a watchdog trip Q1 turns off",
    "in microseconds while relays take milliseconds to release, so contacts are cold-switched even in a fault.",
    "",
    "U5 sits after the transfer relay, in the motor leg proper, so it reads current in BOTH modes.",
    "K3 / K4 carry full motor current in OEM mode - rate them for the load.",
    "R1/R2/R6/R12 must sit on non-strapping GPIOs.  ISENSE must be on ADC1 (ADC2 is unusable with WiFi).",
]
for i, t in enumerate(notes):
    if t:
        s.note(t, 48, 545 + i * 5.6, 1.6)

open("desk_inline.kicad_sch", "w").write(s.render())
print("wrote desk_inline.kicad_sch")
