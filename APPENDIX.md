# Appendix — background, rejected alternatives, future work

**Nothing in this file is required to build or maintain the current design.**
For that, read `README.md`.

This is where the rest of the design process lives: reasoning that is not yet
load-bearing, options that were evaluated and dropped, and analysis of work
that has not started. It exists so the next round begins where the last one
finished, rather than re-deriving the same conclusions.

Read it when you are about to propose an approach, change a parameter whose
value looks arbitrary, or start phase 2.

---

## 1. Control loop and sensing

### 1.1 Collision detection

**Use dI/dt against a rolling baseline, not an absolute threshold.** Baseline
current shifts with load, direction, temperature and position, so any fixed
trip point is either too twitchy when cold and loaded or too slow when warm
and empty.

**Downward travel is the hard case, and also the dangerous one.** Gravity is
assisting the motor, so an obstruction produces a *smaller* relative rise in
current than the same obstruction going up. The direction that most needs
detection is the one where the signal is weakest. Budget more sensitivity
going down, not less.

Note that the stock desk has no collision detection at all; the PSU current
limit is the only protection. Anything added here is a genuine improvement
rather than a restoration.

### 1.2 Reading current correctly under PWM

**Motor current and supply current differ by roughly the duty cycle.** During
a low-duty ramp the winding can carry two or three amps while the supply
contributes under one, the difference coming from the PSU's output
capacitance. Size the drive path on motor current; size the supply budget on
average current.

**The sensor must be in the motor leg, not the FET return.** With low-side
chopping the FET only conducts during the on-time — freewheel current bypasses
it entirely. A low-side shunt therefore reads a chopped fraction and needs
synchronous sampling inside the PWM on-window plus a duty correction. Placing
the ACS724 in the motor leg puts it inside the freewheel loop, so it reads
true motor current continuously. This is the main reason the Hall sensor won
over a shunt-plus-INA240, despite costing more.

### 1.3 Two free signals not currently used

**Rail sag as a load proxy.** Because the supply current-limits rather than
sagging gracefully, the 29 V rail collapses in a fairly binary way when demand
exceeds 1.8 A. A resistor divider on VSW into a spare ADC gives an obvious
"we are in current limit" flag — cheap redundancy alongside the shunt, and
useful for distinguishing a real obstruction from a sensor fault.

**Back-EMF during coast.** With the FET off and the relays released, the
voltage across the winding is proportional to speed. Useful for stall
detection and, more practically, for measuring coast distance after cutoff —
which is what sets preset accuracy.

### 1.4 Why 20 kHz PWM

Above audible, and comfortably short compared with the winding's electrical
time constant. With 2.5 Ω and a plausible 1–3 mH for a motor this size,
τ = L/R lands around 0.4–1.2 ms. At 20 kHz the period is 50 µs, well inside
that, so the current stays in continuous conduction and the motor sees an
effectively smooth average rather than a train of pulses.

### 1.5 Ramp tuning

Starting points are 500 ms up, 300 ms down, 50 ms settle. Tune by feel. Two
things to watch: a ramp that is too slow wastes time at low duty where torque
is marginal under load, and a ramp-down that is too fast reintroduces the
clunk you set out to remove.

Some of the perceived jolt on the stock desk was never electrical — spindle
backlash and the columns taking up load contribute, and no amount of ramping
removes that entirely.

---

## 2. Phase 2 — position sensing, full option analysis

### 2.1 What is actually required

**Repeatability matters more than absolute accuracy.** A consistent 4 mm
offset is invisible in use; 4 mm of jitter is not. Median-filter a handful of
samples and only trust a reading once motion has settled.

**Absolute encoding is not worth paying for.** The bottom limit switch is a
repeatable mechanical reference, detected by current collapse, so one trip
down re-homes the desk. That removes most of the appeal of absolute sensing
and opens up the cheap incremental options below.

### 2.2 Time-of-flight (leading candidate)

VL53L1X, mounted on the moving part and aimed **at the fixed foot plate**,
not at the floor. Same geometry, but the target is rigid and always present
rather than whatever ends up in the footwell.

- Range seen is roughly 600–1100 mm across the 68–118 cm travel. The top end
  is where the VL53L1X gets marginal: the ~4 m specification is a dark-room
  figure, and bright ambient IR pulls it toward ~1.3 m. **Prototype at maximum
  height before committing to a mount.**
- Long distance mode, timing budget 100–200 ms. At 25 mm/s that is only
  2–5 mm of travel per sample.
- Matte white target on the foot. Dark, glossy or textured surfaces cost
  signal exactly where margin is thinnest.
- Run offset and crosstalk calibration, especially behind any cover window.
- **If range proves marginal, measure one telescoping stage instead of the
  whole column.** On a 3-stage leg each stage moves about half the total, so
  the required range halves at the cost of needing the ratio.

### 2.3 Incremental optical or magnetic

- **Reflective sensor over a printed stripe.** 2 mm pitch printed on a laser
  printer, read with a QRE1113 or TCRT5000. Two sensors offset by a quarter
  pitch gives quadrature and direction. At 25 mm/s that is ~12 edges per
  second — trivially slow to process, and 1 mm resolution is far better than
  needed.
- **Magnetic strip and Hall sensor.** Same idea, immune to dust and grime,
  which matters under a desk. Alternating-pole tape plus an AS5311 is the
  clean version; a row of magnets and a Hall switch is the crude one.

The real cost of either is mechanical: a 500 mm scale mounted rigidly along
the travel, parallel and at controlled standoff, plus a head on the moving
part. Considerably fussier than pointing a sensor at a foot plate. What you
get back is resolution you do not need, plus immunity to the ambient-IR
problem that is ToF's main weakness here.

### 2.4 Commutator ripple counting

Zero additional hardware — it uses the current sensor already fitted. Ripple
for a motor like this lands somewhere in the few-hundred-hertz range, so it
needs a clean signal and a few kHz of sampling, not a module's coarse current
output.

Two catches: ripple gets messy under PWM, and counts are lost around start and
stop, which is precisely where accuracy matters. Workable as a cross-check
against another sensor, not as the primary.

**The ESP32-S3's continuous DMA ADC mode is what makes this realistic.** On a
classic ESP32 it is much harder. If there is an S3 in the parts box, prefer it
for that reason alone.

### 2.5 Membrane potentiometer

A 500 mm SoftPot spans the travel almost exactly and reads on one ADC pin.
Genuinely absolute, genuinely simple. Rejected because the wiper needs an
actuator and these wear — but worth remembering as the low-effort option if
the ToF mount proves awkward.

### 2.6 What will not work

**A 6/9-DOF IMU cannot give height.** It gives tilt and vibration; extracting
displacement means double-integrating acceleration, which drifts into
uselessness within seconds. A fine "the desk is moving" detector, a useless
position sensor.

---

## 3. Controller hardware options

### 3.1 CYD (ESP32-2432S028R)

The 2.8" ESP32-2432S028R is the well-documented variant. Free GPIO is
typically **IO21, IO22, IO27, IO35**, with IO16/IO17 available if two of the
RGB LED colours are given up. Most other pins go to display SPI, the separate
touch controller SPI, the SD slot, RGB LED, LDR and speaker.

That covers phase 1 exactly. Phase 2's I²C then costs the LED colours.
IO35 is input-only, which is fine for the ADC, and is on ADC1 — mandatory.

Caveats: newer USB-C revisions and the 3.5" boards shuffle connectors, so
check the specific board rather than a generic pinout guide. It is a bare
PCB, so an enclosure is still needed.

### 3.2 M5Dial

Considered first. The rotary knob suits height adjustment better than a touch
screen, and the price buys an enclosure and integration. Dropped on cost once
it became clear there were spare ESP boards and displays already to hand.

Its port allocation, if ever revisited: G1/G2 for the bridge inputs, G6 for
the watchdog kick, G7 for current sense (ADC1-capable), leaving Port A's I²C
free for the ToF.

### 3.3 Strapping pins

This bites specifically because the failsafe design *requires* external pull
resistors on the drive lines, which fight the bootloader if placed wrong. On
the classic ESP32 avoid GPIO0, 2, 12 and 15 — GPIO12 pulled high at boot sets
the wrong flash voltage. The S3's strapping set differs, but the principle
holds.

---

## 4. Firmware alternatives

### 4.1 Why not pure YAML

The three failures — watchdog kick timing, relay sequencing, and `adc` polling
being far too slow — are in **`README.md` §7**, because they justify a
structural choice someone might otherwise undo.

### 4.2 Arduino under PlatformIO

The pragmatic pure alternative: LEDC, a hardware timer for the tick,
ArduinoOTA. You lose Home Assistant integration unless you add MQTT yourself,
and the UI is hand-rolled. Reasonable if the goal is understanding every line.

### 4.3 Interim presets without position sensing

If presets start itching before phase 2 lands: home against the bottom limit
by watching for current collapse, then dead-reckon on run time. It drifts —
up and down speeds differ, and both vary with load — but re-homing costs one
trip to the bottom. The component already does this; `read_current_()` is what
makes the homing work.

---

## 5. Rejected approaches

Recorded so they are not re-proposed. Several were reasonable at the time and
became obsolete when a later measurement changed the picture.

### 5.1 Passive soft start

- **NTC inrush limiter in series with the motor.** Passive,
  polarity-agnostic, a twenty-minute experiment, and a good way to find out
  how much of the jolt is electrical versus mechanical. Its weakness is that
  it will not fully cool between short, frequent desk movements, so the effect
  fades with repeated use. Still arguably worth doing once as a diagnostic.
- **Series resistor shorted out by a relay after a delay.** A two-step ramp
  rather than a smooth one, but it removes the worst of the jolt for almost
  nothing.

### 5.2 Inline soft starter, controller left intact

Before it was established that no controller exists, the plan was to insert a
soft starter between the control box and the motor without touching either.

Because the box reverses polarity, the device had to be polarity-agnostic: a
bridge rectifier with the motor in series on the AC side and a MOSFET across
the DC rail. It can self-power from the rectified rail, since full supply
voltage sits across it while the FET is off. The minimal version ramps the
gate with an RC network, running the FET in linear mode — needs a heatsink and
a bleed resistor, but no microcontroller.

Two problems killed it. Chopping an inductive load needs a freewheel path, and
a plain antiparallel diode will not do when polarity reverses — you need a
second bridge across the motor with its DC terminals joined through a diode.
And once it became clear the rockers *were* the H-bridge, replacing them was
strictly simpler than wrapping them.

### 5.3 Keeping the OEM handset in the circuit

- **PhotoMOS or optocoupler taps across the rocker contacts** (AQY212 and
  similar). This works only if the rockers switch *signals*. They switch full
  motor current, so it was never applicable — but it was the plan for several
  messages before that was measured.
- **Leaving the rockers wired in parallel as a fallback.** Actively
  dangerous with any electronic drive: the rockers would short the drive
  outputs directly to the supply rails. Either remove them from the motor
  circuit entirely, or use a changeover with no position where both are live.
- **Optocoupler rocker sensing** (PC817 across each handset conductor,
  ~6 mA through a 4k7 half-watt resistor). Correct, isolated, and superseded
  once the board began feeding the handset 3.3 V, which makes the rockers dry
  contacts readable straight into GPIOs.

### 5.4 H-bridge ICs

Rejected on voltage headroom rather than current — see README §6.1. If ever
revisited, the parts with genuine headroom at 29 V are the Pololu G2 24v13
(rated to 40 V, current sense output, sleep pin ideal for the watchdog) and
the DRV8876 (4.5–37 V, ~3.5 A, IPROPI current mirror, nSLEEP).

Also worth remembering: an integrated bridge deletes the FET, the gate driver
and the freewheel diode, so the part count difference is smaller than it
looks. What it costs you is the shoot-through failure mode that relays simply
do not have.

### 5.5 Single DPDT relay for direction

Cheaper than two SPDTs and adequate for direction, but **it has no neutral
state**. Wired the standard reversing way, de-energised gives one direction
and energised the other; there is no third position, so it cannot brake. This
is exactly why the OEM used two independent changeovers.

### 5.6 Transfer relay with automatic fallback

Kept as `desk_inline.kicad_sch` because it is a good design, not a bad one.
Three extra relay poles buy in-place OEM fallback: power loss or a watchdog
timeout hands the desk back to the rockers with no intervention. Dropped only
because reverting by unplugging the box was judged good enough.

If it is ever revived, the one subtlety worth keeping is that the transfer
poles carry full motor current in OEM mode and must be rated accordingly,
while a watchdog trip is self-safe because the FET turns off in microseconds
and the relays take milliseconds to release.

---

## 6. Evidence worth capturing

While the desk is apart, and not obtainable later:

- Photographs of the handset internals, the motor housing terminals, and the
  connector halves next to a ruler.
- Any label on the motor housing. A model string would be the single highest-
  value data point — OEM parts usually carry one, and if it maps to a Jiecang
  / Kaidi / TiMOTION part, a real datasheet suddenly exists.
- Current traces for a full travel in each direction, and coast distance after
  cutoff at a few speeds. This is exactly the calibration data phase 2 needs,
  and it comes free from normal use once the board is in.
- If commutator ripple turns out to be cleanly visible on those traces, the
  cheapest position sensor may be the one already built.

Contacting 2-connect for a spare control box also costs nothing. Even a
refusal often arrives with a model number attached.

---

## 7. Tooling notes

**Schematics are generated.** `schlib.py` provides symbol definitions with
absolute pin lookup, orthogonal wire routing and junctions; each `sch_*.py`
lays out one sheet. Edit the generator, never the `.kicad_sch`.

**Format version is KiCad 7 (`20230121`)**, chosen because that is what
`kicad-cli` was available at. KiCad 7, 8 and 9 all open it. Symbols are
defined inline, so there are no external library dependencies.

Export:

```sh
kicad-cli sch export pdf desk_simple.kicad_sch
kicad-cli sch export svg --output . desk_simple.kicad_sch
```

**Two dead ends in the drawing work**, recorded so they are not repeated:

- Rendering the netlist as a graphviz connectivity graph is a useful *audit*
  tool — it caught a real wiring error where a schematic note and the netlist
  disagreed — but it is not a schematic and should not be presented as one.
- Running literal power rails across the sheet, in an attempt to remove
  visually disconnected "islands", made things worse: every ground became a
  long vertical and the sheet turned into a picket fence. Local GND and rail
  symbols are the conventional idiom precisely because they avoid this. The
  actual problem in that draft was that *signals* were labelled rather than
  wired.

**ERC has never been run.** Expect power-flag and pin-type complaints;
cosmetic rather than structural.

**`sch_simple.py` was not actually regenerable when this repo was first
committed.** It pulled its symbol library in with
`exec(open("/home/claude/kicad/_sym_preamble.py").read())` — a file that only
ever existed in the sandbox the original Claude.ai session ran in, and was
never part of the export. `sch_original.py` and `sch_inline.py` had already
been migrated to a normal `from schlib import ...` and defined their symbols
inline, so only `sch_simple.py` was affected, but it's the chosen design —
the committed `desk_simple.kicad_sch` was an artefact nothing in the repo
could reproduce. All three generators also wrote their output to that same
sandbox path (`/home/claude/kicad/desk_*.kicad_sch`) instead of the working
directory.

Fixed by extracting the symbol set `sch_simple.py` needs into `symbols.py`
(copied from the equivalent block already inline in `sch_inline.py` — the two
generators need the same symbols) and pointing the relevant `open()` calls at
the local directory. Verified by regenerating all three `.kicad_sch` files
and diffing byte-for-byte against what was already committed: identical.
`sch_inline.py` was left with its own inline copy rather than switched to
import `symbols.py` too, since it already worked and didn't need touching.

A `Makefile` in `schematics/` now runs the full `.py → .kicad_sch → .pdf/.svg`
chain. It marks the `.kicad_sch` targets `.PRECIOUS` — without that, GNU
Make treats a file that is a build product of one rule and only a
prerequisite of another as a disposable intermediate and deletes it after
use, which would silently delete the tracked schematic.
