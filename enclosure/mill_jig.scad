// Registration jig for milling desk.kicad_pcb on the Snapmaker A350's CNC
// module. Bolts to the machine's bed grid; holds the pre-cut 70x100x1.5mm
// copper-clad blank (SHOPPING_LIST.md - the same size as the board itself,
// not an oversized sheet needing a separate cutout pass) in a snug pocket
// so the blank re-registers correctly when flipped over between the front
// and back isolation passes.
//
// Software/hardware convention this jig depends on (see mill.tcl):
//   - mill.tcl offsets every Gerber object so the board outline lands flush
//     with the blank's own edges, occupying job-space X:[0,70] Y:[0,100]
//     exactly - not eyeballed, computed from the board outline's own
//     measured bounds.
//   - The physical flip is left-right about the blank's own vertical
//     centerline, like turning a page (not top-to-bottom). A plain
//     rectangular pocket sized to the blank reproduces the exact same
//     footprint after this specific flip - proven by construction: mirroring
//     a rectangle about its own center exactly retraces its own outline.
//   - Zero the machine's work X0/Y0 at the pocket's marked corner (the
//     chamfered one - see zero_corner_mark()) for BOTH the front and the
//     flipped-back job. Don't re-zero between them; the whole point is that
//     the jig's own position doesn't move.
//
// UNVERIFIED - confirm before printing: the A350 bed's mounting-hole grid
// pitch (assumed 50mm here, from a rough visual estimate) and hole size
// (assumed M5-ish). Mounting holes below are deliberately oversized (8mm)
// specifically so this doesn't have to be exact - use washers. If the real
// grid turns out different, only mount_x/mount_y below need to change.

// ---- Blank / pocket ----
stock_w = 70;              // SHOPPING_LIST.md: 70x100mm copper-clad blank
stock_h = 100;
stock_t = 1.5;
pocket_clearance = 0.3;    // per-side slip-fit slack, not interference -
                            // the blank needs to drop in and out freely
                            // without disturbing its own registration
pocket_w = stock_w + 2 * pocket_clearance;
pocket_h = stock_h + 2 * pocket_clearance;
pocket_depth = stock_t + 0.5;   // blank sits at/near flush with the top -
                                  // walls only need to be tall enough to
                                  // constrain XY, not to fence in a proud
                                  // blank that could catch the dust shoe

// ---- Base plate ----
wall_t = 4;                // thicker than the enclosure shell's 2.4mm -
                            // this one takes real cutting vibration, not
                            // just cosmetic load
flange_margin = 15;        // extra plastic beyond the pocket wall, for the
                            // mounting holes to sit in without being right
                            // at a stress-concentrating corner
base_t = 4;                // solid plate thickness under the pocket floor -
                            // this also acts as the sacrificial spoilboard
                            // the drill step (mill.tcl) plunges through;
                            // that's intentional, not a defect - real PCB
                            // milling always backs the blank with something
                            // sacrificial for through-drilling

outer_w = pocket_w + 2 * wall_t + 2 * flange_margin;
outer_h = pocket_h + 2 * wall_t + 2 * flange_margin;
total_h = base_t + pocket_depth;

// ---- A350 bed mounting ----
mount_hole_d = 8;          // oversized for an M5 bolt + washer - see the
                            // UNVERIFIED note above; this is what makes an
                            // imprecise grid-pitch guess tolerable
mount_inset = 9;           // hole center inset from each outer edge
mount_x = [mount_inset, outer_w - mount_inset];
mount_y = [mount_inset, outer_h - mount_inset];

// ---- Zero-reference corner mark ----
// The pocket's 4 corners are otherwise identical (it's a plain rectangle,
// deliberately - see header). This chamfer marks ONE specific corner as
// "zero the machine here", so the front and flipped-back jobs actually
// share the same work origin instead of the operator guessing which
// corner. It does not orient the blank itself - the blank's own symmetry
// under the flip is what handles that (see header).
zero_mark_size = 6;

module pocket_cut() {
    translate([wall_t + flange_margin, wall_t + flange_margin, base_t])
        cube([pocket_w, pocket_h, pocket_depth + 0.5]);
}

module zero_corner_mark() {
    // A chamfer cut OUTWARD from the pocket's corner into the solid wall,
    // at the blank's future (0,0) - i.e. wall_t + flange_margin in from the
    // plate edge, same as pocket_cut()'s origin. Cutting into the wall
    // (negative direction) rather than back into the pocket itself matters:
    // the pocket interior there is already empty, so a cut on that side
    // would be a visually-invisible no-op, not a usable mark.
    //
    // Overlaps 0.02mm into the pocket rather than meeting it at an exact
    // shared corner/edge - two solids touching at a zero-width boundary is
    // a classic CGAL degenerate-geometry trigger (hit this directly: the
    // exact-corner version rendered "Simple: no", manifold-repair warning).
    eps = 0.02;
    x0 = wall_t + flange_margin;
    y0 = wall_t + flange_margin;
    translate([x0 + eps, y0 + eps, base_t])
        linear_extrude(height = pocket_depth + 0.5)
            polygon([[0, 0], [-zero_mark_size - eps, 0], [0, -zero_mark_size - eps]]);
}

module mount_holes() {
    for (x = mount_x)
        for (y = mount_y)
            translate([x, y, -0.5])
                cylinder(d = mount_hole_d, h = total_h + 1, $fn = 32);
}

module jig() {
    difference() {
        cube([outer_w, outer_h, total_h]);
        union() {
            pocket_cut();
            zero_corner_mark();
        }
        mount_holes();
    }
}

jig();
