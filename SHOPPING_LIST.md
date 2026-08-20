# Shopping list

Purchase-ready, itemized version of the BOM in `README.md` §6, with exact
passive values/quantities pulled from `schematics/NETLIST.md`'s component
table (README's own BOM lumps all passives into one line). Grouped by
supplier per README §6.6's sourcing plan. Check off as ordered — don't
delete rows, this doubles as a build-readiness tracker.

**Stale relative to this list:** README §6 ("Protoboard, terminals, wire —
€10-15") and §6.5's "Protoboard assembly, not a PCB house order" framing
both predate this project's pivot to a milled PCB (see git history on the
`u2-onboard`→`main` merge). The through-hole *constraint* in §6.5 still
holds — everything below is still THT — but the assembly method it assumes
is out of date. Worth a README update at some point; not done here since
it's a separate editorial pass, not a shopping decision.

## Reichelt / TME (jellybeans + basic semis)

Per README §6.6: single-digit shipping to NL, no order minimum. TME has the
deeper catalogue if a part isn't at Reichelt.

### Resistors (THT, 1/4W unless noted)

- [ ] 10k — qty 4 (R1, R2, R4, R6)
- [ ] 20k — qty 1 (R5)
- [ ] 100k — qty 3 (R3, R13, R15)
- [ ] 4k7 — qty 2 (R11, R14)
- [ ] 1k — qty 1 (R7)

### Capacitors (THT)

- [ ] 220µF, **≥50V** — qty 1 (C1, input bulk cap — rail is 29V nominal/30V
      unloaded, do not substitute a lower-voltage part here)
- [ ] 220µF, 10V (or higher) — qty 1 (C2, +5V rail, voltage headroom is not
      the concern here, any ≥10V part is fine)
- [ ] 2.2µF — qty 1 (C3, watchdog timing — see README/APPENDIX for why
      74HC123 timing tolerance doesn't matter for this application)
- [ ] 100nF (0.1µF), ≥10V — qty 1 (C4, ACS724 VCC bypass — added when the
      Pololu carrier that used to provide this was dropped, see README §6.5)
- [ ] 1nF — qty 1 (C5, ACS724 FILTER-to-GND — same reason as C4)

### Diodes

- [ ] 1N4148, DO-35 — qty 2 (D2, D6 — relay coil flyback)
- [ ] SB560, DO-201AD axial — qty 1 (D5 — main FET freewheel)
- [ ] TVS, 33V bidirectional (`P6KE33CA` or `1.5KE33CA`, axial) — qty 1 (D1
      — input transient protection; **no fuse fitted by design**, see
      README §6.1 before "fixing" that)

### Current sensor (bare chip, no carrier)

- [ ] ACS724xLCTR-05AB, SOIC-8 — qty 1 (U5, current sensor). Bidirectional,
      5A range. **Not the Pololu carrier** — mounted bare on a generic
      SOIC-8-to-DIP-8 adapter instead (0.3"/7.62mm row spacing, already in
      inventory — see README §6.5). C4/C5 above replace the two caps the
      Pololu carrier used to provide. Fallback if the chip itself is
      unavailable: 10mΩ shunt + INA240 (SOIC-8, needs its own breakout too).

### Transistors

- [ ] 2N7000, TO-92 — qty 2 (Q2, Q3 — relay coil drivers)
- [ ] BC337, TO-92 — qty 1 (Q4 — push-pull NPN half)
- [ ] BC327, TO-92 — qty 1 (Q5 — push-pull PNP half)
- [ ] IRLZ44N, TO-220 — qty 1 (Q1 — main PWM FET). **Not IRLB8721** — its
      30V VDSS doesn't clear this rail. If substituting, check **Qg and
      VDSS**, not Vgs(th) — see README §6.2.

### ICs (THT/DIP)

- [ ] 74HC123N / SN74HC123N, DIP-16 — qty 1 (U3 — watchdog monostable)
- [ ] SN74HC08N, DIP-14 — qty 1 (U6 — AND gating)
- [ ] LM2596HV, TO-220-5 — qty 1 (U1 — buck regulator. **Must be the HV
      variant, rated >40V in** — the base LM2596 tops out at 40V-ish and
      this rail is 29-30V nominal with headroom needed above it)

### Relays

- [ ] SRD-05VDC-SL-C (or equivalent EN50005/Form C bare relay) — qty 2
      (K1, K2). Check **coil voltage (5V)**, **contact rating** (10A
      250VAC/30VDC — cold-switched only, see CLAUDE.md hard invariants),
      and **pinout** (EN50005/Form C) before substituting — see README §6.3.

### Board-side terminals

- [ ] 2-position screw terminal, 2.54mm pitch — qty 4 (TB1-TB4)

## Modules (TinyTronics / Kiwi Electronics / Opencircuit / Antratek)

- [ ] ESP32-S3-DevKitC — qty 1 (U2). Bare devkit, **no display** (see
      README §5/§6). Row spacing on this design's footprint is confirmed
      at **25.4mm** (1"), measured against a real board — verify against
      whatever unit you actually receive before assembly; some DevKitC
      variants use narrower 22.86mm spacing (see `symbols.py` for the full
      story on this).

## Connectors (Molex Mini-Fit Jr., 4-circuit)

Supplier not pinned down in README — TME's "deeper catalogue" comment
(§6.6) makes it worth checking first; otherwise a dedicated connector
distributor. Full ordering gotcha (5557 vs 5566/5569 mating-housing trap)
is in README §6.4 — **order by the terminals, not the housing shape.**

- [ ] Receptacle housing, 4-circuit — Molex `39-01-2040` (legacy 5557-04R)
      — qty 2 (one per mating pair — motor housing side + a spare for the
      revert-path coupler, see README §6.4)
- [ ] Plug housing, 4-circuit — Molex 5559 series, 5559-04P — qty 2 (same
      reasoning — handset side + spare coupler half)
- [ ] Female crimp terminal, 5556 series — qty 8 (4 circuits × 2 housings)
- [ ] Male crimp terminal, 5558 series — qty 8

**Also needed, not orderable as a part:** crimp tool (if not already
owned), and wire for the two pigtails + coupler (20-22 AWG recommended
over stiff 18 AWG PC cable, see README §6.4). Board-to-Mini-Fit pigtails
terminate at TB1-TB4 above, not at a board-mounted connector.

## PCB-specific (new this session, not in README's original BOM)

- [ ] **70×100mm pre-cut copper-clad blank, double-sided (2-layer)** — the
      board (`schematics/desk.kicad_pcb`) is sized to this exact standard
      blank size deliberately (see commit `9a7fce9`). No specific supplier
      identified yet — common sources are general electronics/hobby
      suppliers or eBay/AliExpress for blank copper-clad stock. Confirm
      it's actually pre-cut to size (not a larger sheet) — the board's
      edge-copper clearance was set assuming no outline-milling step (see
      commit `9a7fce9`'s reasoning); if you end up cutting it down
      yourself instead, some traces may sit closer to the new edge than
      that assumption allows.
- [ ] M3 hardware for the four corner mounting holes (`H1`-`H4`,
      3.2mm NPTH, see commit `62d88ca`) — **screw length and any
      standoffs/nuts depend on the enclosure design, not yet done.**
      Hold off ordering until that's settled.

## Not purchased (already exists / out of scope here)

- PS1 (29V/1.8A wall supply), M1 (motor), SW3/SW4 (limit switches),
  D3/D4 (leg bypass diodes) — all inside the existing, unmodified motor
  housing/leg (NETLIST.md "Leg" section).
- Phase 2 parts (VL53L1X carrier + bracket, ~€15-25) — not started, see
  README §8.
