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
xy_clearance = 1.5;        // gap between PCB edge and inner wall, all sides
                            // (U2 was shifted right on the board so its USB-C
                            // end reaches the board's right edge - see session
                            // notes - which as a side effect pulled the
                            // antenna end fully inside the board too, so no
                            // extra left-side allowance is needed any more)

// standoff: cylindrical post from the ceiling down to the PCB's top surface,
// with a pilot hole for an M3 heat-set insert (common brass insert OD ~4.0-
// 4.2mm; using 4.2mm for an easy press-fit, 6mm deep so the insert doesn't
// bottom out against the ceiling)
standoff_od = 8;
insert_hole_d = 4.2;
insert_depth = 6;

// ---- Derived ----
inner_w = pcb_w + 2 * xy_clearance;
inner_h = pcb_h + 2 * xy_clearance;
outer_w = inner_w + 2 * wall_t;
outer_h = inner_h + 2 * wall_t;
shell_h = ceiling_t + component_clearance + pcb_t + 2;  // +2mm below the PCB's
                                                          // back side so solder
                                                          // joints/pad rings
                                                          // don't touch the
                                                          // mounting surface

// PCB origin, in shell coordinates: xy_clearance from the left/front walls'
// inner faces
pcb_x0 = wall_t + xy_clearance;
pcb_y0 = wall_t + xy_clearance;

// wire cutouts - generous per explicit instruction ("liberal, size-wise").
// NOTE: this must come after shell_h/ceiling_t are defined above - OpenSCAD
// resolves top-level scalar assignments in file order, not by dependency,
// so referencing shell_h here before its own definition silently produced
// undef (caught by rendering a cross-section and finding no cutouts at all,
// not by any error/warning).
cutout_h = shell_h - ceiling_t;  // exactly the open-interior height, so the
                                   // cutout perforates the wall without
                                   // touching the solid ceiling slab above it
cutout_z = wall_t + cutout_h / 2;  // vertical center of the open interior,
                                     // used to center round pass-through holes

// TB1+TB2 and TB3+TB4 are each wired with a single shared pigtail off-board
// (motor+supply, and handset, respectively - see README §6.4) - the screw
// terminals themselves stay fully internal, wired before the enclosure goes
// on, so they need no external access at all. Just a round pass-through per
// pigtail bundle, generously sized rather than fitted to a wire gauge.
// TB3/TB4 were relocated (session notes) to a right-side pocket to clear
// U2's USB edge, so their pigtail hole moves to the right wall with them;
// TB1+TB2's hole goes on the opposite (left) wall, clear of the antenna.
pigtail_hole_d = 10;

module wall_hole_x(y, z, from_left) {
    // round pass-through in the X direction (left or right wall)
    x0 = from_left ? -0.5 : outer_w - wall_t - 0.5;
    translate([x0, y, z])
        rotate([0, 90, 0])
            cylinder(d = pigtail_hole_d, h = wall_t + 1, $fn = 32);
}

// U2's USB-C cutout - a rounded rectangle (rounded corners per explicit
// request), built as the hull of four corner cylinders so it actually
// spans the wall's full penetration depth (x) as well as its height (y).
module rounded_wall_slot(x0, y0, depth, w, r) {
    hull() {
        for (dx = [r, depth - r])
            for (dy = [r, w - r])
                translate([x0 + dx, y0 + dy, -0.5])
                    cylinder(r = r, h = cutout_h + 1, $fn = 24);
    }
}

module shell() {
    difference() {
        cube([outer_w, outer_h, shell_h]);

        // hollow interior: cut from the open bottom (z=0) up to just below
        // the ceiling, leaving a solid ceiling_t slab at the top
        translate([wall_t, wall_t, 0])
            cube([inner_w, inner_h, shell_h - ceiling_t]);

        // TB1+TB2 shared pigtail (motor+supply): left wall, clear of the
        // antenna (which sits within U2's own PCB y:13.4-41.8 span)
        wall_hole_x(pcb_y0 + 6, cutout_z, true);

        // TB3+TB4 shared pigtail (handset): right wall, near their actual
        // relocated position (PCB y:42.8-70)
        wall_hole_x(pcb_y0 + 56, cutout_z, false);

        // U2 USB-C: connector overhangs the PCB's own x=70 edge by ~2.5mm
        // near pins 22/23 -> right wall, positioned within U2's PCB
        // y:13.4-41.8 span (below the antenna end, above TB3/TB4's new
        // spot), widened per "liberal" instruction
        rounded_wall_slot(outer_w - wall_t - 1, pcb_y0 + 17, wall_t + 2, 20, 1.2);
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
