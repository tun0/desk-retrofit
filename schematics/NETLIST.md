# desk — schematic as text

Generated from KiCad's own netlist export (`kicad-cli sch export netlist`)
against the current `desk.kicad_sch`, so this reflects actual
connectivity, not the Python source. Regenerate the raw connection list (and
diff it against a saved copy, or another variant) with:

```sh
cd schematics && python3 sch.py && python3 netlist_text.py desk.kicad_sch
```

This document adds functional descriptions on top of that raw list. Kept as
a reference for understanding the circuit or rebuilding it by hand — not a
substitute for `sch.py`, which is the actual source of truth.

## Components

| Ref | Value | Notes |
|---|---|---|
| PS1 | 29V 1.8A 52W (via motor housing) | wall supply, current-limiting |
| D4 | 33V bidir | TVS, input transient protection; no fuse fitted, see README 6.1 |
| C4 | 220u 50V | input bulk cap |
| U5 | LM2576HVS-5.0 29V-5V | buck regulator, SMD (TO-263-5) - the true through-hole HV part wasn't sourceable, see README 6.5; real part is base symbol LM2596T-12, a pin-compatible non-HV placeholder for the library's own missing HV/SMD variant, see TODO.md |
| C5 | 220u 10V | +5V output cap |
| TB4 | motor pair | 2-position screw terminal; board-side termination for MOT_A/MOT_B, pigtails to J3 via J2 (no longer drawn - see Connectors) |
| TB5 | supply pair | 2-position screw terminal; board-side termination for VSW/GND, pigtails to J3 via J2 |
| TB1 | signal pair | 2-position screw terminal; board-side termination for HND_A/HND_B, pigtails to J4 via J1 |
| TB2 | power pair | 2-position screw terminal; board-side termination for +3V3/GND, pigtails to J4 via J1 |
| TB3 | ToF signal pair | 2-position screw terminal; SDA/GPIO38 and SCL/GPIO41 breakout for a future VL53L1X (Phase 2, not started - see README 8). Fully routed and DRC-clean - originally targeted GPIO12/13, moved after those pins proved unroutable, see README 8.1. +3V3/GND for the same sensor share TB2 (a second wire under each of its screws) rather than a dedicated terminal - a `TB6` for that was tried and dropped once TB2-sharing made it unnecessary. |
| U1 | ESP32 | bare devkit, no display - see README 5/6; real part is Espressif's ESP32-S3-DevKitC symbol (vendored, see Controller section) as the closest local match |
| R3 | 4k7 | HND_A series resistor (rocker divider) |
| R5 | 100k | SW_UP pull-up to +3V3 |
| R4 | 4k7 | HND_B series resistor (rocker divider) |
| R6 | 100k | SW_DN pull-up to +3V3 |
| U2 | 74HC123 250ms | monostable (retriggerable watchdog timer); real part is 74LS123, `74HC123` is a same-pinout wrapper in Kicad's library |
| R7 | 100k | U2 timing resistor |
| C1 | 2u2 | U2 timing capacitor |
| U3 | 74HC08 | triple AND gate (3 of 4 gates used); real part is 74LS08 placeholder, see TODO.md |
| R8 | 10k | DIR_A gate pulldown (boot-safe) |
| R9 | 10k | DIR_B gate pulldown (boot-safe) |
| R10 | 10k | PWM gate pulldown (boot-safe) |
| Q1 | BC337 | gate driver for Q5, NPN half of a discrete push-pull (replaces a TC4427 IC) |
| Q2 | BC327 | gate driver for Q5, PNP half of the push-pull |
| R11 | 1k | Q1/Q2 base resistor |
| Q5 | IRLZ44N | main PWM FET, low side |
| D1 | SB560 | freewheel diode |
| K1 | energized = UP (raises desk) | relay, real part Relay_SPDT (EN50005 pinout) |
| K2 | energized = DOWN (lowers desk) | relay, same part as K1 |
| D2 | flyback | K1 coil flyback diode |
| D3 | flyback | K2 coil flyback diode |
| Q3 | 2N7000 | K1 coil driver |
| Q4 | 2N7000 | K2 coil driver |
| U4 | ACS712ELCTR-05B | current sensor, in series with K1's leg; switched from ACS724xLCTR-05AB for real stock availability, checked pin-identical against both datasheets - see README 6.5/6.6. The library symbol used is literally named after this part now, no "extends" placeholder needed |
| R1 | 10k | ISENSE divider, top |
| R2 | 20k | ISENSE divider, bottom |
| SW1 | top limit | limit switch, in the leg |
| SW2 | bottom limit | limit switch, in the leg |
| D5 | allows down | SW1 bypass diode |
| D6 | allows up | SW2 bypass diode |
| M1 | 2R5 winding | motor |

## Power

Each rail is drawn as many separate flag symbols (one per tap point), not one
continuous wire — they still form a single real net each, because the
GND/rail symbols are flagged as Kicad power symbols (`(power global)`); see
`schlib.py`'s `Sym` docstring if adapting this pattern elsewhere. Confirmed
against Kicad's own netlist export, which merges them into one named net
each:

- **VSW**: D1.1, K1.12, K2.12 — the raw supply rail via the two relays' NC
  contacts and D1's anode. TB5/D4/C4/U5.1 sit on a separate, unnamed net
  (same potential, reached only through the literal-wire chain below, not
  through a VSW-flagged tap) - see Supply.
- **+5V**: C5.1, D2.1, D3.1, K1.A2, K2.A2, Q1.1, R7.1, U5.2, U5.4, U1.21,
  U2.16, U2.2, U2.3, U4.8, U3.14 — regulated 5V, from U5's OUT (pin 2) and
  FB (pin 4, tied to OUT - see Drive/Supply below)
- **+3V3**: R5.1, R6.1, TB2.1, U1.1, U1.2 — from the ESP32 board's own
  regulator (real part has two physical 3V3 pins, merged onto one net by
  Kicad's power-symbol matching even though only pin 1 is wired), not
  generated on this board; only fed out to the handset (via TB2/J1/J4) and
  the rocker pull-ups. TB2 is also the planned physical source for a
  future ToF sensor's +3V3/GND (second wire under each of its screws,
  not a separate net or terminal - see README 8.1)
- **GND**: C4.2, C5.2, C1.1, D4.2, PS1.2, Q5.3, Q3.3, Q4.3, Q2.1, R8.2, R9.2,
  R2.2, R10.2, TB5.2, TB2.2, U5.3, U5.5, U1.22, U1.23, U1.24, U1.44, U2.8,
  U4.5, U3.7

## Connectors

The board itself no longer carries a Mini-Fit Jr connector at all - see
"screw terminals" below. J3/J4 remain: both Molex Mini-Fit Jr, 4 circuit
dual row (README 1.5). Real part: Kicad's `Conn_02x02_Top_Bottom` -
row-major numbering (pins 1,2 = row 1; pins 3,4 = row 2), confirmed against
Molex's own 5557-series sales drawing (SD-5557-003).

- **J3** (in motor housing): the actual mating half for the motor housing
  cable. Wired directly to the LEG section's own motor leads and to PS1,
  not to a same-named-label match - see the note at the end of this
  document. Mates with a short pigtail off TB4/TB5 (see below), not with a
  second Mini-Fit drawn on this sheet.
- **J4** (in handset): the actual mating half for the handset cable, wired
  directly to SW3/SW4. Mates with a short pigtail off TB1/TB2.

## Screw terminals (board-side termination)

TB1, TB2, TB4, TB5 replace what used to be two board-side Mini-Fit Jr connectors
(J2, J1) - the board now only ever solders to a screw terminal (no crimp
tool needed for board assembly); a short crimped pigtail, off-board,
carries each circuit on from there to J3/J4's actual Mini-Fit pins. Real
part: Kicad's `Screw_Terminal_01x02`, 2-position, 2.54mm pitch.

- **TB4** (motor pair): 1=`MOT_A`, 2=`MOT_B` (also U4.1, U4.2 - IP+, both
  leads; K2.11 on pin 1). Circuit numbering here still matches what the
  former J2 used (README 1.6: motor pair = circuits 1/2). Which of
  MOT_A/MOT_B sits on pin 1 vs 2 is still provisional - MOT_A is defined
  by function (§1.6: whichever conductor raises the desk), not by a fixed
  pin, so if bring-up shows this backwards, relabel here rather than
  rewire.
- **TB5** (supply pair): 1=the unnamed VSW-potential net (see Power), 2=GND.
  Mirrored (pins face right, toward the SUPPLY chain) rather than left
  (toward TB4) - see `sch.py`.
- **TB1** (signal pair): 1=`HND_A` (also R3.2), 2=`HND_B` (also R4.2). No
  README-documented circuit numbering exists here (unlike TB4) - this
  assignment is for routing convenience only.
- **TB2** (power pair): 1=`+3V3`, 2=GND. Mirrored, same reasoning as TB5.

## Controller (U1 = ESP32)

Real part: Kicad's `ESP32-S3-DevKitC` (github.com/espressif/kicad-libraries,
CC-BY-SA 4.0 - vendored in `espressif.kicad_sym`, not part of the local Kicad
install). Bare devkit, no display - this hardware lives under the desk, not
somewhere a display is ever seen (README 5); a display, if ever added, would
be a separate on-desk peripheral. Chosen over `Arduino_Nano_ESP32` for its
bare GPIO-numbered pins, matching how this design already refers to every
signal (the Nano's exposed pins don't even overlap with the GPIOs this
design uses).

GPIO choice was picked for schematic-wiring simplicity, not final PCB
routing - expect this table to change once routing is considered. Only
constraints respected: avoid strapping (GPIO 0/3/45/46), avoid this specific
module's flash/PSRAM-reserved range (GPIO 22-37 - wider than the usual 26-32
since this is an N16R8/octal-PSRAM part), avoid native USB (GPIO 19/20), keep
ISENSE on an ADC1-capable pin (GPIO1-10; ADC2 and WiFi can coexist on the S3
unlike the classic ESP32, but ADC1 is still simpler).

| U1 pin | GPIO | Net | Goes to |
|---|---|---|---|
| 21 | (5V) | +5V | supply |
| 22 | (GND) | GND | ground (1 of 4 GND pins, only this one wired) |
| 1/2 | (3V3) | +3V3 | source for TB2/handset feed (2 physical pins, 1 wired, merged by Kicad's power matching) |
| 10 | GPIO17 | DIR_A | R8.1, U3.2 (gate A input) |
| 11 | GPIO18 | DIR_B | R9.1, U3.5 (gate B input) |
| 27 | GPIO21 | PWM | R10.1, U3.10 (gate C input) |
| 12 | GPIO8 | MODE | unconnected (spare) |
| 41 | GPIO1 | KICK | U2.1 (monostable A trigger input) |
| 40 | GPIO2 | ISENSE | R1.1, R2.2 (divider midpoint) |
| 18 | GPIO12 | - | unconnected (spare) - was SDA, moved off this pin, see below |
| 19 | GPIO13 | - | unconnected (spare) - was SCL, moved off this pin, see below |
| 35 | GPIO38 | SDA | TB3.1 (ToF prep, Phase 2 not started) - fully routed, see README 8.1 |
| 38 | GPIO41 | SCL | TB3.2 (ToF prep, Phase 2 not started) - fully routed, see README 8.1 |
| 15 | GPIO9 | SW_UP | R3.1, R5.2 |
| 16 | GPIO10 | SW_DN | R4.1, R6.2 |

DIR_A/PWM (GPIO17/21) aren't the classic-ESP32 assignment this design used to
use (GPIO21/27) - swapped so DIR_A, whose gate target is the topmost of the
three AND gates below, lands on the topmost of these three MCU pins, and PWM
(bottommost gate) lands on the bottommost; DIR_B (middle gate) was already in
between. The other ~30 pins on this real part (GPIO4-7, most of the JTAG/UART
pins, etc.) are unconnected - normal for a full-featured real MCU symbol
where a given design only uses a fraction of the breakout, not a sign of
anything missing. `CHIP_PU` (pin 3, the board's own EN) is also left
unconnected - it has an onboard pull-up on real devkits, no external drive
needed.

Rocker dividers: `HND_A` → R3 (4k7) → node also pulled to +3V3 through R5
(100k) → `SW_UP`. Same pattern for `HND_B`/R4/R6/`SW_DN`. Dry contacts, no
clamp diodes (29V can never reach these conductors).

## Watchdog + gating (U2 = 74HC123, U3 = 74HC08)

- U2 pin 1 (A, trigger) ← `KICK` (U1.41, GPIO1)
- U2 pin 2 (B) and pin 3 (Clr) both tied to +5V (never retriggers or clears
  from those inputs)
- U2 pins 14/15 (Cext/RCext) ↔ C1 (2u2) / R7 (100k) — sets the ~250ms pulse
  width
- U2 pin 13 (Q, watchdog output) → `WDOG` net → U3 pins 1, 4, 9 (the "A"
  input of each of the three AND gates)
- U2 pin 4 (~Q) — unconnected
- U2 pins 16/8 (VCC/GND) → +5V / GND

Each AND gate: `WDOG` AND `<signal>` → gated output to the corresponding FET.

| Gate | A (WDOG) | B (signal) | Y (out) | Pulldown | Drives |
|---|---|---|---|---|---|
| U3 unit 1 | pin 1 | pin 2 = DIR_A | pin 3 | R8 (10k) on pin 2 | Q3 gate |
| U3 unit 2 | pin 4 | pin 5 = DIR_B | pin 6 | R9 (10k) on pin 5 | Q4 gate |
| U3 unit 3 | pin 9 | pin 10 = PWM | pin 8 | R10 (10k) on pin 10 | R11 → Q1/Q2 base |

U3 pins 14/7 (VCC/GND, unit 5) → +5V / GND. Pulldowns hold each gated line
low (drive lines safe) before the MCU boots.

## Drive

- **Q1/Q2** (BC337/BC327, discrete push-pull gate driver - replaces a
  TC4427 driver IC, see README/APPENDIX for why): bases tied together ←
  U3 gate-3 output (pin 8) through R11 (1k); emitters tied together →
  **Q5.1** (gate). Q1 collector → +5V; Q2 collector → GND.
- **Q5** (IRLZ44N, main PWM FET): gate ← Q1/Q2 emitters; source → GND;
  drain (`MRET`) → K1.14, K2.14, D1.2.
- **D1** (SB560, freewheel): K → `MRET`; A → `VSW`.
- **Q3** (2N7000): gate ← U3 unit-1 output (pin 3); drain → K1's coil
  (`A1`/D2 node); source → GND.
- **Q4** (2N7000): gate ← U3 unit-2 output (pin 6); drain → K2's coil
  (`A1`/D3 node); source → GND.
- **K1** (relay, UP): coil A2 → +5V, coil A1 → Q3 drain + D2 cathode (D2
  anode → +5V, flyback) - A1/A2's roles swapped from a pre-rotation
  layout (`sch.py`'s own history); the schematic is correct, this doc
  wasn't. Contacts: 12 (NC) → `VSW`; 14 (NO) → `MRET`; 11 (COM) →
  `DRV_UP` net → U4 pin 3 (IP-).
- **K2** (relay, DOWN): same pattern - coil via Q4/D3; 12 (NC) → `VSW`; 14
  (NO) → `MRET`; 11 (COM) → TB4 pin 1 (`MOT_A`, pigtails on to the motor
  housing connector J3).
- **U4** (ACS712ELCTR-05B, current sensor): VCC (pin 8)/GND (pin 5) →
  +5V/GND. IP- (pin 3, both leads) ← K1.11 (`DRV_UP`). IP+ (pin 1, both
  leads) → TB4 pin 2 (`MOT_B`) — U4 sits in series in K1's leg only; K2's
  leg (`MOT_A`) bypasses it directly. Which of IP+/IP- faces which side
  is arbitrary (README 4.4 - either leg works, direction isn't used) and
  was picked for routing. VIOUT (pin 7) → R1.1. FILTER (pin 6) is
  unconnected - the datasheet ties it to GND through a cap for noise
  filtering; not fitted, open item.
- **R1/R2** (10k/20k): OUT → R1 → R2 → GND; the R1/R2 midpoint is `ISENSE`,
  fed to U1 pin 40 (GPIO2).

## Leg (unmodified motor housing internals)

- `MOT_A` → SW1.1 (top limit) ∥ D5.1 (bypass, "allows down") → common node
  (SW1.2, D5.2) → M1.1
- M1.2 → common node (SW2.1, D6.2) → SW2.1 (bottom limit) ∥ D6.2 (bypass,
  "allows up") → SW2.2/D6.1 → `MOT_B`

Note the diodes are reversed relative to each other pin-for-pin (D5: pin 1 on
the `MOT_A` side; D6: pin 1 on the `MOT_B` side) — that's the "allows
down"/"allows up" direction difference, not a mistake.

This section is physically inside the motor housing/leg and reached only via
J3 (which pigtails on to TB4/TB5 on the board) — it's the same hardware as
the stock desk, unmodified.

**Previously found here, since fixed:** `MOT_A`/`MOT_B` used to be global
labels placed only in this section, far from the board-side connector, which
meant they never actually merged with that connector's own pins in Kicad's
netlist (global labels merge by matching text anywhere on the sheet, and
those pins carried no such label). Fixed by adding `J3` — the actual mating
half, wired straight to this section's motor leads instead of relying on
label-matching. See `sch.py`.
