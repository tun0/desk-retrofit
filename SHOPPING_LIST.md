# Shopping list

Purchase-ready BOM. Check off as ordered — don't delete rows.

## Resistors (THT, 1/4W unless noted)

- [x] 10k — qty 4 (R8, R9, R1, R10)
- [x] 20k — qty 1 (R2)
- [x] 100k — qty 3 (R7, R5, R6)
- [x] 4k7 — qty 2 (R3, R4)
- [x] 1k — qty 1 (R11)

## Capacitors (THT)

- [x] 220µF, ≥50V — qty 1 (C4)
- [x] 220µF, ≥10V — qty 1 (C5)
- [x] 2.2µF — qty 1 (C1)
- [x] 100nF (0.1µF), ≥10V — qty 1 (C2)
- [x] 1nF — qty 1 (C3)

## Diodes

- [x] 1N4148, DO-35 — qty 2 (D2, D3)
- [ ] SB560, DO-201AD axial — qty 1 (D1), order 5
- [ ] TVS, 33V bidirectional (`P6KE33CA` or `1.5KE33CA`, axial) — qty 1 (D4), order 5

## Current sensor

- [ ] ACS712ELCTR-05B, SOIC-8 — qty 1 (U4), order 3
- [ ] DIP-8 IC socket, 0.3"/7.62mm — qty 1, order 5

## Transistors

- [ ] 2N7000, TO-92 — qty 2 (Q3, Q4), order 10
- [x] BC337, TO-92 — qty 1 (Q1)
- [x] BC327, TO-92 — qty 1 (Q2)
- [ ] IRLZ44N, TO-220 — qty 1 (Q5), order 3. **Not IRLB8721** (30V VDSS too low for this rail).

## ICs (THT/DIP)

- [ ] 74HC123N / SN74HC123N, DIP-16 — qty 1 (U2), order 3. **Must be retriggerable** — not 74HC221.
- [ ] DIP-16 IC socket, 0.3"/7.62mm — qty 1, order 5
- [ ] SN74HC08N, DIP-14 — qty 1 (U3), order 3
- [ ] DIP-14 IC socket, 0.3"/7.62mm — qty 1, order 5

## Buck regulator

- [ ] LM2576HVS-5.0/NOPB, TO-263-5 SMD — qty 1 (U5), order 2. Must be the true **HV** variant.

## Relays

- [ ] Omron `G5LE-1-5VDC`, SPDT/Form-C, 5V coil, 10A/250VAC-30VDC — qty 2 (K1, K2), order 4

## Board-side terminals

- [x] 2-position screw terminal, 2.54mm pitch — qty 5 (TB1-TB5), order 8. Degson `DG308-2.54-02P-14-00A(H)`.

## Modules

- [x] ESP32-S3-DevKitC — qty 1 (U1). Row spacing 25.4mm (1") — verify against the unit received.
- [x] 2× 2.54mm-pitch female header, 1×22 position (sockets U1) — covered by inventory.

## Connectors (Molex Mini-Fit Jr., 4-circuit)

- [x] Receptacle housing, 4-circuit — Molex `39-01-2040` — qty 2
- [x] Plug housing, 4-circuit — Molex 5559-04P — qty 2
- [x] Female crimp terminal, 5556 series — qty 8
- [x] Male crimp terminal, 5558 series — qty 8

Also needed: crimp tool, wire for the two pigtails + coupler (20-22 AWG).

## PCB / CNC

- [ ] 150×100mm copper-clad blank, double-sided, 1.5mm — pack of 5 (sourcing map, Amazon.nl `B07RFRVTGB`)
- [ ] CNC V-bit, 1/8" shank, 15° — Genmitsu `70V15` (Amazon.nl `B07P99C2FH`)
- [ ] Flat-nose end mill, 1/8" shank — Genmitsu `FN10A`-family (Amazon.nl `B07P7LGQJ6`)
- [ ] DIP IC socket assortment, 66pcs, 6-28 pin — Amazon.nl `B0C442NFWC` (covers the DIP-8/14/16 sockets above)
- [ ] M3 hardware for corner mounting holes (H1-H4, 3.2mm NPTH) — hold off until enclosure is finalized

## Not purchased (already exists / out of scope)

- PS1, M1, SW1/SW2, D5/D6 — inside the existing motor housing/leg
- Phase 2 parts (VL53L1X carrier + bracket) — not started
