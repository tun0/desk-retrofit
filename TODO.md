# TODO

Working list of what's outstanding. Not a durable doc like `README.md` /
`APPENDIX.md` — check items off once done or superseded, don't delete them.

## Schematic layout (schematics/sch.py)

- [x] **Snap all coordinates to KiCad's grid.** Done in `schlib.py`
  (`GRID`/`_snap`/`_snap_pt`, applied in `wire`, `place`, `pin`, `junction`).
- [x] **J2 (motor housing connector) placement/routing.** Settled — see
  `sch.py`.
- [x] **Rocker divider cluster (R11/R13/R14/R15) + J3 (handset connector).**
  Settled — see `sch.py`.
- [x] Re-run the full detector suite (diagonals / shorts / crossings /
  body-crossings). Now persisted as `schematics/gen/find_*.py`, run via
  `make check`. Found one bug in the checker itself (diagonals false
  positives from checking pre-snap coordinates), fixed; the 15
  crossings/6 body-crossings that remain are legitimate unconnected
  crossings and cosmetic-only body proximity, not defects.
- [x] Full visual re-render/review of `desk`. Done (task #11).

## Deferred ideas

- [x] Consider replacing hand-drawn symbols (`schlib.py`/`symbols.py`) with
  real local KiCad libraries where cleaner ones exist. Done — tasks #1-10
  migrated relays, logic ICs, MCU, connectors, passives and power flags to
  real KiCad library parts.

## From HANDOFF.md — not yet applied

Came out of a separate claude.ai session; ground rules and full detail are in
that file. Titles only, for a quick glance:

- [ ] 1. Replace 2N7002 with 2N7000 (through-hole)
- [ ] 2. Record the 74HC122 investigation as a negative result
- [ ] 3. Propose a use for the spare half of the 74HC123
- [ ] 4. Note the through-hole constraint in the BOM
- [ ] 5. Record sourcing constraints (Netherlands)
- [ ] 6. Pin down the current sensor specification
- [ ] 7. Confirm two earlier fixes are present
- [ ] (see "Not yet decided" section at the end of HANDOFF.md too)

## Known gaps (already tracked in CLAUDE.md "Open work")

- [x] ERC has never been run on any schematic. Run this session (task #11):
  127 violations, all triaged as documented gaps or convention artefacts.
- [ ] Relay module active-high vs active-low polarity is unverified.
- [ ] `read_current_()` in `desk_cover.cpp` is a stub (IDF 4.x vs 5.x ADC call).
- [ ] Phase 2 (position feedback, presets) not started.
