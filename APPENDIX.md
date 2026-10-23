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

### 1.6 Proposal: spare 74HC123 channel as a second, hardware-enforced timeout

**Not implemented — a design change, not a documentation fix. Needs
discussion before it goes into the schematic.**

U2 is dual (74HC123, §5.7) and only one channel is used, for the 250 ms
watchdog. The spare channel could provide a second, independent timeout: a
~30 s monostable retriggered by "any drive line active," hard-limiting how
long the desk can run continuously.

Why it would be worth doing: the travel timeout is currently a firmware
property (`max_run_ms`), so it dies with the firmware — a hung or buggy
control loop that keeps a drive line asserted has nothing hardware backing
it up past the existing (much shorter) watchdog. Moving the *duty-cycle*
limit into hardware makes maximum continuous run something the MCU cannot
override, the same way the existing 74HC123 channel already makes the
kick-or-stop behavior something the MCU cannot override. It would also
enforce the manual's duty-cycle limit (§1 of the manual, README §1.1)
against a firmware bug rather than only trusting firmware to enforce it.

What would need deciding before wiring it in: what "any drive line active"
should actually gate off if it trips (full stop, like the existing
watchdog, or just inhibit further starts until it resets?), and whether 30
s is the right figure against the manual's actual duty-cycle numbers.

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

Kept as a schematic (`desk_inline.*`, since dropped — see §7) for a long time
because it is a good design, not a bad one. Three extra relay poles buy
in-place OEM fallback: power loss or a watchdog timeout hands the desk back
to the rockers with no intervention. Dropped only because reverting by
unplugging the box was judged good enough.

If it is ever revived, the one subtlety worth keeping is that the transfer
poles carry full motor current in OEM mode and must be rated accordingly,
while a watchdog trip is self-safe because the FET turns off in microseconds
and the relays take milliseconds to release.

### 5.7 74HC122 for the watchdog, instead of 74HC123

Functionally the better fit: a single-channel retriggerable monostable with
overriding clear, and its internal 10k timing resistor would eliminate R7,
leaving only C1. Considered as a replacement for the dual 74HC123 U2 uses
(only one of its two channels is populated).

**Discontinued in the HC family.** Searches for an HC122 datasheet return the
HC123 instead, and no current NXP or TI HC122 part page exists. The '122
survives as 74LS122 only, and dragging a TTL part into an otherwise HC design
buys nothing. Retaining 74HC123, recorded here so the question is not
reopened and re-researched later.

**CD4538** (dual precision retriggerable monostable) is worth noting as the
alternative if timing tolerance ever matters — the HC123's timing spread is
famously loose. It does not matter for a 250 ms watchdog, which only needs to
sit comfortably above the 50 ms kick interval and below "dangerous".

**74x121 and 74x221 will not work** for this — both are non-retriggerable
one-shots, and the watchdog's whole point is retriggering on every kick.

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
absolute pin lookup, orthogonal wire routing and junctions; `sch.py` lays
out the sheet. Edit the generator, never the `.kicad_sch`. Generator and
dependencies live in `schematics/gen/`; the `.kicad_sch`/`.pdf`/`.svg` and
`NETLIST.md` land one level up in `schematics/` — machine-facing tooling
kept apart from the human-facing result.

**Format version is KiCad 7 (`20230121`)**, chosen because that is what
`kicad-cli` was available at. KiCad 7, 8 and 9 all open it. Symbols are
embedded verbatim (hand-drawn, or copied out of real KiCad libraries via
`import_symbol()`), so there are no external library dependencies at
open-time.

Export (from `schematics/gen/`):

```sh
kicad-cli sch export pdf -o ../desk.pdf ../desk.kicad_sch
cd .. && kicad-cli sch export svg desk.kicad_sch   # -o always names a
                                                    # directory for svg,
                                                    # never a file - cd
                                                    # first instead
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

**ERC has been run** (`kicad-cli sch erc`): 127 violations, all triaged as
documented gaps or power-flag/embedded-symbol artefacts — no structural
defects. See README §9.

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

A `Makefile` in `schematics/gen/` now runs the full `.py → .kicad_sch →
.pdf/.svg` chain. It marks the `.kicad_sch` target `.PRECIOUS` — without
that, GNU Make treats a file that is a build product of one rule and only a
prerequisite of another as a disposable intermediate and deletes it after
use, which would silently delete the tracked schematic.

**`make check`** (same Makefile) runs `find_shorts.py`/`find_diagonals.py`/
`find_crossings.py`/`find_body_crossings.py` — schematic-quality checkers
that trace `sch.py`'s actual `wire()`/`place()` calls (via `_trace.py`,
which monkeypatches both before importing `sch`) rather than re-parsing the
`.kicad_sch` output, so they see exactly what the generator draws. Previously
these were recreated from scratch each session (lost across context
compactions); persisted here instead. One bug found while persisting them:
the tracer recorded wire() calls' raw pre-snap arguments instead of the
post-`_snap_pt()` coordinates actually drawn, producing false-positive
"diagonal" reports for wires that render perfectly orthogonal - fixed by
snapping inside the tracer the same way `wire()` does internally.

**`sch_original.py`/`sch_inline.py` and their outputs were dropped once the
symbol migration and layout cleanup on the chosen design were done.**
`desk_original` was the stock desk's own wiring — fully described by §1/§2's
measurements, so keeping a duplicate schematic added nothing. `desk_inline`
was design 3.3 (README §3), a good design but over-complex, kept only for
reference while 3.4 was still being finished; once 3.4 (this file) was
settled, keeping a second maintained generator around had no further purpose.
With only one sheet left, `sch_simple.py`/`desk_simple.*` were renamed to
`sch.py`/`desk.*` — "simple" was only ever a name to distinguish it from the
other two.

### 7.1 Isolation-milling tooling: FlatCAM's bugs, and the move to pcb2gcode

`schematics/gen/` also holds the isolation-milling pipeline: `mill.tcl`
(FlatCAM headless driver), `verify_isolation.py` (per-pixel confirmation
that the toolpath actually cuts the copper it needs to), `snapmaker_header.py`
(header patch the Snapmaker touchscreen requires), and `fix_travel_jumps.py`
(FlatCAM-specific G-code post-processor, see below). None of this was listed
in `CLAUDE.md`'s layout table until this pass — an oversight, not a decision.

**Why `verify_isolation.py` exists at all.** A zone-fill Gerber render's own
"white" areas are design *intent* (clearance/keepout), not a property of the
raw copper-clad blank - the blank starts copper everywhere, and only the
G-code toolpath actually sweeping a pixel removes material there. Treating
design-white as already-bare (an earlier version of this checker did exactly
that) silently invents material removal that never happened. The tool
renders the KiCad copper SVG and the real (parsed, not idealized) G-code
toolpath into the same raster and checks, per pixel, whether the swept area
actually falls on raw-blank copper - see its own docstring for the full
detail, including why off-board has to be determined from the known
board-rectangle geometry rather than SVG alpha (kicad-cli's Edge.Cuts export
does not reliably fill the board interior opaque).

**Three distinct, confirmed FlatCAM `isolate()` defects**, found by
progressively distrusting each "looks fine" result against this checker:

1. **`iso_type=2` (the default, exterior+interior combined) silently fails
   across most of a large ground-pour-with-many-cutouts polygon** - measured
   ~34-38% real toolpath coverage of the design's own clearance-channel
   centerlines, board-wide, not just at one complex corner. `iso_type=1`
   (interior alone) produces *zero* G-code paths for this Gerber-derived
   region topology (confirmed in FlatCAM's own debug log). `iso_type=0`
   (exterior only) is not simply "what's left after subtracting `iso_type=1`
   from `iso_type=2`" - it's a different, more robust code path that alone
   recovered the vast majority of real coverage. `mill.tcl` now isolates
   both copper layers with `-iso_type 0` explicitly, with this reasoning
   inline as a comment.
2. **`fix_travel_jumps.py`'s original length-threshold heuristic
   (">1mm G1 move while cutting = bogus gouge") was itself actively harmful**
   once `iso_type=0` was adopted: a genuine long straight cut (e.g. a run
   parallel to the board's own edge, needing few tessellation points) is
   indistinguishable from a genuine bogus gouge by length alone (no clean
   percentile gap - p95=0.56mm, p99=7.86mm, max=86mm, all real board-scale
   distances). Comparing raw pre-fix output (76% coverage) against the
   "fixed" output (33% coverage) on the *same file* is what caught this -
   the post-processor meant to fix one bug was quietly destroying more
   coverage than it recovered. Rewritten to be geometry-aware: a candidate
   move is only "dangerous" if it does NOT hug a real copper/clearance edge
   the whole way (checked against the same KiCad SVG render
   `verify_isolation.py` trusts, via a distance-to-copper-*edge* field - not
   distance-to-copper, since being inside solid copper trivially scores as
   "close to copper" and would let a gouge through a pad's interior pass).
   A second bug category needed a separate fix: a path can close a loop
   short by ~1mm at the exact point it retracts, detectable by comparing the
   retract position against the segment's own recorded start point (see the
   script's own docstring for both fixes in full).
3. **A narrower, unpatchable defect**: FlatCAM's G-code path ordering can
   mid-loop detour through a nearby unrelated feature and back, permanently
   skipping a short (~1mm or less) direct connection on the original loop.
   Confirmed directly on one specific small pad (raw G-code inspection
   showed the loop's start/end points already coincide - it isn't an
   unclosed-loop bug - but direct `swept`-mask sampling at the true gap's
   own midpoint came back `False`). Not detectable by either a length
   threshold or the edge-hugging check above: every individual move in the
   detour is itself legitimate, they just don't sum to a complete loop for
   the pad in question. This is the specific finding that motivated trying
   a different tool rather than continuing to patch FlatCAM's output.

**pcb2gcode was rejected in an earlier session on hearsay** - other people's
reported experience, never tested against this board - and documented
nowhere except a terse comment in an earlier Makefile revision. Given three
confirmed, real FlatCAM bugs on this specific board, it was tried directly
this session. Building it exposed real, separate tooling problems:

- **The AUR `pcb2gcode-git` package is stale.** Its `prepare()` step still
  runs `autoreconf -i && ./configure`, but upstream deleted `configure.ac`/
  `Makefile.am` when it migrated the whole build to CMake; the PKGBUILD
  never caught up, so it fails outright (`autoreconf: error: 'configure.ac'
  is required`). Bypass the PKGBUILD entirely and build the CMake tree
  directly (this is what `tools/pcb2gcode-src/` is, see below) - not
  installed as a system package at all.
- Two more issues were hit and root-caused **against the old, abandoned
  autotools build** before the CMake migration was discovered; neither
  affects the CMake build, but both are worth knowing so they aren't
  re-discovered blind if anyone ever has to debug the old path: (a) GCC 16's
  `#include_next` chains break if a directory it already searches by default
  gets re-added via `-isystem` in a different position - `configure.ac`
  blanket-substitutes every `-I` in `$(BOOST_CPPFLAGS)` to `-isystem`, and on
  this Arch-based system Boost lives directly under `/usr/include`, so this
  reliably broke `<cstdlib>`; `geos-config --cflags` independently emits the
  same bare `-I/usr/include`. (b) `path_finding.cpp` used an old
  `boost::optional` construction pattern that a newer installed Boost's
  explicit-constructor rules reject - already fixed upstream on git HEAD,
  commit `1120553b`.

**Build recipe** (validated this session; the checked-out tree lives at
`tools/pcb2gcode-src/`, gitignored the same way `tools/flatcam/` is - not a
system package):

```sh
sudo pacman -S gerbv-git    # or: yay -S gerbv-git --noconfirm
                            # (conflicts with plain gerbv - pcb2gcode needs
                            # the newer libgerbv API only gerbv-git ships)
git clone https://github.com/pcb2gcode/pcb2gcode tools/pcb2gcode-src
cd tools/pcb2gcode-src
cmake -B build -DCMAKE_BUILD_TYPE=Release -DPCB2GCODE_COMPILE_WARNING_AS_ERROR=OFF
cmake --build build -j$(nproc)
```

`-DPCB2GCODE_COMPILE_WARNING_AS_ERROR=OFF` works around a
`-Wmaybe-uninitialized` false positive deep in Boost.Geometry's own template
code (envelope/expand box computation), promoted to a hard error by
`-Werror` under this system's gcc - nothing to do with pcb2gcode's own code.
No source patching needed on this path. Binary ends up at
`tools/pcb2gcode-src/build/pcb2gcode`.

**Coordinate frame - the one genuinely surprising, safety-critical finding.**
`--zero-start` anchors the job origin to `board.get_bounding_box().min_corner()`
- the union of all loaded layers. Without `--outline`, that's just the
copper's own bounding box (~67×98mm here), not the true 70×100mm board - the
wrong anchor for a milling jig that registers against the *physical blank's*
edges. Passing `--outline desk-Edge_Cuts.gm1` (with a placeholder
`--cutter-diameter`/`--zcut`/`--cut-feed`/`--cut-speed`/`--cut-infeed` - the
resulting `outline.ngc` is never used, the blank is pre-cut same as
`mill.tcl`) fixes the anchor to the true board - except pcb2gcode's own
outline-bounding-box computation **inflates that box outward by
`(cutter-diameter + 0.05mm)` in +X/+Y**, undocumented anywhere and only
found by tracing a known drilled hole's exact coordinates end to end through
the pipeline (a T8/3.2mm mounting-hole drill at Gerber `X19Y-19` should land
at job `(4, 96)` on a zero-started, true-board-anchored frame; it actually
landed at `(5.05, 97.05)` with a 1.0mm cutter-diameter placeholder - exactly
`1.0 + 0.05` off in both axes). Fixed with `--x-offset -1.05 --y-offset -1.05`
(paired with the 1.0mm placeholder `--cutter-diameter` `make mill` uses) -
after that correction the same hole lands at exactly `(4, 96)`, verified to
5 decimal places, and every copper feature's extent falls cleanly inside
`[0,70]×[0,100]` (before the fix, some extended past board edges into
negative jig territory). `--mirror-axis 35` (half the *true* 70mm board
width) is only correct once the bounding box above is fixed - get any of
this wrong and every coordinate silently shifts by about a millimetre
against the physical jig.

**Re-verification against pcb2gcode's real output** (`verify_isolation.py`,
same tool that found the FlatCAM bugs above): both layers report 100% of
swept toolpath pixels landing on real raw-blank copper, and the connectivity
check finds *more* distinct isolated copper islands than FlatCAM's own
best-tuned output (276/300 vs FlatCAM's 228) - more separation, not less,
i.e. no evidence of new shorts. The specific pad where FlatCAM's third bug
(the path-ordering detour) was confirmed shows a fully closed ring in
pcb2gcode's output. A cruder, ad hoc board-wide "skeletonize the design's
clearance channels and check toolpath overlap" metric (built this session,
not part of `verify_isolation.py`) was also tried for a single aggregate
number, but proved unreliable on this board: direct spot-checks of several
of its "uncovered" flags turned out to be false positives of the metric
itself (its own antialiasing-exclusion logic around drilled holes and small
pads created phantom boundaries where the design has none - e.g. a via
correctly soldered straight to its surrounding ground pour, with no
isolation channel needed at all, still got flagged as "missing a channel").
Rather than keep patching a proxy metric that had already fooled the
investigation once (see the FlatCAM section above - the same trap), the
per-pixel diagnostic and connectivity check above are the numbers actually
trusted here.

**pcb2gcode retracts to Z-safe before every disjoint isolation loop as a
structural property of its own G-code** (confirmed by counting retract
commands against loop count) - no evidence of FlatCAM's silent same-Z gouge
bug that `fix_travel_jumps.py` exists to fix, so that post-processor is not
run on pcb2gcode's output. This was checked, not assumed.

`make mill` now runs the pcb2gcode pipeline by default; the FlatCAM pipeline
stays available as `make mill-flatcam` (still using `mill.tcl` and
`fix_travel_jumps.py` exactly as before) in case pcb2gcode's from-source
build ever proves too fragile on a future system update. See README §5
for the one-line summary of the decision.

**`--voronoi` was tried and rejected.** The fixed-width isolation channel
above still leaves small copper remnants where two closely-spaced same-net
pads (e.g. adjacent pins in a 2.54mm header row) each keep an independently
rounded boundary that doesn't quite meet its neighbor - harmless (confirmed
via the connectivity check: each remnant is the same colour as, i.e. part
of, one specific neighbouring pad, never a bridge between two different
nets) but untidy. `--voronoi` mode replaces the fixed-width-channel
algorithm with a fair boundary computed between neighbouring copper
regions, which does clean these up - confirmed visually at the exact header
row above, and it still honours `--isolation-width`/`--milling-overlap`, so
the channel width itself doesn't get thinner. But it's a different
algorithm, not just a flag on the same one, and two separate real problems
were found in the same test run:

- The coverage metric (toolpath-only-touches-real-copper) dropped from 100%
  to 96.9%, traced to Voronoi regions for a couple of near-board-edge nets
  extending past the true board rectangle entirely (nothing bounds the
  "fair" boundary on the open side) - two visible spikes past the drawn
  board edge in the full-board render. That means commanding the mill to
  travel briefly outside the 70x100mm blank in those spots.
- **Worse: two of the four corner mounting holes weren't isolated at all.**
  Spot-checking all four corners directly (the same per-pixel diagnostic
  used throughout this investigation) showed the top two holes isolated
  cleanly, but at the bottom two the toolpath just traces the flat board
  edge and skips the hole's own clearance arc entirely - leaving that
  hole's surrounding copper permanently connected to the ground pour on the
  real board. Not a cosmetic issue like the header-row remnants above: a
  genuine unmilled short, and specifically the kind of defect this whole
  verification pipeline exists to catch before it reaches the mill.

Rejected on this basis rather than chasing a fix; the per-net fixed-width
channel above, despite its small cosmetic remnants, isolates all four
mounting holes correctly and never commands anything outside the board.

### 7.2 `custom_isolate.py`: generating the toolpath directly from KiCad's own boundary

By this point the isolation-milling investigation had found five confirmed
bugs across two independent tools' internal polygon-offset algorithms
(FlatCAM's default isolate(): 3; pcb2gcode's `--voronoi` mode: 2, one of
them an actual short) and zero in KiCad's own zone fill. Both tools take
the same fundamentally redundant path: KiCad already computes the exact
copper/clearance boundary during zone fill (that's what
`verify_isolation.py`'s `render_at()` renders and has been the trusted
ground truth this whole investigation), and both tools re-derive a
toolpath from a re-imported, re-flattened Gerber using their own offset
algorithm - a second, independent computation of something already solved,
and exactly where every bug above came from.

`schematics/gen/custom_isolate.py` skips that redundant step: it rasterizes
the same KiCad SVG render (not Gerber, no re-import), extracts copper
regions directly via `cv2.findContours` (with proper hole hierarchy - RETR_CCOMP,
so a filled region's own cutouts are tracked as real holes, not lost),
builds Shapely polygons, and offsets them with Shapely's own `.buffer()` -
backed by GEOS, a library specifically known for getting robust polygon
offsetting right in exactly the cases FlatCAM and pcb2gcode's own
implementations were failing. The result is written straight to G-code in
board-mm coordinates, with true board bottom-left as `(0,0)` by
construction - no dependency on pcb2gcode's bounding-box-inflation quirk
(§7.1 above) at all.

Five real defects were found and fixed during development, each traced to
a genuine root cause rather than papered over:

1. **A pad's own future drill hole isn't a net boundary.** The first
   version isolated every ordinary THT pad twice - once correctly around
   its outer edge, and again around its own hole, which KiCad's SVG export
   draws as bare (matching the real annular-ring pad shape) even though
   it's not a clearance requirement, just where the drill will go. Milling
   a channel there is pure waste (drilling removes it anyway) and risks a
   channel not landing exactly where the drill goes. Fixed by
   cross-referencing every hole in the copper mask against the real
   Excellon drill file (`is_drilled_away()`): a hole no wider than its
   matching real drill position is skipped entirely; only holes wider than
   their drill (e.g. a mounting hole's clearance disc, deliberately bigger
   than the hole itself) get a toolpath.
2. **Board-edge overreach.** Same root cause as pcb2gcode's `--voronoi`
   issue above but self-inflicted: without clipping, any copper feature
   running close to the board edge (the main ground pour routinely does)
   pushes the offset boundary slightly past it - confirmed directly, one
   single 221,696px cluster running nearly the full length of the board's
   right edge, not scattered noise. Fixed by intersecting every offset pass
   with the true board rectangle before emitting it.
3. **Gaps wider than the channel's own reach leave copper stranded in the
   middle.** Wherever a design's clearance gap is wider than twice the
   channel width, whatever's in the middle of it never gets touched by a
   fixed-width channel alone - confirmed harmless (the stranded copper is
   always fully disconnected from every net, visible as its own distinct
   colour in the connectivity check, never a bridge) but real leftover
   copper nonetheless, and confirmed to be an even bigger characteristic of
   pcb2gcode's own default output on this same board (769mm² total unswept
   area there vs 603mm² here, single biggest connected region 620mm² vs
   602mm²) - i.e. not a regression, a pre-existing and worse-elsewhere
   property of "channel-only" isolation strategies generally. Small,
   bounded instances are now auto-cleared with a dedicated second pass
   (`find_orphan_islands()` + `pocket_paths()`, concentric inward offsets
   until the island is fully consumed); anything bigger than
   `MAX_ORPHAN_AREA_MM2` (4mm²) is left alone and warned about instead of
   blindly milled, since something that large would indicate a real bug
   rather than this expected characteristic - confirmed this cutoff
   correctly separates the ~140mm² of genuinely small, legitimate leftover
   crumbs from the ~600mm² network-wide characteristic on this board.
4. **Un-simplified point-count blowup.** `cv2.findContours`'s
   `CHAIN_APPROX_NONE` keeps a vertex every ~0.01mm along any curve, and
   Shapely's `.buffer()` adds its own points on top of that - a real
   board's G-code ballooned to ~1M lines (~19x pcb2gcode's ~54k), and
   Snapmaker's own time estimate went from ~1h/side to ~7.5h/side.
   Simplifying each offset pass's own emitted ring independently was tried
   first and rejected: confirmed to erode the deliberate overlap margin
   between adjacent passes into real hairline gaps at some pad boundaries,
   since each pass's simplification error is uncorrelated with its
   neighbours'. Fixed by simplifying exactly once per shape, on the shared
   source before any buffering (`build_copper_polygons()`'s return line,
   and each orphan island in `find_orphan_islands()`) - every offset pass
   is then `buffer()`'d deterministically from the same fixed input, so
   their relationship to each other is exact regardless of the input's own
   coarseness. This alone did NOT fix the time estimate (still ~7.5h/side
   after a 14x point-count cut) - see defect 5.
5. **Rapid-travel blowup - the actual cause of the ~7.5h/side estimate.**
   ~2400 separate loops were emitted in whatever order Shapely's
   `unary_union`/`buffer` happened to produce (effectively arbitrary, not
   spatially sorted), producing ~20,000mm of G00 rapid travel alone on a
   real board - more than the ~14,800mm of actual cutting. Confirmed
   Snapmaker's own time estimator (Luban) charges G00 moves at the active
   cutting feedrate rather than a fast jog rate, so this unsorted travel
   dominated the estimate even after defect 4 was fixed. Fixed with a
   greedy nearest-neighbour reordering pass (`order_paths()`) - cut rapid
   travel to ~1430mm, close to pcb2gcode's own ~725mm on the same board.
   Also tried, and rejected: rotating each closed ring to start at its
   closest vertex to the incoming position (saves a little more travel in
   principle) measurably regressed real coverage instead (board-wide
   defect count 69→98, max size 0.315→0.947mm², all at new locations) -
   suspected cause is that `verify_isolation.py`'s thick-line rendering
   isn't perfectly seam-position-independent. Reordering alone recovers
   nearly all the travel benefit at zero correctness cost.

After all five fixes, extensive spot-checking (all four mounting holes on
both layers, the full ESP32 DevKitC header row, several vias and pads near
C4/D4/U5 including a 4-spoke thermal-relief pad) found no further defects -
each checked against both the raw per-pixel diagnostic and the
net-connectivity check (which distinguishes a real short from a merely
untidy-looking but harmless same-net connection - confirmed necessary
during this same investigation: a capacitor's GND pin with a
thermal-relief-style partial ring looks identical to a genuinely broken
isolation ring at a glance, and only the connectivity check tells them
apart).

**Back-layer mirroring** uses the same convention as mill.tcl/pcb2gcode
("flip like a page", about the board's own vertical centerline): the
back-layer copper SVG is exported already mirrored
(`kicad-cli ... --mirror`), so the copper geometry itself needs no special
handling; the only thing `--mirror` (this script's own flag) does is also
mirror the Excellon drill positions before matching them against that
already-mirrored copper mask, since a physical hole is the same from
either face and the drill file itself is never mirrored.

Drilling is NOT reimplemented here - `make mill` still runs pcb2gcode
purely for its milldrill output (discarding its isolation output, which
this generator replaces), since milldrilling hasn't shown any of the
isolation-specific bugs this investigation found and pcb2gcode's own
coordinate frame (with the x/y-offset correction from §7.1) is already
independently verified.

`make mill` now runs this generator by default; `make mill-pcb2gcode` and
`make mill-flatcam` both still work as explicit fallbacks.
