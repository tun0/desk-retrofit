// Single open-bottom shell for desk.kicad_pcb (70x100mm, 2-layer).
//
// The PCB hangs from four standoffs cast into the ceiling, component side
// up, secured by M3 screws driven up from below into heat-set inserts.
// There is no separate floor/lid - the open bottom is meant to close off
// against whatever flat surface this gets mounted to (see README §6 for
// the board itself; this is a new, separate concern from the PCB design).
//
// All dimensions measured directly from schematics/desk.kicad_pcb via the
// pcbnew Python API, not eyeballed from the PDF/SVG render - see the
// session history for exactly how (courtyard-bbox queries per footprint).
// Re-measure and update these if the board is ever revised.

// ---- PCB ----
pcb_w = 70;
pcb_h = 100;
pcb_t = 1.6;              // standard FR4 thickness

// H1-H4: 3.2mm NPTH, 4mm inset from each corner (commit 62d88ca)
hole_inset = 4;
hole_d = 3.2;

// ---- Component clearance ----
// Tallest parts are all THT and none have a confirmed datasheet height in
// this project's docs - this is an estimate, not a measurement:
//   - K1/K2 (SRD-05VDC-SL-C relay): ~16mm typical for this package
//   - U2 (ESP32-S3-DevKitC): pin socket (~8.5mm) + devkit PCB (~1.6mm) +
//     tallest part on the devkit itself (module/connector, ~3.5mm) = ~14mm
//   - Q1/U1 (TO-220, upright): ~10-14mm depending on lead bend
//   - C1/C2 (220uF radial electrolytic): commonly 12.5-16mm tall
// Using 16mm + 3mm safety margin. Cheap to revise once real parts are in
// hand (see SHOPPING_LIST.md) - this is the single number to change.
component_clearance = 19;

// ---- Shell geometry ----
wall_t = 2.4;              // FDM-friendly - 2 perimeters at a common 0.4mm/1.2mm nozzle
ceiling_t = 2.4;
xy_clearance = 1.5;        // gap between PCB edge and inner wall, most sides
left_clearance = 8;        // extra on the left: U2's USB-C connector overhangs
                            // the PCB's own left edge by ~2mm (pin1/44 sit at
                            // x=3.9mm on the board - see session notes) and
                            // needs room to plug in a cable beyond that

// standoff: cylindrical post from the ceiling down to the PCB's top surface,
// with a pilot hole for an M3 heat-set insert (common brass insert OD ~4.0-
// 4.2mm; using 4.2mm for an easy press-fit, 6mm deep so the insert doesn't
// bottom out against the ceiling)
standoff_od = 8;
insert_hole_d = 4.2;
insert_depth = 6;

// ---- Derived ----
inner_w = pcb_w + left_clearance + xy_clearance;
inner_h = pcb_h + 2 * xy_clearance;
outer_w = inner_w + 2 * wall_t;
outer_h = inner_h + 2 * wall_t;
shell_h = ceiling_t + component_clearance + pcb_t + 2;  // +2mm below the PCB's
                                                          // back side so solder
                                                          // joints/pad rings
                                                          // don't touch the
                                                          // mounting surface

// PCB origin, in shell coordinates: left_clearance from the left wall's
// inner face, xy_clearance from the front wall's inner face
pcb_x0 = wall_t + left_clearance;
pcb_y0 = wall_t + xy_clearance;

// wire/USB cutouts - generous per explicit instruction ("liberal, size-wise")
// rather than tightly matched to connector bodies. Positions are the real
// PCB-edge span of each connector (see session notes), expanded outward.
// NOTE: this must come after shell_h/ceiling_t are defined above - OpenSCAD
// resolves top-level scalar assignments in file order, not by dependency,
// so referencing shell_h here before its own definition silently produced
// undef (caught by rendering a cross-section and finding no cutouts at all,
// not by any error/warning).
cutout_h = shell_h - ceiling_t;  // exactly the open-interior height, so the
                                   // cutout perforates the wall without
                                   // touching the solid ceiling slab above it

module cutout(x, y, w) {
    translate([x, y, -0.5])
        cube([w, wall_t + 1, cutout_h + 1]);
}

module shell() {
    difference() {
        cube([outer_w, outer_h, shell_h]);

        // hollow interior: cut from the open bottom (z=0) up to just below
        // the ceiling, leaving a solid ceiling_t slab at the top
        translate([wall_t, wall_t, 0])
            cube([inner_w, inner_h, shell_h - ceiling_t]);

        // TB2 (supply pair): near PCB y=0 edge, x:7.5-16.4 -> front wall (y=0)
        cutout(pcb_x0 + 6, -0.5, 12);

        // TB1 (motor pair): near PCB y=100 edge, x:36.4-47.9 -> back wall
        cutout(pcb_x0 + 35, outer_h - wall_t - 0.5, 14);

        // TB3+TB4 (signal + power pairs): near PCB x=70 edge, y:13.4-37.5
        // combined -> right wall (x=outer_w)
        translate([outer_w - wall_t - 0.5, pcb_y0 + 12, -0.5])
            cube([wall_t + 1, 26, cutout_h + 1]);

        // U2 USB-C: overhangs PCB's own x=0 edge; pin1/44 span y:14.9-40.3
        // on the board -> left wall (x=0), widened per "liberal" instruction
        translate([-0.5, pcb_y0 + 8, -0.5])
            cube([wall_t + 1, 30, cutout_h + 1]);
    }

    // four standoffs, hanging from the ceiling underside down to the PCB's
    // top (component) surface
    for (pos = [[hole_inset, hole_inset],
                [pcb_w - hole_inset, hole_inset],
                [hole_inset, pcb_h - hole_inset],
                [pcb_w - hole_inset, pcb_h - hole_inset]]) {
        translate([pcb_x0 + pos[0], pcb_y0 + pos[1], shell_h - ceiling_t - component_clearance]) {
            difference() {
                cylinder(d = standoff_od, h = component_clearance, $fn = 32);
                // pilot hole for the heat-set insert, opening from the
                // PCB-facing (bottom, z=0 local) end - the screw drives up
                // from below the PCB into this
                cylinder(d = insert_hole_d, h = insert_depth + 0.5, $fn = 24);
            }
        }
    }
}

shell();
