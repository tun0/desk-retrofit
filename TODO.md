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

- [x] 1. Replace 2N7002 with 2N7000 (through-hole). Done — `sch.py` Q2/Q3
  now `2N7000`; added the missing BOM row (README §6).
- [x] 2. Record the 74HC122 investigation as a negative result. Done —
  `APPENDIX.md` §5.7.
- [x] 3. Propose a use for the spare half of the 74HC123. Written up as a
  proposal (not implemented, per HANDOFF's own instruction) in
  `APPENDIX.md` §1.6: a second, hardware-enforced ~30s continuous-run
  timeout.
- [x] 4. Note the through-hole constraint in the BOM. Done — `README.md`
  §6.5, adapted for parts that changed since HANDOFF was written (TC4427
  dropped, replaced by the already-through-hole discrete BC337/BC327).
- [x] 5. Record sourcing constraints (Netherlands). Done — `README.md`
  §6.6 (Digikey/Farnell ruled out with reasons, two-order pattern,
  Mouser left open, substitutes list). TC4427 substitute dropped, not
  applicable since the driver is discrete BC337/BC327 now.
- [x] 6. Pin down the current sensor specification. Already decided in the
  schematic, just not narrated where HANDOFF looked: `symbols.py` imports
  `ACS724xLCTR-05AB` for U5 (bidirectional, 5A range — exactly HANDOFF's
  two requirements), and README §4.4 already assumes this part. HANDOFF's
  "Not yet decided" framing was stale relative to the repo.
- [x] 7. Confirm two earlier fixes are present. Half held, half didn't:
  `symbols.py` exists and no generator uses `exec()` — confirmed OK. Q1
  was still `IRLB8721` (30V) on the 29-30V rail, not `IRLZ44N` (55V) as
  the earlier session intended — genuinely hadn't survived into the repo.
  Fixed now (`sch.py`, README §6.2/§5 item 9).
- [ ] (see "Not yet decided" section at the end of HANDOFF.md too — stale
  on item 6, see above; items 3 and 5's Mouser question still genuinely open)

## Known gaps (already tracked in CLAUDE.md "Open work")

- [x] ERC has never been run on any schematic. Run this session (task #11):
  127 violations, all triaged as documented gaps or convention artefacts.
- [ ] Relay module active-high vs active-low polarity is unverified.
- [ ] `read_current_()` in `desk_cover.cpp` is a stub (IDF 4.x vs 5.x ADC call).
- [ ] Phase 2 (position feedback, presets) not started.
