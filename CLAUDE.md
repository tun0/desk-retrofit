# Desk retrofit — working context

Reverse-engineered replacement drive for a **Jysk Slangerup** electric
standing desk. Soft start/stop under an ESP32, replacing a stock design that
has no control electronics at all.

`README.md` is the full record: measurements, why each design was rejected,
and the mistakes made along the way. **Read the relevant section before
changing anything in that area** — most of the non-obvious decisions have a
measurement behind them, and several are only correct because an earlier
answer was wrong.

`APPENDIX.md` holds background, rejected alternatives and future work. Nothing
in it is needed to build the current design. **Check it before proposing an
approach or changing a parameter that looks arbitrary** — several obvious
ideas were already tried and rejected for reasons that are not obvious.

Do not read either file in full by default. Section map:

| Need | Section |
|---|---|
| Connector, pinout, polarity | §1.5, §1.6 |
| What was measured and what it proved | §2 |
| Why the other three designs lost | §3 |
| The chosen design | §4 |
| **Wrong turns — read before re-deriving anything** | §5 |
| Part selection traps | §6 |
| Firmware architecture | §7 |
| Position sensing (not yet built) | §8, and APPENDIX §2 |
| Collision detection, PWM, sensing detail | APPENDIX §1 |
| **Already-rejected approaches** | APPENDIX §5 |
| Schematic tooling and its dead ends | APPENDIX §7 |

## Hard invariants

These are safety properties, not preferences. Do not remove or "simplify"
them without explicit discussion.

1. **The watchdog gates drive downstream of the MCU.** A 74HC123 monostable
   feeds a 74HC08 that gates all three drive lines. LEDC PWM keeps running in
   hardware after a firmware hang, so stopping PWM in software is not a safety
   measure. The kick must come from the completed control loop, never a timer.
2. **Relays change state only with the FET off and current decayed (~50 ms).**
   Every direction change routes through `SETTLING`. Relay writes are legal in
   `IDLE` only. This is enforced structurally in the state machine — keep it
   that way.
3. **Do not fit a larger PSU.** The stock 29 V / 1.8 A supply current-limits,
   and that limit is the desk's only collision protection. The motor's thermal
   rating was chosen around it.
4. **Boot state is defined by hardware.** R1/R2/R6 hold the drive lines safe
   before firmware runs. They must stay on non-strapping GPIOs.
5. **ISENSE must be on ADC1.** ADC2 is unusable while WiFi is active.

## Conventions

- **`MOT_A` is the conductor that must be POSITIVE to raise the desk**
  (connector circuit 2). `MOT_B` is circuit 1. Defining it by function means
  the schematic is correct by construction.
- **K1 = up, K2 = down.** Chain: `DIR_A → U8 → Q2 → K1 = up`. This matches
  `relay_up:` / `relay_down:` in `desk.yaml`. If the relay assignment ever
  changes, the YAML keys must change with it.
- **Both relays off = brake** (both winding ends on VSW), matching the OEM
  rest state. This is also the boot state and the watchdog-timeout state.
- Connector circuit numbering is a **project-local convention** defined by the
  README §1.6 diagram. The housings have no legible moulded numbers, and Molex
  numbering may differ. Never assume it matches a datasheet or a bought cable.

## Measured constants

Do not re-derive these; they were measured on the actual desk.

| | |
|---|---|
| Supply | 29.0 V, 1.8 A, 52.2 W (current-limiting) |
| Winding | 2.5 Ω, single motor, shaft to second leg |
| Travel | 500 mm, ~25 mm/s |
| Duty cycle | 10% at half load, or 2 min continuous |
| End stops | diode-bypassed limit switches, in the leg, passive |
| Connector | Molex Mini-Fit Jr., 4.20 mm, 4 circuit dual row |

## Layout

```
APPENDIX.md    background, rejected alternatives, phase-2 analysis
schematics/    KiCad 7 format, symbols embedded, no external libs
               desk.kicad_sch/.pdf/.svg  <- the design, human-facing
                                  (rejected variants dropped once this was
                                  finalised — see APPENDIX §7)
               NETLIST.md      <- connectivity reference, human-facing
               gen/            <- generator + its dependencies (machine-facing)
                 sch.py            <- the generator
                 schlib.py         <- drawing primitives
                 symbols.py        <- shared symbol library (see below)
                 espressif.kicad_sym <- vendored ESP32 symbol (see its header)
                 netlist_text.py   <- renders a .kicad_sch as plain text
                 find_*.py         <- schematic-quality checkers, run via `make check`
                 Makefile          <- `make` regenerates .kicad_sch/.pdf/.svg
my_components/desk/   ESPHome external component (cover platform)
desk.yaml             example ESPHome config
```

**Schematics are generated, not hand-edited.** Edit `schematics/gen/sch.py`
and re-run; do not edit the `.kicad_sch` directly or the change is lost.

```sh
cd schematics/gen && make        # regenerate desk.kicad_sch/.pdf/.svg
cd schematics/gen && make check  # run the shorts/diagonals/crossings/body-crossings checkers
```

`make` regenerates `../desk.kicad_sch`/`.pdf`/`.svg` if the generator changed.
The `.kicad_sch` target is marked `.PRECIOUS` in the Makefile — without that,
GNU Make treats it as a disposable intermediate in the `.py → .kicad_sch →
.pdf` chain and deletes it after export, which would delete a tracked file.
Don't remove that line.

## Open work

- `read_current_()` in `desk_cover.cpp` is a stub. The ADC call differs
  between IDF 4.x and 5.x — that is the one place to adapt.
- Phase 2 (position feedback, presets) is not started. See README §8.

## Working style

- This project's value is in the reasoning, not the artefacts. When a decision
  changes, update `README.md` with **why**, including what was believed before.
  §5 exists because several conclusions only make sense against an earlier
  wrong answer.
- Prefer stating what is measured versus what is inferred. The README is
  careful about that distinction; keep it.
