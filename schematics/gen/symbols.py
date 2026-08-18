"""Shared symbol library for the desk schematic.

Extracted from the symbol-definition preamble originally common to this
generator and two now-dropped variants (itself originally
`_sym_preamble.py`, exec'd from a path that only existed in the session
that produced this repo and was never committed). This module exists so
sch.py has one to import.
"""
import os

from schlib import Schematic, Sym, poly, rect, BGFILL, import_symbol  # noqa: F401,E501

KICAD_SYMBOLS = "/usr/share/kicad/symbols"
# Not part of the local Kicad install - vendored from
# github.com/espressif/kicad-libraries (CC-BY-SA 4.0) because it has the
# one thing neither the system libraries nor Arduino_Nano_ESP32 do: an
# ESP32-S3-DevKitC symbol with bare GPIO-numbered pins, matching how this
# design already refers to pins everywhere else in the project.
ESPRESSIF_SYMBOLS = os.path.join(os.path.dirname(__file__), "espressif.kicad_sym")

P, I, O, PWI, PWO = "passive", "input", "output", "power_in", "power_out"

# power=True is what actually merges every placement of these into one
# global net by value/pin name - without it each instance is just an
# ordinary component that happens to share a value string, not a real
# connection (see schlib.Sym). Real parts: power.kicad_sym's own GND/+5V
# - both already carry (power global) natively, no override needed.
# One imported "+5V" symbol (a plain arrow - the same shape Kicad's own
# library uses for every voltage rail) is reused for every rail name in
# this design, including ones Kicad doesn't ship (nothing named "VSW"
# exists): net identity for a power symbol comes from the *placed
# instance's* own Value text (which tap()/place() always set
# explicitly), not from which library symbol drew the arrow, so one
# shared arrow for +5V/+3V3/VSW is exactly as correct as three separate
# ones would be.
GNDS = import_symbol(f"{KICAD_SYMBOLS}/power.kicad_sym", "GND", prefix="#PWR")
_RAIL_SYM = import_symbol(f"{KICAD_SYMBOLS}/power.kicad_sym", "+5V",
                          prefix="#PWR")


def _rail(name):
    return _RAIL_SYM


RAILS = {}

# Real parts: generic passives/discretes from Kicad's own libraries. Pin
# geometry already matches almost exactly what the hand-drawn versions
# used (R/C both default to vertical pins at (0,+-3.81); D defaults to
# horizontal, K/A at (+-3.81,0)) - where this design needs the other
# orientation (RH's old role), the call site passes angle=90/270 to the
# same imported symbol instead of a separate pre-rotated object -
# place()/pin() already rotate pin positions for any angle, the same
# mechanism used for genuine part rotations elsewhere in sch.py,
# so a second object would just be a duplicate.
# ref_dy/val_dy/dx explicitly overridden for all three: their library-
# stored label offsets are clearly meant to be re-autoplaced by Kicad's
# editor per instance (Value sits at the exact origin, on top of the
# body, with a 90 degree text-rotation our importer doesn't even read) -
# not usable as a static default the way the relay/transistor parts'
# were. Ref/value kept an equal distance from centre, on either side.
# Standard 1/4W axial THT resistor - every R_ instance in this design
# (100k/10k/4k7/1k/20k) is a small-signal or pull-up/pull-down value,
# none of them power resistors needing a bigger body.
R_ = import_symbol(f"{KICAD_SYMBOLS}/Device.kicad_sym", "R",
                   ref_dy=2.8, val_dy=-2.8, ref_dx=3.4, val_dx=3.4)
R_.footprint = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
# Default is a small ceramic disc, matching C3 (2u2 timing cap) - C1/C2
# are 220uF electrolytics and need a much bigger radial-can footprint,
# overridden per instance in sch.py's own place() calls.
C_ = import_symbol(f"{KICAD_SYMBOLS}/Device.kicad_sym", "C",
                   ref_dy=2.8, val_dy=-2.8, ref_dx=4.4, val_dx=4.4)
C_.footprint = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
# Default is small-signal DO-35 (1N4148), matching D2/D3/D4/D6 - D5
# (SB560) is a bigger Schottky and needs DO-201AD, overridden per
# instance in sch.py.
DH = import_symbol(f"{KICAD_SYMBOLS}/Device.kicad_sym", "D",
                   ref_dy=4.4, val_dy=-4.4)
DH.footprint = "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"
# No generic bidirectional TVS symbol exists in this Kicad library
# snapshot (only specific parts like TVS0500DRV) - kept hand-drawn.
TVS = Sym("TVS", "D", [("1", "1", P, 0, 6.35, 270, 3.81),
                       ("2", "2", P, 0, -6.35, 90, 3.81)],
          [poly([(-2.54, 0.5), (2.54, 0.5), (0, 3.4), (-2.54, 0.5)], BGFILL),
           poly([(-2.54, -0.5), (2.54, -0.5), (0, -3.4), (-2.54, -0.5)],
                BGFILL)], ref_dy=2.2, val_dy=-2.2, ref_dx=4.4, val_dx=4.4,
          justify="left")
# DO-15, matching the P6KE33CA/1.5KE33CA axial TVS parts README 6.5 names.
TVS.footprint = "Diode_THT:D_DO-15_P10.16mm_Horizontal"
# ref_dy/val_dy overridden to match the BJT parts' spacing exactly (1.27
# to -1.27) - the library's own stored gap (1.905 to 0) is tighter, even
# though the body is about the same size.
NMOS = import_symbol(f"{KICAD_SYMBOLS}/Transistor_FET.kicad_sym",
                     "Q_NMOS_GDS", prefix="Q", ref_dy=1.27, val_dy=-1.27)
# Default is TO-92 with leads spread to 2.54mm pitch (not the native
# 1.27mm), matching Q2/Q3 (2N7000) - standard practice for hand assembly,
# and it's what a 0.4mm home-fab clearance rule needs: at native pitch
# the 3 legs sit too close together for that clearance, since all 3 are
# on different nets. Also matches standard perfboard hole spacing, which
# 1.27mm pitch wouldn't. Q1 (IRLZ44N) is TO-220 and needs the bigger
# footprint, overridden per instance in sch.py.
NMOS.footprint = "Package_TO_SOT_THT:TO-92_Wide"
# M1 is the existing motor, not populated on this board.
MOT = import_symbol(f"{KICAD_SYMBOLS}/Motor.kicad_sym", "Motor_DC",
                    prefix="M")
# ref_dy/val_dy overridden: the library's stored gap (2.54 to -1.905,
# 4.445mm total) is too tight for this design's longer Value strings
# ("top limit" etc) - they end up overlapping the Reference right next
# to them. Matches DH/other simple 2-pin parts' clearance instead.
LIM = import_symbol(f"{KICAD_SYMBOLS}/Switch.kicad_sym", "SW_Push_Open",
                    prefix="SW", ref_dy=4.4, val_dy=-4.4)
# Handset rocker: real SPDT part instead of a hand-drawn switch - the OEM
# handset's two rockers are momentary SPDT contacts (README S2.5), same
# class of part as LIM just with a common pole (pin 2) instead of NO-only.
ROCKER = import_symbol(f"{KICAD_SYMBOLS}/Switch.kicad_sym", "SW_Push_SPDT",
                       prefix="SW")
# Real part instead of hand-drawn: EN50005 SPDT relay, pins 11/12/14 (the
# switch contacts) and A1/A2 (coil) - kept at the library's own positions
# rather than remapped to the old RELAY layout, so routing is adapted to
# this in sch.py rather than the part being bent back to match it.
# Pin names are blank on this real part (only the numbers carry meaning,
# same as a connector) and it doesn't hide numbers itself, so both show
# up matching what a connector-style part wants - nothing to override.
RLY = import_symbol(f"{KICAD_SYMBOLS}/Relay.kicad_sym", "Relay_SPDT",
                    prefix="K")
# Bare relay (this design drives the coil directly with Q2/Q3/D2/D6, not
# through a driver-included module - see NETLIST.md). Switched from the
# Songle SRD-05VDC-SL-C originally specced to the Hongfa JQC-3FF/005-1ZS
# (same "subminiature 1 Form C, 5V/10A PCB relay" class, extremely common,
# in stock at LCSC) specifically because this footprint's pad names are
# "11"/"12"/"14"/"A1"/"A2" - the SAME names as this generic Relay_SPDT
# symbol's pins, not renumbered "1".."5" like the SANYOU footprint was.
# That renumbering is what caused K1/K2 to import with zero net
# assignment on the PCB (pin "A1" had no matching pad named "A1") without
# ever throwing a visible error - a silent gap found only by noticing the
# PCB pads still read netcode 0 after everything else routed. 11/12/14
# is the standard DIN SPDT relay numbering (common/NC/NO) essentially
# every manufacturer of this relay style follows, so pin-number matching
# between symbol and footprint is trustworthy here, unlike guessing NC
# vs NO from a datasheet picture.
RLY.footprint = "Relay_THT:Relay_SPDT_Hongfa_JQC-3FF_0XX-1Z"


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


# Real part: LM2596T-5 (fixed 5V, TO-220-5 THT) - LM2596T-12 is the base
# symbol it `extends` (same "thin wrapper" pattern as 74HC123/BC337),
# importing it gets the real pins/graphics; place() still sets the
# instance's own Value. This library snapshot has no HV (high-input-
# voltage) variant, so this is a pin-compatible placeholder for the
# actual LM2596HV, same reasoning as 74LS08 standing in for 74HC08 (see
# TODO.md). Real pinout adds two pins the hand-drawn box never had: FB
# (feedback - must be wired to VOUT for the regulator to work at all,
# fixed-output parts still sense their own output externally) and
# ~ON/OFF (must be tied low for always-on operation, floating is not a
# valid state) - both wired in sch.py.
BUCK = import_symbol(f"{KICAD_SYMBOLS}/Regulator_Switching.kicad_sym",
                     "LM2596T-12", prefix="U")
# Bare chip (TO-220-5), not a buck module - the real pinout wired here
# (FB, ~ON/OFF) only exists on the bare part; a prebuilt module would
# only expose VIN/VOUT/GND. README 6.5's "modules with headers" line
# lumped this in with U2/relays incorrectly - fix that wording too.
BUCK.footprint = "Package_TO_SOT_THT:TO-220-5_Vertical"
# OUT (pin 2) is generically typed "output" in the library, not
# "power_out" - accurate for an adjustable part where OUT could feed
# anything, but this fixed-5V regulator's OUT *is* the +5V source, and
# ERC otherwise reports the whole +5V rail as undriven. Overridden the
# same way a hand-drawn Sym's pins are edited.
BUCK.pins_by_unit[1] = [
    p if p[0] != "2" else (p[0], p[1], PWO, *p[3:])
    for p in BUCK.pins_by_unit[1]
]
# Real part: ESP32-S3-DevKitC (Espressif's own devkit symbol, see
# ESPRESSIF_SYMBOLS above). Bare devkit, no display - this hardware lives
# under the desk, not somewhere a display would ever be seen; a display,
# if ever added, would be a separate on-desk peripheral in a later phase
# (README 5). Chosen over Arduino_Nano_ESP32 because it exposes bare
# GPIO-numbered pins - matching how this design already refers to every
# signal, and avoiding a board (the Nano) whose exposed pin set doesn't
# even overlap with the GPIOs this design uses (see conversation - most
# of them aren't broken out on that board at all).
#
# GPIO_PIN maps a GPIO number to this symbol's own pin number (its 44
# pins are numbered 1-44 on the physical part, unrelated to the GPIO
# number) - regenerate from the raw library file
# (github.com/espressif/kicad-libraries, CC-BY-SA 4.0) if the chip/pin
# selection ever changes.
MCU = import_symbol(ESPRESSIF_SYMBOLS, "ESP32-S3-DevKitC", prefix="U")
# Genuinely a module (unlike BUCK/RLY - the whole point of this part is
# the devkit board, not a bare chip), socketed rather than soldered
# direct so it's removable. 44 pins, 2 rows of 22 at the standard 1 inch
# (25.4mm) devkit row spacing - confirmed against a real board's own
# dimension drawing (2x22, 2.54mm pin pitch, 25.40mm row spacing, 53.34mm
# pin-1-to-pin-22 span). No stock KiCad footprint has a 2x22 socket at
# this spacing (the closest, PinSocket_2x22_P2.54mm_Vertical, is a
# single-pitch header with both rows only 2.54mm apart - a solid
# obstacle a router can't find a path through, not a real connector with
# a channel down the middle); built as two PinSocket_1x22_P2.54mm's,
# pins 1-22 and 23-44, spaced 25.4mm apart - see local.pretty/ and
# fp-lib-table. Still a placeholder pin-numbering scheme (1-22 down one
# row, 23-44 down the other) - verify against the real board's own
# silkscreen before ordering a specific part.
MCU.footprint = "local:DevKitC_2x22_P2.54mm_1in_row"
GPIO_PIN = {
    0: "31", 1: "41", 2: "40", 3: "13", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "12", 9: "15", 10: "16", 11: "17", 12: "18", 13: "19", 14: "20",
    17: "10", 18: "11", 19: "25", 20: "26", 21: "27",
    35: "32", 36: "33", 37: "34", 38: "35", 39: "36", 40: "37",
    41: "38", 42: "39", 43: "43", 44: "42", 45: "30", 46: "14",
    47: "28", 48: "29",
}
# 5V/GND/3V3 by their own real pin numbers (not GPIOs). 3V3 has 2
# physical pins (1/2) and GND has 4 (22/23/24/44) - only one of each is
# wired, same as the old hand-drawn box only ever had one.
MCU_5V, MCU_GND, MCU_3V3 = "21", "22", "1"
# 3V3 (pin 1) is typed passive in the library (its duplicate, pin 2, is
# power_in) - neither satisfies ERC's "net needs a power_out somewhere"
# check, which is backwards for how this design actually uses U2: the
# ESP32's own onboard regulator is what sources +3V3 for the handset
# (see NETLIST.md), same as the old hand-drawn box already had it (5V
# power_in, 3V3 power_out) - only 3V3 needs the override, 5V's own
# power_in is already correct here.
MCU.pins_by_unit[1] = [
    p if p[0] != MCU_3V3 else (p[0], p[1], PWO, *p[3:])
    for p in MCU.pins_by_unit[1]
]
# Real part: 74LS123 (74HC123 is a thin "extends" wrapper around this
# same pinout in Kicad's own library - importing the base part directly
# gets the actual pins/graphics; the instance's own Value text is still
# set to "74HC123 ..." wherever it's placed, so the BOM/notes are
# unaffected). It's a DUAL monostable and this design only ever used one
# half - unit 1 is that half (A/B/Clr/Cext/RCext/Q), unit 3 is the shared
# VCC/GND, placed separately since Kicad draws multi-unit parts as
# separate placements sharing one reference.
# Ref/value both sit above the body, ref further out than value (matches
# Kicad's own auto-placement for this part: dy = half-height+5.08 for
# ref, half-height+2.54 for value - confirmed by placing the part in
# Kicad itself and reading back where it auto-placed the labels) - unit
# 3 (power) overrides this with
# explicit ref_at/val_at in sch.py instead, since Kicad's own
# rendering puts a power-only unit's labels beside it, not above.
MONO = import_symbol(f"{KICAD_SYMBOLS}/74xx.kicad_sym", "74LS123",
                     prefix="U", ref_dy=12.7, val_dy=10.16)
MONO.footprint = "Package_DIP:DIP-16_W7.62mm"
# Real part: 74LS08 (74HC08, used everywhere else in this design, isn't
# in this Kicad library snapshot at all - 74LS08 is a pin-compatible
# placeholder pending a real part decision, see TODO.md). Quad 2-input
# AND gate - units 1/2/3 are the three gates this design actually uses,
# unit 4 is the unused fourth gate, unit 5 is the shared VCC/GND.
# Ref/value both above the body, ref further out - see MONO's note.
AND2 = import_symbol(f"{KICAD_SYMBOLS}/74xx.kicad_sym", "74LS08",
                     prefix="U", ref_dy=8.89, val_dy=6.35)
AND2.footprint = "Package_DIP:DIP-14_W7.62mm"
# Gate driver is discrete instead of an IC: a complementary BJT push-pull
# (BC337 NPN + BC327 PNP, both on hand already) driven by the AND gate's
# 5V output through a base resistor. Output swings ~0.6V (off, well under
# Vgs(th)) to ~4.4V (on) - not a full 0-5V swing, but close enough to the
# 5V Vgs Q1's own "logic level" Rds(on) is characterised at that it isn't
# the compromise it looks like. Q1 is IRLZ44N, not IRLB8721 - the latter's
# 30V VDSS doesn't clear this 29-30V rail, see README 6.2. Both BJTs share
# the same generic CBE pin layout (C top, B left, E bottom); PNP is placed
# mirrored (see sch.py) so its collector points down to GND instead of up.
# BC337/BC327 themselves are thin "extends" wrappers in Kicad's library
# (same reason 74HC123 needed 74LS123) - importing the generic base
# symbol directly gets the real pins/graphics; place() still sets the
# instance's own Value to "BC337"/"BC327" wherever they're used.
BJT_NPN = import_symbol(f"{KICAD_SYMBOLS}/Transistor_BJT.kicad_sym",
                        "Q_NPN_CBE", prefix="Q")
BJT_NPN.footprint = "Package_TO_SOT_THT:TO-92_Wide"
BJT_PNP = import_symbol(f"{KICAD_SYMBOLS}/Transistor_BJT.kicad_sym",
                        "Q_PNP_CBE", prefix="Q")
BJT_PNP.footprint = "Package_TO_SOT_THT:TO-92_Wide"
# Real part: ACS724xLCTR-05AB (ACS712xLCTR-05B is the base symbol it
# `extends`, same "thin wrapper" pattern as 74HC123/BC337 - importing the
# base gets the real pins/graphics; place() still sets the instance's own
# Value to "ACS724xLCTR-05AB"). Real pinout is fixed: VCC top, GND
# bottom, IP+/IP- both on the left (stacked, IP+ above IP-), VIOUT/FILTER
# both on the right - unlike the old hand-drawn placeholder, which put
# VCC/GND on the left and everything else on the right. See
# sch.py for which of IP+/IP- ends up facing K1 vs J2 (the part
# doesn't care which way current flows through it for this design - see
# README 4.4 - so it's picked for routing, not signal sense).
# ref_dy/val_dy overridden (dx/justify left as the library specifies):
# the library's own stored dy (11.43/8.89) sits *inside* the VCC pin's
# own name+number text (pin tips already reach 10.16) and renders
# garbled - stale data from whenever this part was last autoplaced in
# its own library, same as MONO/AND2's stored values didn't match a
# fresh Kicad auto-placement either. A bit further out clears the pin
# text.
ACS = import_symbol(f"{KICAD_SYMBOLS}/Sensor_Current.kicad_sym",
                    "ACS712xLCTR-05B", prefix="U",
                    ref_dy=12.7, val_dy=10.16)
# The bare chip is SOIC-8 (README 6.5) - not through-hole, so this is
# actually the Pololu ACS724 carrier board, socketed like U2. 8 pins,
# single row - a generic placeholder; verify against the carrier's own
# hole spacing once it's in hand.
ACS.footprint = "Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical"
# Real part: Conn_02x02_Top_Bottom - closer to physical reality than a
# single row (J2/J3 are both Molex Mini-Fit Jr, 4 circuit dual row, per
# README 1.5). "Top_Bottom" numbers row-major (pins 1,2 = row 1; pins
# 3,4 = row 2), confirmed against Molex's own 5557-series sales drawing
# (SD-5557-003) - which is also what README 1.6's circuit diagram uses
# (motor pair = circuits 1,2; supply pair = circuits 3,4). The symbol
# draws pins 1/2 as a left column and 3/4 as a right column (KiCad's
# generic connector symbols draw this way regardless of N, purely for
# schematic layout - it doesn't imply anything about physical left/right,
# which this project deliberately doesn't rely on - see README 1.6).
CONN = import_symbol(f"{KICAD_SYMBOLS}/Connector_Generic.kicad_sym",
                     "Conn_02x02_Top_Bottom", prefix="J")
# The board-side Mini-Fits (formerly J2, J3) are dropped from this sheet
# entirely - the board only ever solders to screw terminals (no crimp
# tool needed for board assembly), and a short crimped pigtail, off-board,
# carries each circuit on to the actual Mini-Fit pin. That pigtail/mating
# detail belongs with the connector reference (README 1.5/1.6, NETLIST.md),
# not duplicated as a second connector symbol here. CONN (J1, J4) still
# stands for the real Mini-Fits at the far end, inside the motor housing/
# handset. 2-position, 2.54mm pitch - same pitch as CONN's own pins, which
# is what lets a terminal drop into an existing pair's wiring unchanged.
TERM2 = import_symbol(f"{KICAD_SYMBOLS}/Connector.kicad_sym",
                      "Screw_Terminal_01x02", prefix="TB")
# 5.00mm pitch - a common, easy-to-source real terminal block pitch,
# unrelated to the symbol's own 2.54mm drawn pin spacing (schematic
# layout only; footprint pads match symbol pins by number, not position).
TERM2.footprint = "TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm"
# U2's 2x22 header is a genuine copper-layer capacity wall: every
# crossing point between its margin and the rest of the board is used
# up by other nets, and even a connector placed right at U2 doesn't
# help - its body doesn't fit what little margin is left, and per-signal
# jumpers there still fought the same congestion piecemeal (see
# conversation - that attempt got messy: some signals on direct PCB
# copper, some on pigtails, wires crossing body outlines). Cleaner fix:
# U2 isn't on this board at all (`on_board=False` below, same mechanism
# already used for the motor/handset/PSU) - it lives elsewhere as a
# free-standing DevKitC, and EVERY signal it needs crosses on a
# hand-soldered wire into one of three small JST-XH connectors, grouped
# by function so there's one plug for power, one for the four drive
# outputs, one for the two rocker inputs + current sense - matching
# "plenty of JST plugs, one set for each of power/handset input/driver
# output" from conversation. 2.50mm pitch is JST's own native pitch,
# not a match to this board's 2.54mm grid; the ~0.04mm per pin
# accumulated error is irrelevant at 3-4 pins.
JP3 = import_symbol(f"{KICAD_SYMBOLS}/Connector_Generic.kicad_sym",
                    "Conn_01x03", prefix="JP")
JP3.footprint = "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"
JP4 = import_symbol(f"{KICAD_SYMBOLS}/Connector_Generic.kicad_sym",
                    "Conn_01x04", prefix="JP")
JP4.footprint = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
# Real part: HLK-30M05 is the base symbol HLK-30M24 (and every other
# HLK-30Mxx voltage) `extends` - same pattern as 74HC123/BC337/LM2596HV.
# No HLK part actually matches this desk's measured 29V/52W (every
# HLK-30M variant tops out at 30W; the closest voltage is 24V, not 29V) -
# used as a visual stand-in for "some AC-DC module", same as 74LS08
# stands in for 74HC08, but place() sets the instance Value to the
# measured 29V 1.8A 52W, not "HLK-30M24", so the schematic doesn't imply
# a lower wattage/voltage than what's actually in the desk (CLAUDE.md:
# the supply's own current limit is the desk's only collision
# protection, so this number matters).
PSU = import_symbol(f"{KICAD_SYMBOLS}/Converter_ACDC.kicad_sym",
                    "HLK-30M05", prefix="U")
# Mains L/N - power.kicad_sym's generic "AC" flag (same shape/mechanism
# as our own +5V/+3V3/VSW rails: one imported arrow, reused per instance
# via Value, not a specific connector - the real mains entry has never
# been opened up to identify one, so an abstract flag is more honest
# than guessing a connector part).
AC_FLAG = import_symbol(f"{KICAD_SYMBOLS}/power.kicad_sym", "AC",
                        prefix="#PWR")
