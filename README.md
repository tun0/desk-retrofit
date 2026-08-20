# Jysk Slangerup standing desk — smart drive retrofit

Reverse engineering notes, design decisions and firmware for replacing the
control of a **Jysk Slangerup** electric height-adjustable desk.

The original complaint: the up/down buttons switch the motor on at full
voltage, so the desk jolts into motion. The goal is soft start/stop under
programmatic control, with height presets as a later phase.

This document is the project's memory. It records not just the final design
but the measurements it rests on, the alternatives considered, and — deliberately —
the wrong turns, because several conclusions here are only correct in light of
an earlier mistake.

---

## 1. The desk as found

### 1.1 Documented facts

From the JYSK manual (rev. 1, 22.06.2022; item numbers 3601130, 3601131,
75668001, 75672001, C123681):

| Property | Value |
|---|---|
| Height range | 68–118 cm |
| Max load | 40 kg |
| Speed | ~25 mm/s, load dependent |
| Duty cycle | 10% at 50% max load, or 2 min continuous |
| Operation | Micro switches |
| Anti-collision | **Not listed** (JYSK's SVANEKE model does advertise it) |
| Manufacturer of record | 2-connect ApS, Ikast, Denmark |

Essentially nothing else is publicly documented. 2-connect is a furniture
trading and sourcing company rather than an electronics designer, so they are
the CE-responsible party and the parts are unbranded OEM. There is no control
box model number, no wiring diagram, no service manual, no aftermarket
replacement. The Machinery Directive technical file is only available to
national market-surveillance authorities, not the public.

**Conclusion: everything below was measured, not looked up.**

### 1.2 Physical layout

- **Single motor**, permanently attached to one leg, driving the second leg
  through a shaft. Both columns are mechanically locked together, so one
  position measurement is authoritative for the whole desk.
- **No separate control box.** The electronics — such as they are — live in
  the motor housing. Only two cables exist: PSU → motor housing, and a
  4-conductor cable between the motor housing and the handset.
- The handset enclosure contains two rocker microswitches and nothing else.

### 1.3 Power supply

Label reads:

```
Input:  AC 100-240V  50/60Hz  1.5A
Output: DC 29.0V  1.8A  52.2W
```

The 1.8 A rating turns out to be one of the most important numbers in the
project — see §2.4.

### 1.4 The 4-conductor cable

Terminals on the motor housing, left to right: **red, yellow, white, grey**.

| Conductor | Connects to |
|---|---|
| red | UP rocker only |
| yellow | both rockers |
| white | both rockers |
| grey | DOWN rocker only |

Two shared conductors, one unique conductor per rocker, three terminals per
rocker. That topology is the signature of **two SPDT changeover switches
sharing a common pair** — the minimal H-bridge you can build from two rockers.

### 1.5 The connector

**Molex Mini-Fit Jr., 4.20 mm pitch, 4 circuits, dual row (2x2).**

Identified by caliper, recorded here because the pitch is genuinely awkward to
measure on a moulded housing with recessed cavities, and a first attempt at
buying an extension cable got the wrong part.

Two measurements, and how they combine:

| Measurement | Value |
|---|---|
| Terminal centre-to-centre (pitch), approximate | ~4 mm |
| Outer edge to outer edge across two adjacent cavities | 7.7 mm |

The second is the reliable one — flat outside faces, a longer span, so a
smaller relative error. It equals **one pitch plus one cavity width**:

```
7.7 mm  =  4.2 (pitch)  +  3.5 (cavity)      → Mini-Fit Jr.   ✓
5.4 mm  =  3.0 (pitch)  +  2.4 (cavity)      → Micro-Fit 3.0  ✗
```

Micro-Fit was the initial guess — it is the usual choice for this class of
desk — but it cannot produce a 7.7 mm span. For reference, a Micro-Fit 3.0
dual-row 4-circuit part measures 9.65 mm along the row axis against 6.65 mm
for the 2-circuit version; the 3.00 mm difference is exactly one pitch.

Family identification by pitch, for future reference:

| Pitch | Family | Current/circuit |
|---|---|---|
| 2.00 mm | Milli-Grid | low |
| 2.50 mm | Nano-Fit | ~6.5 A |
| 3.00 mm | Micro-Fit 3.0 | 5.0 A |
| 3.50 mm | Ultra-Fit | ~9 A |
| **4.20 mm** | **Mini-Fit Jr.** | **9.0 A** |

9 A per circuit is wildly over-specified for 1.8 A — normal for a furniture
OEM buying whatever was cheap and available.

Quick sanity check without calipers: Mini-Fit Jr. *is* the ATX family. The
4-pin 12V CPU plug on any PC power supply is the same connector.

### 1.6 Pinout and polarity

Measured on the **5557 receptacle** — the half with the *movable* thumb latch,
holding female sockets. The 5559 plug has the fixed catch that latch grabs.

```
Receptacle (5557, female sockets, movable latch)
viewed INTO the mating face, latch uppermost:

        ─── latch ───
      ┌───────────────┐
      │  [ 1 ] [ 2 ]  │   motor pair
      │  [ 3 ] [ 4 ]  │   supply pair
      └───────────────┘

  1 = motor          3 = supply +
  2 = motor          4 = supply -
```

The plug, viewed into *its* mating face, is the left-right mirror of this.
Never carry a "left and right" description across from one half to the other.

> **This numbering is a project-local convention defined by the diagram above.**
> The housings carry no legible moulded numbers, and Molex's own circuit
> numbering for Mini-Fit Jr. may differ. Inside this project the convention is
> consistent; do **not** assume it matches a Molex drawing or a pre-made cable
> assembly.

Because the numbering lives only in this document, **mark the connector
physically**: a dab of paint or nail varnish on the MOT_A cavity. Then the
mark is the definition and no orientation reasoning is ever needed again. The
housings are polarised, so the box itself cannot be mated the wrong way round.

**Polarity, measured:**

| Applied | Result |
|---|---|
| 3→2 and 4→1 (circuit 2 positive) | **UP** |
| 3→1 and 4→2 (circuit 1 positive) | **DOWN** |

**Naming convention used throughout this project:**

> **MOT_A** is the conductor that must be **positive to raise** the desk =
> circuit 2.
> **MOT_B** = circuit 1.

Defining it this way makes the schematic correct by construction, so the only
project-specific fact to remember is which circuit MOT_A is.

**On wire colours — not needed.** The colours in §1.4 did one job: deriving
the rocker topology. Everything downstream works in circuit numbers, because
the box mates with connectors rather than cutting into the cable, so a
conductor's colour mid-run never comes up. The connector end also carries a
moulded protector sleeve, so the colours are not visible there anyway.

For the record, the mapping is *predicted* but unconfirmed: red is the UP
rocker's common and the rockers rest on NC → V+ (§2.4), so red goes negative
while raising, making **red = circuit 1 (MOT_B)** and **grey = circuit 2
(MOT_A)**. If it is ever wanted, it can be had without opening the handset:
the colours are visible at the motor housing terminals, so continuity from a
housing terminal to a connector pin gives the mapping with the cable still
installed.

**Re-identification recipe.** The numbering is a convenience, not a
dependency — every fact above is re-measurable in about five minutes with
nothing but a multimeter:

| Step | Measurement | Tells you |
|---|---|---|
| 1 | ~2.5 Ω across a pair | that pair is the motor winding |
| 2 | ~29 V across the other pair (powered) | supply pair; DC volts gives + and − |
| 3 | Park at the **bottom** stop, diode mode across the motor pair | the conductor reading ~0.6 V with the **red** probe on it is **MOT_A** (positive raises) |

Step 3 works because at the bottom stop the limit switch is open and its
bypass diode passes only the escape direction, which is up.

---

## 2. Measurements and what each proved

Every measurement below was taken with mains disconnected unless noted.

### 2.1 Which pair is which

With the handset assembly disconnected:

- ~**30 V** across one pair → these are the supply rails, routed up to the handset.
- ~**2.5 Ω** across the other pair → this is the motor winding, routed up and back.

A relay coil at 29 V would read hundreds of ohms to low kilohms. 2.5 Ω can
only be a winding. **This proved the rockers carry full motor current and that
no controller exists anywhere in the desk.**

### 2.2 Isolation

- Supply negative to either winding terminal: **< 1 V**, and **open** on the
  resistance range.
- All conductor combinations open except the 2.5 Ω winding pair.

This ruled out either winding end being permanently tied to a rail — which
would have shorted the supply on the first press of a naive H-bridge retrofit.

### 2.3 End stops

Diode mode across the winding pair, measured at the motor-side terminals:

| Position | Reading |
|---|---|
| Mid-travel | near zero both directions (the winding) |
| Bottom stop | **0.6 V one way, OL the other** |
| Top stop | same behaviour, mirrored |

This identifies **diode-bypassed limit switches** — a normally-closed
microswitch at each end of travel with a diode across it, in **series** with
the winding. At a limit the switch opens: one polarity is blocked entirely,
the other passes through the bypass diode so the desk can drive away from the
stop. Two switches, two diodes, still only two conductors down the leg.

Consequences:
- The desk cannot be driven past either extreme, in hardware, regardless of
  firmware. This is inherited for free by any retrofit.
- Homing is clean: drive down until current collapses to zero. That is the
  switch opening at a repeatable mechanical position.

### 2.4 Rest state and current

With both rockers in neutral, **three of the four contacts read shorted**, to
the **positive** rail. Both rockers sit on their NC contacts, tying both
winding ends to V+. That is dynamic braking, and it explains why the desk
stops as abruptly as it starts.

Locked-rotor current would be 29 V ÷ 2.5 Ω ≈ **11.6 A** — but the supply is
rated 1.8 A. The PSU current-limits long before the winding sees anything like
that. Practical consequences:

- The supply is already acting as the current limiter and, incidentally, as
  the collision protection. Jam the desk and it drops into limit and stalls
  rather than drawing 12 A.
- **Do not casually fit a bigger PSU.** That current limit is load-bearing
  safety on a frame with no other protection, and the motor's thermal rating
  was chosen around it.
- A sanity check supports this: lifting ~60 kg at 25 mm/s is ~15 W mechanical,
  which through a spindle drive lands near 40–50 W electrical. The desk runs
  close to the supply limit under load, which is exactly what the manual's
  "speed depends on load" is describing.

### 2.5 The as-found circuit

```
        V+ ──┬──────────────┬──────────
             │              │
           [SW1]          [SW2]          two SPDT rockers
        UP   │ COM      COM │  DOWN      NC → V+  (rest = brake)
             │              │            NO → V−
             │              │
             ├─[LIM_top ∥ D_down]─(M)─[LIM_bot ∥ D_up]─┤
             │                                          │
        V− ──┴──────────────┴──────────
```

Not kept as a separate schematic file — this circuit is fully captured by
the measurements above and the diagram, and the stock wiring is unmodified
in the chosen design (§4).

---

## 3. Design evolution

Four designs were considered in sequence:

| | Design | Outcome |
|---|---|---|
| 3.1 | ESP32 + integrated H-bridge IC | rejected on voltage headroom |
| 3.2 | Relay direction + low-side FET PWM | adopted as the drive topology |
| 3.3 | In-line interceptor with 3-pole transfer relay and automatic fallback | good design, dropped as over-complex |
| 3.4 | **Simple in-line drive** | **chosen** |

> Why each of the first three lost, and what would be worth keeping if any
> were revived, is in **`APPENDIX.md` §5**. Several were reasonable at the time
> and became obsolete only when a later measurement changed the picture.

### 3.4 Simple in-line drive — **CHOSEN**

Same in-line position, no transfer relay, no automatic fallback. The board
owns the winding permanently. Reverting is physical:

```
motor — box — handset      becomes      motor — handset
```

39 components instead of 51. Dropping the transfer also deleted the clamp
diodes: with no transfer relay, 29 V can never appear on the handset
conductors, so there is no transition window to protect against.

---

## 4. The chosen design

Schematic: `desk.kicad_sch` / `.pdf`.

### 4.1 Topology

```
PSU 29V ──[F1]──┬── VSW rail
                │
                ├── buck ── +5V ── ESP32
                │
          [K1]──┴──[K2]        two SPDT relays, NC→VSW, NO→MRET
            │       │
            └─ winding ─┘      via limit switches in the leg
                │
              MRET ──[Q1]── GND    low-side PWM
                │
              [D5] freewheel to VSW
```

### 4.2 Relay truth table

`MOT_A` = circuit 2, positive to raise (§1.6). `MOT_B` = circuit 1.

| K1 | K2 | Result |
|---|---|---|
| off | off | both winding ends on VSW → **brake** (matches OEM rest state, and is the boot state) |
| **on** | off | MOT_B to return, MOT_A stays positive → **UP** |
| off | **on** | MOT_A to return, MOT_B stays positive → **DOWN** |
| on | on | both ends on MRET → coast if Q1 off, brake to ground if on |

No combination shorts the supply.

The signal chain therefore runs `DIR_A → U8 → Q2 → K1 = up` and
`DIR_B → U9 → Q3 → K2 = down`, which is what `relay_up:` and `relay_down:` in
`desk.yaml` are wired to. The current sensor sits in the K1 (MOT_B) leg; either
leg works, since it only needs to be inside the freewheel loop.

### 4.3 The handset

Permanently removed from the motor circuit. The board feeds it **3.3 V** and
reads the rockers as dry contacts — high at rest through the OEM NC contact,
low when pressed. Same cable, same connectors, different job. The tactile
up/down survives alongside the screen.

### 4.4 Current sensing

An **ACS724-5AB** sits in the motor leg, *not* in the FET return. With low-side
chopping the FET only carries current during the on-time; freewheel current
bypasses it entirely, so a low-side shunt would read a chopped fraction and
need synchronous sampling. In the motor leg the sensor is inside the freewheel
loop and reads true motor current continuously.

Its output is centred at 2.5 V and reaches ~3.7 V at 3 A, over the ADC limit,
so R4/R5 divide it down. **ISENSE must be on ADC1** — ADC2 is unusable while
WiFi is active.

### 4.5 Failsafe layer

- **Boot state.** R1/R2/R6 hold all three drive lines at "off" before firmware
  runs. These *must* sit on non-strapping GPIOs — on the classic ESP32 avoid
  GPIO0, 2, 12 and 15, since a pull resistor there fights the bootloader and
  GPIO12 pulled high selects the wrong flash voltage. The S3's strapping set
  differs; the principle holds.
- **Watchdog.** A 74HC123 retriggerable monostable (~250 ms) gates all three
  drive lines through a 74HC08. The ESP32 must keep kicking it. This sits
  **downstream of the MCU** deliberately: LEDC PWM keeps running in hardware
  after a firmware hang, so stopping PWM in software is not a safety measure.
- **Sequencing.** Relays change state only with Q1 off and current decayed
  (~50 ms). Switching contacts under a couple of amps of inductive DC is how
  relays weld, and a welded direction relay on a desk is a genuinely bad
  failure. On a watchdog trip this holds automatically: Q1 turns off in
  microseconds while relays take milliseconds to release.
- **Coast is safe.** Loss of drive leaves the desk where it is, because the
  spindle is self-locking. This is why the stock desk isn't dangerous despite
  having no electronics at all.
- **Duty cycle.** Enforce the manual's 10% / 2-minute limit in firmware.
  Thermal damage is the boring failure mode.
- **Travel timeout.** Full range is 500 mm at 25 mm/s, so anything over ~25 s
  of continuous drive is a fault.

---

## 5. Corrections made along the way

Recorded because several later conclusions only make sense in light of these.

1. **"No anti-collision implies no current sensing."** Too quick. If the desk
   had used stall detection at the end stops, it would have needed current
   sensing after all. Resolved by finding passive diode-bypassed limit
   switches — but the inference was unsound until then.
2. **Predicted the wrong diode-test result.** Expected "winding one way, diode
   the other". Wrong: the switch and its bypass sit in *series* with the
   winding, so at a limit one polarity is blocked entirely. The measured
   0.6 V / OL is what the series arrangement predicts.
3. **Recommended BTS7960 / VNH5019 on current headroom alone.** Both are out
   of voltage spec at 29 V (BTS7960: 5.5–27.5 V; VNH5019: 5.5–24 V). They
   survive 40 V+ as absolute maximum, but "probably fine" is not what should
   be holding up a desk.
4. **"Size the bridge for 12 A stall."** Wrong — the PSU current-limits at
   1.8 A, so the winding never sees locked-rotor current. This also reframed
   the supply as the existing collision protection.
5. **"Losing brake removes protection."** Overstated, and inconsistent with
   the self-locking spindle noted elsewhere. The brake does stop-precision
   work, not safety work.
6. **Wired NC to V− in the first `desk_original` schematic.** The measurement
   (three contacts shorted, to the positive rail) says NC → V+. Caught only
   when the netlist was rendered as a connectivity graph; the written note and
   the drawing had disagreed silently.
7. **Ran literal power rails across the schematic sheet.** Intended to remove
   "islands"; produced a picket fence of metre-long ground verticals instead.
   Local GND and rail symbols are the conventional idiom precisely because
   they avoid this. The real problem was that *signals* were labelled rather
   than wired.
8. **Planned an "ESP32 devkit + display" (CYD).** This board lives under the
   desk, not somewhere a display is ever seen, so U2 is a bare
   ESP32-S3-DevKitC instead. A display, if ever wanted, would be a separate
   peripheral mounted on the desk itself, not part of this board.
9. **Specified Q1 as IRLB8721.** Caught by an external review, not by this
   project's own process — the schematic still had it after the part was
   supposedly already swapped. IRLB8721's 30 V VDSS doesn't clear the 29–30 V
   rail once flyback clamping is accounted for; fixed to IRLZ44N (55 V). See
   §6.2.
10. **Assumed hand-wired perfboard was the assembly plan.** Reasoning at the
    time: this design is all through-hole specifically because there's no
    reflow equipment, and a fab-house PCB order felt like overkill for a
    one-off — so point-to-point perfboard wiring, guided by a generated
    wiring table, looked like the natural fit. Reversed once that wiring
    table turned out to need far more jumpers than expected, concentrated
    around locally dense ICs rather than anything structural — a strong
    signal that hand-wiring reliability, not layout, was the actual risk.
    A real 2-layer board (still hand-soldered, still through-hole — see
    §6.5) routes those same nets with zero jumpers once an autorouter can
    place traces on both layers, so it was worth doing even without a
    fab-house order: milled at home from a standard 70×100mm pre-cut
    copper-clad blank instead of ordered or hand-wired. See
    `schematics/desk.kicad_pcb` and its commit history for the design
    itself.

---

## 6. Bill of materials

Rough EUR incl. BTW, Netherlands. Prices are budgeting figures, not quotes.

| Item | Note | Cost |
|---|---|---|
| ESP32-S3-DevKitC | bare devkit, no display — see §5 | €5–15 |
| 2x SRD-05VDC-SL-C relay | bare relay, not a driver-included module — this design drives the coil directly, see NETLIST.md Drive section | €3–5 |
| 2x 2N7000 MOSFET | relay coil drivers (Q2/Q3), TO-92 — through-hole | €1–2 |
| IRLZ44N MOSFET | logic-level, 55V — see §6.2 | €1–2 |
| BC337 + BC327 | discrete gate driver push-pull — see §6.2 | €1–2 |
| 74HC123 + 74HC08 | watchdog and gating | €1–3 |
| SB560 Schottky | freewheel | <€1 |
| 2x 1N4148 | relay coil flyback diodes (D2/D6), DO-35 | <€1 |
| ACS724xLCTR-05AB (bare) + SOIC-8→DIP-8 adapter | bidirectional, 5A — see §4.4/§6.5; the Pololu carrier this used to be is dropped, its 2 caps (C4/C5) now on the main board instead; or 10 mΩ shunt + INA240, similar cost | €4–8 |
| LM2596HV buck | **must** be rated >40 V in | €4–8 |
| TVS 33 V bidirectional | D1 — no fuse fitted, see §6.1 | <€1 |
| Passives | resistors, caps | €4–8 |
| 4x 2-position screw terminal | 2.54mm pitch, board-side termination (TB1-TB4) — see §6.4 | €2–4 |
| Mini-Fit Jr. housings + terminals | 2 mating pairs, each now on a short pigtail off the board rather than a board-mount connector — see §6.4 | €3–6 |
| PCB blank, 70×100mm pre-cut copper-clad (2-layer) | milled, not fab-house ordered — see §6.5; SHOPPING_LIST.md flags this as still needing a specific supplier | €5–10 |
| **Total** | | **€25–100** |

Phase 2 adds ~€15–25 for a VL53L1X carrier and bracket. Sourcing detail
below (§6.6).

### 6.1 Voltage, not current, is the constraint

The rail is 29 V nominal, 30 V unloaded. Anything in the motor path or the
buck input needs headroom above that. Common traps:

- BTS7960 / IBT-2: spec'd 5.5–27.5 V. Out of spec.
- VNH5019: 5.5–24 V. Out of spec.
- MP1584 / Mini-360 buck modules: top out ~28 V. Marginal at best.

No fuse is fitted (there was one in early drafts, `F1`). The wall supply
already current-limits at 1.8 A — that limit is this design's only collision
protection, already relied on elsewhere (§4.4, `CLAUDE.md`'s own hard
invariants) — so a fuse adds little on top of it while being one more
embedded part to replace if it ever blows. The OEM desk never had one
either. D1 (33 V bidirectional TVS) stays.

### 6.2 Q1: voltage rating first, then the gate driver

**Q1 is IRLZ44N (55 V), not IRLB8721 (30 V).** The IRLB8721 is a common
default for "logic-level MOSFET," but its 30 V VDSS doesn't clear this
29 V nominal / 30 V unloaded rail — at PWM turn-off the freewheel diode
clamps the drain to VSW plus a diode drop, putting it at or over absolute
maximum every cycle. Substitution criterion for any replacement: check
**Qg and VDSS**, not Vgs(th) — plenty of parts marketed as "logic-level"
still top out at 30 V.

The gate driver still isn't optional: at 3.3 V Vgs a logic-level MOSFET is
only partially enhanced, and at 20 kHz that's how you cook a part that
would otherwise dissipate under 0.1 W. This design drives Q1 from a
discrete BC337/BC327 push-pull (not an IC — see `schematics/gen/symbols.py`),
fed 5 V through the AND gate output. Avoid the ubiquitous IRF520 "MOSFET
trigger" modules — that FET isn't logic-level at all.

### 6.3 K1/K2 are bare relays, not a driver-included module

**This design drives the coil directly** (Q2/Q3 discrete transistor
switches, D2/D6 flyback diodes — see NETLIST.md's Drive section), not
through a prebuilt "2-channel relay module" board. Those Arduino-kit
modules already include their own opto-isolated input, driver transistor
and flyback diode, which would make Q2/Q3/D2/D6 redundant rather than
complementary if one were used here — don't substitute one in without
also removing this board's own driver circuit. What to check when buying
the bare relay itself:

- **Coil voltage** — must be 5 V; this design's coil drive assumes it, and
  a 12 V coil would draw roughly half the current for the same drive
  voltage, undersaturating the relay.
- **Contact rating** — typically 10 A 250 VAC / 10 A 30 VDC. Your 29 V is right
  at that DC limit; acceptable only because contacts are cold-switched
  (§Sequencing/hard invariants — relays only change state with the FET
  off and current decayed).
- **Pinout** — EN50005/"Form C" (the real Kicad symbol this design uses,
  `Relay_SPDT`) is the common footprint for this class of relay; verify
  before assuming a drop-in substitute matches pin-for-pin.

### 6.4 Connector parts (Mini-Fit Jr., 4 circuit dual row)

| Part | Molex no. | Legacy |
|---|---|---|
| Receptacle housing (holds female terminals) | `39-01-2040` | 5557-04R |
| Plug housing (holds male terminals) | 5559 series, 4-circuit | 5559-04P |
| Female crimp terminal | 5556 | |
| Male crimp terminal | 5558 | |

**Wire-to-wire pairs a 5557 receptacle with a 5559 plug.** Datasheets for the
5557 list 5566 and 5569 as mating housings — those are *PCB headers*, not the
wire-to-wire half. That is the most likely explanation for the first wrong
order, alongside Molex's naming: a "receptacle housing" holds female terminals
while a "plug housing" holds male pins, and the plug is the part that inserts
into the receptacle. Order by the terminals, not by the shape you are looking
at, and check the datasheet drawing.

The retrofit box needs a **5559 plug on one end and a 5557 receptacle on the
other**, so it drops into the existing cable run in only one orientation.

Make up a short 5557-to-5559 **coupler** at the same time and tape it inside
the leg. That is the one-minute revert, and it is worth doing while the parts
and crimp tool are already on the bench rather than at an awkward moment.

Because this is the ATX family, a PC 4-pin 12V CPU extension is mechanically
correct and costs a few euros. Two cautions: verify the pinout is
straight-through 1:1 rather than crossed, and PC cables use stiff 18 AWG that
may not sit well in a desk-sized strain relief. Crimping your own in 20 or
22 AWG gives a tidier result; 2 m at 1.8 A is a couple of hundred millivolts
round trip either way.

Build any extension by **matching wire colours end to end** rather than
trusting circuit numbering. One reversed pair swaps the rails.

**The board itself doesn't carry a Mini-Fit connector at all.** Each side
(motor housing, handset) terminates on the board in a 2-position screw
terminal instead (TB1-TB4 — 2.54mm pitch, solders straight onto perfboard,
no crimp tool needed for board assembly). A short pigtail, crimped
separately on the bench, carries each pair from its screw terminal to the
actual Mini-Fit half (still needed, still built exactly as described
above) that mates with the cable. One extra connection point per circuit
versus terminating the Mini-Fit directly at the board edge, traded for
never needing a crimp tool during board assembly or rework.

### 6.5 This design is deliberately all through-hole

A hand-soldered, self-milled 2-layer PCB (`schematics/desk.kicad_pcb`,
sized to a standard 70×100mm pre-cut blank), not a fab-house order and not
raw perfboard either — but the reason for through-hole-only still holds
regardless of which of those three it ends up being: no reflow equipment.
Every substitution should preserve that, not just match electrically.
Substitution criterion is the **package**, not just the part:

| Part | Through-hole option |
|---|---|
| 74HC123 | `74HC123N` / `SN74HC123N`, DIP-16 |
| 74HC08 | `SN74HC08N`, DIP-14 |
| BC337 / BC327 | TO-92 (already through-hole) |
| IRLZ44N | TO-220 |
| 2N7000 | TO-92 |
| SB560 | DO-201AD axial |
| TVS 33 V | `P6KE33CA` or `1.5KE33CA`, axial |
| Coil flyback | `1N4148`, DO-35 |
| SRD-05VDC-SL-C relay | bare relay, TO-5-ish THT (EN50005/Form C) |
| LM2596HV buck | TO-220-5, bare chip — not a module |
| ACS724 | bare SOIC-8 chip on a generic SOIC-8→DIP-8 adapter, socketed like U2 |
| ESP32-S3-DevKitC | devkit module, socketed with 0.1" pin headers |

The ACS724 (`ACS724xLCTR-05AB`, §4.4) is SOIC-8, not through-hole itself —
what keeps the board through-hole is whatever it's mounted on. Earlier
revisions of this design used a Pololu carrier for that (0.1" holes,
ready-made); this one uses a generic SOIC-8-to-DIP-8 adapter instead
(0.3"/7.62mm row spacing, already in inventory). That swap drops two
things the Pololu carrier provided for free: a 0.1uF VCC bypass cap and a
1nF FILTER-to-GND cap, both confirmed against Allegro's own ACS712/ACS724
application circuit (not just the Pololu board). Both are now discrete
parts on the main schematic instead (C4, C5) - see NETLIST.md.

### 6.6 Sourcing (Netherlands)

Ruled out, with reasons, so they are not re-evaluated:

- **Digikey** — ~€25 shipping on small orders.
- **Farnell** — €50 order minimum, even after a reduction.

Working pattern is **two orders**:

- **Jellybean components** — Reichelt (DE) or TME (PL). Both ship to NL for
  single-digit shipping with no minimum. TME has the deeper catalogue. The
  bare ACS724 and a generic SOIC-8-to-DIP-8 adapter both belong here now
  that the Pololu carrier (§6.5) is out of the design - neither needs a
  modules supplier specifically.
- **Modules** — TinyTronics (Ede), Kiwi Electronics, Opencircuit (Zaandam) or
  Antratek.

**Mouser is being evaluated** as a possible single-order option — its
European free-shipping threshold may be low enough to cover the whole BOM.
Left open; not decided.

Substitutes worth recording:

- **IRLZ44N** → any 55–60 V logic-level N-channel in TO-220. Check **Qg and
  VDSS**, not Vgs(th) — see §6.2.
- **74HC08** → 74HC00 with inverted logic, or 74HC11 triple 3-input AND.
- **ACS724 carrier** → 10 mΩ shunt + INA240, but INA240 is SOIC-8 and needs a
  breakout, which fights the through-hole preference (§6.5).

---

## 7. Firmware

ESPHome, with motion control in a custom external component.

Pure YAML cannot do this safely. Three reasons, all in the safety path:

- The watchdog kick must come from the control loop, not a timer. ESPHome's
  `interval` runs in the cooperative main loop, which WiFi work can stall for
  hundreds of ms. Solving that with a hardware LEDC pulse is worse — it keeps
  kicking through a hang, making the monostable decorative.
- Relay sequencing is a small state machine with real timing constraints.
- `adc` sensors poll on the order of seconds. Useless for collision detection.

What ESPHome earns: OTA, logging, web server, Home Assistant integration, and
LVGL for the screen. Inheriting `cover::Cover` makes the desk a first-class HA
entity with open/close/stop/position and no glue.

### 7.1 Structure

```
config/
  desk.yaml
  my_components/
    desk/
      __init__.py      (empty)
      cover.py         config schema + codegen
      desk_cover.h
      desk_cover.cpp
```

`cover.py` declares the YAML keys and emits C++ setter calls into the
generated `main.cpp`. Anything configurable goes there; anything fast goes in
the `.cpp`.

### 7.2 Control loop

A FreeRTOS task pinned to **core 0**, ticking at 200 Hz via `vTaskDelayUntil`.
WiFi lives on core 1 and cannot stall it. Each tick reads current, runs the
state machine, updates PWM duty, and *then* kicks the watchdog — after a
completed iteration, never on a timer.

States: `IDLE → SETTLING → RAMPING → RUNNING → STOPPING → IDLE`, plus a latched
`FAULT`. Relay writes are legal in `IDLE` only, and every direction change
routes through `SETTLING`. Enforcing that structurally is what stops a future
refactor quietly switching a relay under load.

Starting parameters: 20 kHz PWM, 500 ms ramp up, 300 ms ramp down, 50 ms
settle. Tune the ramps by feel.

### 7.3 To fill in

- `read_current_()` is a stub. The ADC call differs between IDF 4.x
  (`adc1_get_raw`) and 5.x (`adc_oneshot_read`) — the one place to adapt to
  your toolchain, and why the YAML specifies `esp-idf` rather than Arduino.
- Relay `inverted:` flags depend on your module (see §6.3).

**Flash with the motor unplugged first.** Watch the log and the current sensor
before anything can move.

---

## 8. Phase 2 — position feedback and presets

Phase 1 deliberately has no absolute position sensing. Presets need it.

> Full option analysis, including mounting constraints, range limits and the
> approaches that will not work, is in **`APPENDIX.md` §2**. The summary below is
> the decision, not the reasoning.

### 8.1 Direction

Leading candidate is a **VL53L1X time-of-flight sensor** aimed at the fixed
foot plate. Absolute encoding is not worth paying for, because the bottom
limit switch already gives a repeatable mechanical reference detected by
current collapse — one trip down re-homes the desk.

> Full analysis — mounting constraints, the range limit that could sink it,
> incremental optical and magnetic alternatives, commutator ripple counting,
> and why an IMU cannot do this — is in **`APPENDIX.md` §2**.

### 8.2 Data worth logging from day one

Current against time for a full travel in each direction, and coast distance
after cutoff at various speeds. That's exactly the calibration data phase 2
needs, and you get it free by using the desk. If commutator ripple turns out
to be cleanly visible on the ACS724 trace, the cheapest option may be the one
already built.

---

## 9. Open questions

- Exact position of the limit switches inside the leg is inferred from
  behaviour; the leg was never opened.
- The polarity convention at each limit (which probe orientation gave 0.6 V)
  was not written down. Two-minute remeasure, needed before wiring the relays
  so "up" is actually up.
- Wire colour to circuit number is predicted but unconfirmed (§1.6), and is
  **not required** for the build — noted only for completeness.
- Which of yellow / white is supply positive was never recorded. Also not
  required: circuits 3 and 4 are identified on the connector itself.
- The housings carry no legible moulded circuit numbers, so the §1.6 diagram
  is the sole definition of the numbering. Mark the MOT_A cavity with paint so
  the physical part carries the convention rather than this file.
- ERC has been run (`kicad-cli sch erc`): 127 violations, all triaged as
  either documented gaps (unused MCU pins, U3/U6 spare units, SDA/SCL
  pending Phase 2) or artefacts of this design's power-flag/embedded-symbol
  conventions — no structural defects found.

---

## 10. Files

| File | Purpose |
|---|---|
| `APPENDIX.md` | Background, rejected alternatives, phase-2 analysis — not required to build |
| `CLAUDE.md` | Project context for Claude Code |
| `SHOPPING_LIST.md` | Purchase-ready BOM, grouped by supplier — see §6 for the narrative version |
| `schematics/desk.kicad_sch` / `.pdf` / `.svg` | **The chosen schematic design** |
| `schematics/desk.kicad_pcb` | **The chosen PCB layout** — 70×100mm, 2-layer, hand-milled (§6.5) |
| `schematics/NETLIST.md` | Connectivity reference, generated + annotated |
| `schematics/gen/` | Generator and its dependencies — see `CLAUDE.md` |
| `enclosure/shell.scad` / `.stl` | 3D-printable enclosure (single open-bottom shell) — component clearance is an estimate, see the file's own header comment |
| `my_components/desk/` | ESPHome external component |
| `desk.yaml` | Example ESPHome config |

Schematics are KiCad 7 format (`version 20230121`); KiCad 7, 8 and 9 open them.
Symbols are embedded (either hand-drawn or copied from real KiCad libraries),
so there are no external library dependencies at open-time. Regenerate with
`cd schematics/gen && make` (or `python3 sch.py`, then
`kicad-cli sch export pdf ../desk.kicad_sch`).

---

## 11. Safety notes

- Mains lives in the PSU. All work here is on the 29 V side. Do not open the
  supply.
- 29 V will not hurt you, but a dead short across it will make a mess. The
  supply can deliver 1.8 A continuously and rather more from its output
  capacitance.
- The spindle is self-locking and holds the load unpowered. This is what makes
  coast an acceptable failure mode, and it is the single assumption most worth
  re-verifying if the frame is ever changed.
- The 1.8 A supply limit is part of the safety story on a desk with no
  anti-collision. Replacing the PSU with something beefier removes protection
  the design depends on.
