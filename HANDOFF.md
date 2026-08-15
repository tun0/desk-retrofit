# Handoff — changes to apply to `desk-retrofit`

These came out of a claude.ai session working alongside you. Apply them on top
of whatever is currently in the repo; rebase rather than assuming the tree
matches what that session last saw.

Ground rules that already exist in `CLAUDE.md`, repeated because they matter
for every item below:

- **Never edit `.kicad_sch` directly.** Edit `schematics/sch_*.py` and
  regenerate.
- **Run `cd schematics && make sch && make verify` after any schematic
  change.** UUID generation is deterministic, so `verify` is an exact drift
  check and must report OK for all three sheets before committing.
- Record *why*, not just what. `README.md` §5 is the corrections list; add to
  it when a decision reverses.

---

## 1. Replace 2N7002 with 2N7000 (through-hole)

**Files:** `schematics/sch_simple.py`, `schematics/sch_inline.py`,
`README.md` BOM.

`Q2`/`Q3` (relay coil drivers) are specified as **2N7002**, which is SOT-23
only. This project is deliberately all through-hole for protoboard assembly.

Replace with **2N7000** (or BS170) in TO-92: logic-level gate, 60 V, 200 mA
continuous, comfortable against ~70 mA relay coils. Drop-in, no other changes.

---

## 2. Record the 74HC122 investigation as a negative result

**File:** `APPENDIX.md` §5 (rejected alternatives).

The single-channel 74x122 was considered as a replacement for the dual
74HC123 in the watchdog. It is functionally the better fit — single
retriggerable monostable with overriding clear, and its **internal 10k timing
resistor would eliminate R3**, leaving only C3.

**It is discontinued in the HC family.** Verified: searches for an HC122
datasheet return the HC123 instead, and no current NXP or TI HC122 part page
exists. The '122 survives as 74LS122 only, and dragging a TTL part into an
otherwise HC design buys nothing.

**Decision: retain 74HC123.** Record this so the question is not reopened and
re-researched later.

Also note **CD4538** (dual precision retriggerable monostable) as the
alternative if timing tolerance ever matters — the HC123's timing spread is
famously loose. It does not matter for a 250 ms watchdog, which only needs to
sit comfortably above the 50 ms kick interval and below "dangerous".

And note that **74x121 and 74x221 will not work** — they are non-retriggerable
one-shots.

---

## 3. Propose a use for the spare half of the 74HC123

**File:** `APPENDIX.md` (future work). **Do not wire this into the schematic
without discussion** — it is a design change, not a documentation fix.

The 74HC123 is dual and only one channel is used. The spare could provide a
**second, independent hardware timeout**: a ~30 s monostable retriggered by
"any drive line active", hard-limiting continuous run.

Why it is attractive: the travel timeout is currently a firmware property
(`max_run_ms`), so it dies with the firmware. Moving it into hardware makes
maximum continuous run a property the MCU cannot override, complementing the
existing watchdog. It also enforces the manual's duty-cycle limit against a
firmware bug rather than trusting firmware to enforce it.

---

## 4. Note the through-hole constraint in the BOM

**File:** `README.md` §6.

Add that the design is **deliberately all through-hole** for protoboard
assembly, and list the packages so substitutions preserve it:

| Part | Through-hole option |
|---|---|
| 74HC123 | `74HC123N` / `SN74HC123N`, DIP-16 |
| 74HC08 | `SN74HC08N`, DIP-14 |
| TC4427 | `TC4427CPA`, DIP-8 |
| IRLZ44N | TO-220 |
| 2N7000 | TO-92 |
| SB560 | DO-201AD axial |
| TVS 33 V | `P6KE33CA` or `1.5KE33CA`, axial |
| Coil flyback | `1N4148`, DO-35 |
| ACS724 | Pololu carrier (0.1" holes) — the bare chip is SOIC-8 |
| Buck / ESP32 / relays | modules with headers |

The ACS724 is the one part where the carrier, rather than the chip, is what
keeps the board through-hole. Note that trade-off explicitly.

---

## 5. Record sourcing constraints (Netherlands)

**File:** `README.md` §6, near the existing sourcing paragraph.

Ruled out, with reasons, so they are not re-evaluated:

- **Digikey** — ~€25 shipping on small orders.
- **Farnell** — €50 order minimum, even after a reduction.

Working pattern is **two orders**:

- **Jellybean components** — Reichelt (DE) or TME (PL). Both ship to NL for
  single-digit shipping with no minimum. TME has the deeper catalogue.
- **Modules** — TinyTronics (Ede), Kiwi Electronics, Opencircuit (Zaandam) or
  Antratek. Kiwi and Antratek carry Pololu, which matters for the ACS724
  carrier.

**Mouser is being evaluated** as a possible single-order option — its European
free-shipping threshold may be low enough to cover the whole BOM including the
bare ACS724. Leave this marked as open; do not write it up as decided.

Substitutes worth recording:

- **TC4427** → TC4420, MCP1407, UCC27517, or a discrete totem-pole. Any driver
  sourcing a few hundred mA works; the arithmetic is in `APPENDIX.md` §1.5.
- **IRLZ44N** → any 55–60 V logic-level N-channel in TO-220. Check **Qg and
  VDSS**, not Vgs(th).
- **74HC08** → 74HC00 with inverted logic, or 74HC11 triple 3-input AND.
- **ACS724 carrier** → 10 mΩ shunt + INA240, but INA240 is SOIC-8 and needs a
  breakout, which fights the through-hole preference.

---

## 6. Pin down the current sensor specification

**File:** `README.md` §6, and `APPENDIX.md` §1.2 if useful.

"ACS724" alone is **not a specification** — prices vary ~5x because the name
spans a bare SOIC-8 chip, a carrier board, five current ranges, and
unidirectional vs bidirectional variants. Buying the wrong one degrades
collision detection quietly rather than visibly.

Two requirements:

- **Bidirectional (`AB` suffix).** Current reverses when the relays flip. A
  unidirectional `AU` part reads zero for one direction of travel.
- **5 A range**, not 20 A or 30 A. Sensitivity scales inversely and the
  working span is 0–3 A.

| Part | Sensitivity | Swing over 0–3 A |
|---|---|---|
| ACS724-5AB | 400 mV/A | 1.2 V |
| ACS712-05B | 185 mV/A | 0.55 V |
| ACS712-20A | 100 mV/A | 0.30 V |
| ACS712-30A | 66 mV/A | 0.20 V |

Cheap €2 modules are nearly always 20 A or 30 A. At 66 mV/A an obstruction has
to be detected inside 200 mV of a noisy ADC range.

Options: Pololu ACS724 5 A bidirectional carrier (€10–15); bare
`ACS724LLCTR-05AB-T` on a SOIC-8 breakout (~€5, 1.27 mm pitch is hand-solderable);
or an **ACS712-05B** module (€2–4) as a budget fallback — older and noisier,
but adequate with averaging in a 200 Hz loop, *provided it is the 5 A version*.

Warn about clone modules labelled ACS724 that are actually ACS712, and about
automotive `KMA` variants that cost more for no benefit here.

---

## 7. Confirm two earlier fixes are present

Both were made in the claude.ai session; verify they survived into the repo
rather than assuming.

- **`Q1` must be `IRLZ44N` (55 V), not `IRLB8721`.** The IRLB8721 is a 30 V
  part on a 29 V nominal / 30 V unloaded rail; at PWM turn-off the freewheel
  diode clamps the drain to VSW plus a diode drop, putting it at or over its
  absolute maximum every cycle. `README.md` §6.2 should lead with the voltage
  rating and give the substitution criterion as Qg and VDSS.
- **`schematics/symbols.py` exists and no generator uses `exec()`.** All three
  generators should resolve paths from `__file__`, and `make verify` should
  pass.

---

## Not yet decided — do not write these up as settled

- Mouser single-order viability (item 5).
- Final current sensor choice between the Pololu carrier, a bare chip on a
  breakout, and an ACS712-05B module (item 6).
- Whether to actually implement the second hardware timeout (item 3).
