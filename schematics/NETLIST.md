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
| F1 | 2A slow-blow | |
| D1 | 33V bidir | TVS, input transient protection |
| C1 | 220u 50V | input bulk cap |
| U1 | LM2596HV 29V-5V | buck regulator; real part is base symbol LM2596T-12 (fixed-output LM2596T-5's own base), a pin-compatible non-HV placeholder, see TODO.md |
| C2 | 220u 10V | +5V output cap |
| J2 | to motor housing | 4-circuit: MOT_A, MOT_B, VSW, GND |
| J3 | to handset | 4-circuit: HND_A, HND_B, +3V3, GND |
| U2 | ESP32 + display | custom board, see README; real part is Espressif's ESP32-S3-DevKitC symbol (vendored, see Controller section) as a closer stand-in than anything in the local Kicad install |
| R11 | 4k7 | HND_A series resistor (rocker divider) |
| R13 | 100k | SW_UP pull-up to +3V3 |
| R14 | 4k7 | HND_B series resistor (rocker divider) |
| R15 | 100k | SW_DN pull-up to +3V3 |
| U3 | 74HC123 250ms | monostable (retriggerable watchdog timer); real part is 74LS123, `74HC123` is a same-pinout wrapper in Kicad's library |
| R3 | 100k | U3 timing resistor |
| C3 | 2u2 | U3 timing capacitor |
| U6 | 74HC08 | triple AND gate (3 of 4 gates used); real part is 74LS08 placeholder, see TODO.md |
| R1 | 10k | DIR_A gate pulldown (boot-safe) |
| R2 | 10k | DIR_B gate pulldown (boot-safe) |
| R6 | 10k | PWM gate pulldown (boot-safe) |
| Q4 | BC337 | gate driver for Q1, NPN half of a discrete push-pull (replaces a TC4427 IC) |
| Q5 | BC327 | gate driver for Q1, PNP half of the push-pull |
| R7 | 1k | Q4/Q5 base resistor |
| Q1 | IRLB8721 | main PWM FET, low side |
| D5 | SB560 | freewheel diode |
| K1 | energized = UP (raises desk) | relay, real part Relay_SPDT (EN50005 pinout) |
| K2 | energized = DOWN (lowers desk) | relay, same part as K1 |
| D2 | flyback | K1 coil flyback diode |
| D6 | flyback | K2 coil flyback diode |
| Q2 | 2N7002 | K1 coil driver |
| Q3 | 2N7002 | K2 coil driver |
| U5 | ACS724xLCTR-05AB | current sensor, in series with K1's leg; real part is base symbol ACS712xLCTR-05B, same "extends" pattern as 74HC123/BC337 |
| R4 | 10k | ISENSE divider, top |
| R5 | 20k | ISENSE divider, bottom |
| SW3 | top limit | limit switch, in the leg |
| SW4 | bottom limit | limit switch, in the leg |
| D3 | allows down | SW3 bypass diode |
| D4 | allows up | SW4 bypass diode |
| M1 | 2R5 winding | motor |

## Power

Each rail is drawn as many separate flag symbols (one per tap point), not one
continuous wire — they still form a single real net each, because the
GND/rail symbols are flagged as Kicad power symbols (`(power global)`); see
`schlib.py`'s `Sym` docstring if adapting this pattern elsewhere. Confirmed
against Kicad's own netlist export, which merges them into one named net
each:

- **VSW**: C1.1, D1.1, D5.1, F1.2, J2.3, K1.12, K2.12, U1.1 — the raw supply
  rail, straight off the fuse, before the buck regulator
- **+5V**: C2.1, D2.1, D6.1, K1.A1, K2.A1, Q4.1, R3.1, U1.2, U1.4, U2.21,
  U3.16, U3.2, U3.3, U5.8, U6.14 — regulated 5V, from U1's OUT (pin 2) and
  FB (pin 4, tied to OUT - see Drive/Supply below)
- **+3V3**: J3.3, R13.1, R15.1, U2.1, U2.2 — from the ESP32 board's own
  regulator (real part has two physical 3V3 pins, merged onto one net by
  Kicad's power-symbol matching even though only pin 1 is wired), not
  generated on this board; only fed out to the handset (J3) and the
  rocker pull-ups
- **GND**: C1.2, C2.2, C3.2, D1.2, J2.4, J3.4, PS1.2, Q1.3, Q2.3, Q3.3, Q5.1,
  R1.2, R2.2, R5.1, R6.2, U1.3, U1.5, U2.22, U3.8, U5.5, U6.7

## Connectors

Both are Molex Mini-Fit Jr, 4 circuit dual row (README 1.5). Real part:
Kicad's `Conn_02x02_Top_Bottom` - row-major numbering (pins 1,2 = row 1;
pins 3,4 = row 2), confirmed against Molex's own 5557-series sales drawing
(SD-5557-003).

- **J2** (to motor housing): 1=`MOT_A`, 2=`MOT_B` (also U5.1, U5.2 - IP+,
  both leads), 3=`VSW`, 4=GND (also K2.11 on pin 1). This matches README
  1.6's circuit numbering (motor pair = circuits 1/2, supply pair =
  circuits 3/4) - it didn't before this pass; the pins were previously
  swapped relative to §1.6. Which of MOT_A/MOT_B sits on pin 1 vs 2 is
  still provisional - MOT_A is defined by function (§1.6: whichever
  conductor raises the desk), not by a fixed pin, so if bring-up shows
  this backwards, relabel here rather than rewire. **Not actually merged
  into the same Kicad net as the `MOT_A`/`MOT_B` glabels in the LEG
  section below** - see the note at the end of this document.
- **J3** (to handset): 1=`HND_A` (also R11.2), 2=`HND_B` (also R14.2),
  3=`+3V3`, 4=GND. No README-documented circuit numbering exists for J3
  (unlike J2) - this assignment is for routing convenience only.

## Controller (U2 = ESP32 + display)

Real part: Kicad's `ESP32-S3-DevKitC` (github.com/espressif/kicad-libraries,
CC-BY-SA 4.0 - vendored in `espressif.kicad_sym`, not part of the local Kicad
install). U2 is a generic "ESP32 devkit + display" (README 6, a "CYD"), not
literally this board, but it's the closest real symbol available: bare
GPIO-numbered pins, matching how this design already refers to every signal,
unlike `Arduino_Nano_ESP32` (whose exposed pins don't even overlap with the
GPIOs this design uses).

GPIO choice was picked for schematic-wiring simplicity, not final PCB
routing - expect this table to change once routing is considered. Only
constraints respected: avoid strapping (GPIO 0/3/45/46), avoid this specific
module's flash/PSRAM-reserved range (GPIO 22-37 - wider than the usual 26-32
since this is an N16R8/octal-PSRAM part), avoid native USB (GPIO 19/20), keep
ISENSE on an ADC1-capable pin (GPIO1-10; ADC2 and WiFi can coexist on the S3
unlike the classic ESP32, but ADC1 is still simpler).

| U2 pin | GPIO | Net | Goes to |
|---|---|---|---|
| 21 | (5V) | +5V | supply |
| 22 | (GND) | GND | ground (1 of 4 GND pins, only this one wired) |
| 1/2 | (3V3) | +3V3 | source for J3 handset feed (2 physical pins, 1 wired, merged by Kicad's power matching) |
| 10 | GPIO17 | DIR_A | R1.1, U6.2 (gate A input) |
| 11 | GPIO18 | DIR_B | R2.1, U6.5 (gate B input) |
| 27 | GPIO21 | PWM | R6.1, U6.10 (gate C input) |
| 12 | GPIO8 | MODE | unconnected (spare) |
| 41 | GPIO1 | KICK | U3.1 (monostable A trigger input) |
| 40 | GPIO2 | ISENSE | R4.1, R5.2 (divider midpoint) |
| 18 | GPIO12 | SDA | unconnected in this design (spare) |
| 19 | GPIO13 | SCL | unconnected in this design (spare) |
| 15 | GPIO9 | SW_UP | R11.1, R13.2 |
| 16 | GPIO10 | SW_DN | R14.1, R15.2 |

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

Rocker dividers: `HND_A` → R11 (4k7) → node also pulled to +3V3 through R13
(100k) → `SW_UP`. Same pattern for `HND_B`/R14/R15/`SW_DN`. Dry contacts, no
clamp diodes (29V can never reach these conductors).

## Watchdog + gating (U3 = 74HC123, U6 = 74HC08)

- U3 pin 1 (A, trigger) ← `KICK` (U2.41, GPIO1)
- U3 pin 2 (B) and pin 3 (Clr) both tied to +5V (never retriggers or clears
  from those inputs)
- U3 pins 14/15 (Cext/RCext) ↔ C3 (2u2) / R3 (100k) — sets the ~250ms pulse
  width
- U3 pin 13 (Q, watchdog output) → `WDOG` net → U6 pins 1, 4, 9 (the "A"
  input of each of the three AND gates)
- U3 pin 4 (~Q) — unconnected
- U3 pins 16/8 (VCC/GND) → +5V / GND

Each AND gate: `WDOG` AND `<signal>` → gated output to the corresponding FET.

| Gate | A (WDOG) | B (signal) | Y (out) | Pulldown | Drives |
|---|---|---|---|---|---|
| U6 unit 1 | pin 1 | pin 2 = DIR_A | pin 3 | R1 (10k) on pin 2 | Q2 gate |
| U6 unit 2 | pin 4 | pin 5 = DIR_B | pin 6 | R2 (10k) on pin 5 | Q3 gate |
| U6 unit 3 | pin 9 | pin 10 = PWM | pin 8 | R6 (10k) on pin 10 | U7.3 (IN) |

U6 pins 14/7 (VCC/GND, unit 5) → +5V / GND. Pulldowns hold each gated line
low (drive lines safe) before the MCU boots.

## Drive

- **Q4/Q5** (BC337/BC327, discrete push-pull gate driver - replaces a
  TC4427 driver IC, see README/APPENDIX for why): bases tied together ←
  U6 gate-3 output (pin 8) through R7 (1k); emitters tied together →
  **Q1.1** (gate). Q4 collector → +5V; Q5 collector → GND.
- **Q1** (IRLB8721, main PWM FET): gate ← Q4/Q5 emitters; source → GND;
  drain (`MRET`) → K1.14, K2.14, D5.2.
- **D5** (SB560, freewheel): K → `MRET`; A → `VSW`.
- **Q2** (2N7002): gate ← U6 unit-1 output (pin 3); drain → K1's coil
  (`A2`/D2 node); source → GND.
- **Q3** (2N7002): gate ← U6 unit-2 output (pin 6); drain → K2's coil
  (`A2`/D6 node); source → GND.
- **K1** (relay, UP): coil A1 → +5V, coil A2 → Q2 drain + D2 cathode (D2
  anode → +5V, flyback). Contacts: 12 (NC) → `VSW`; 14 (NO) → `MRET`; 11
  (COM) → `DRV_UP` net → U5 pin 3 (IP-).
- **K2** (relay, DOWN): same pattern - coil via Q3/D6; 12 (NC) → `VSW`; 14
  (NO) → `MRET`; 11 (COM) → J2 pin 1 (`MOT_A`, straight to the motor
  housing connector).
- **U5** (ACS724xLCTR-05AB, current sensor): VCC (pin 8)/GND (pin 5) →
  +5V/GND. IP- (pin 3, both leads) ← K1.11 (`DRV_UP`). IP+ (pin 1, both
  leads) → J2 pin 2 (`MOT_B`) — U5 sits in series in K1's leg only; K2's
  leg (`MOT_A`) bypasses it directly. Which of IP+/IP- faces which side
  is arbitrary (README 4.4 - either leg works, direction isn't used) and
  was picked for routing. VIOUT (pin 7) → R4.1. FILTER (pin 6) is
  unconnected - the datasheet ties it to GND through a cap for noise
  filtering; not fitted, open item.
- **R4/R5** (10k/20k): OUT → R4 → R5 → GND; the R4/R5 midpoint is `ISENSE`,
  fed to U2 pin 40 (GPIO2).

## Leg (unmodified motor housing internals)

- `MOT_A` → SW3.1 (top limit) ∥ D3.1 (bypass, "allows down") → common node
  (SW3.2, D3.2) → M1.1
- M1.2 → common node (SW4.1, D4.2) → SW4.1 (bottom limit) ∥ D4.2 (bypass,
  "allows up") → SW4.2/D4.1 → `MOT_B`

Note the diodes are reversed relative to each other pin-for-pin (D3: pin 1 on
the `MOT_A` side; D4: pin 1 on the `MOT_B` side) — that's the "allows
down"/"allows up" direction difference, not a mistake.

This section is physically inside the motor housing/leg and reached only via
J2 — it's the same hardware as the stock desk, unmodified.

**Previously found here, since fixed:** `MOT_A`/`MOT_B` used to be global
labels placed only in this section, far from J2, which meant they never
actually merged with J2's own pins 1/2 in Kicad's netlist (global labels
merge by matching text anywhere on the sheet, and J2.1/J2.2 carried no such
label). Fixed by adding `J1` — the actual mating half of J2, wired straight
to this section's motor leads instead of relying on label-matching. See
`sch.py`.
