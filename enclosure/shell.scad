// Single-shell enclosure for desk.kicad_pcb (70x100mm, 2-layer).
//
// The floor is solid and is what mounts to the desk (mounting ears flush
// with it, screwed straight into the desk). Standoffs rise from the floor
// to the PCB's back (solder) side, so the component side faces the open
// top - screws for the PCB go in from that same accessible top, down into
// heat-set inserts in the standoffs.
//
// The top is closed by a flat cover that slides on over the top of the
// shell on a dovetail joint - a wedge-shaped rail on each long wall's top
// edge, tapered only on its inner face (narrow where it meets the wall,
// gradually widening toward the interior as it rises), mating with a
// matching groove cut into the cover. Earlier attempts: a snap-fit lid
// (dropped - too brittle/fiddly for FDM); a fully-captured internal
// channel (dropped - its retaining lip needed an unsupported horizontal
// overhang the full length of the wall to print); an open-top groove
// with ribs (dropped once it was clear this mounts hanging under a desk -
// the cover's own weight would pull it straight out through the open
// top, since nothing was actually capturing it against gravity); a
// dovetail tapered on both faces (dropped - symmetric widening meant it
// overhung past the wall's own outer face on one side and further into
// the interior than needed on the other; only one sloped face is needed
// for the interlock). The remaining taper is shallow enough (~34° off
// vertical) to be self-supporting - each layer only slightly wider than
// the one below, not a true overhang - so the wall side prints with no
// bridging at all; the matching groove lives entirely in the cover, which
// prints lying flat, so its shape costs nothing there either. The front
// wall is left solid to stop the cover when closed; the rail ends flush
// with the back wall, which doubles as the open-end stop - the cover
// comes free by tilting it up once slid back far enough to mostly clear
// the taper. This is a first-draft mechanism: the
// dovetail/clearance dimensions below are estimates, not measurements,
// and want a test print before being trusted.
//
// All PCB-derived dimensions are measured directly from desk.kicad_pcb via
// the pcbnew Python API, not eyeballed from the PDF/SVG render - see the
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
//   - U1 (ESP32-S3-DevKitC): pin socket (~8.5mm) + devkit PCB (~1.6mm) +
//     tallest part on the devkit itself (module/connector, ~3.5mm) = ~14mm
//   - Q5 (TO-220, upright): ~10-14mm depending on lead bend. U5 was this
//     too, but is SMD now (TO-263-5, laid flat - see conversation) and
//     no longer belongs in this list; well under any of the others.
//   - C4/C5 (220uF radial electrolytic): commonly 12.5-16mm tall
// Using 16mm + 3mm safety margin. Cheap to revise once real parts are in
// hand (see SHOPPING_LIST.md) - this is the single number to change.
component_clearance = 19;

// ---- Shell geometry ----
wall_t = 2.4;              // FDM-friendly - 2 perimeters at a common 0.4mm/1.2mm nozzle
floor_t = 2.4;             // solid floor slab - the face that mounts to the desk
xy_clearance = 1.5;        // gap between PCB edge and inner wall, all sides
                            // (U1's courtyard, USB-C overhang included, stays
                            // within PCB x:3.2-69.1 - checked directly via
                            // the pcbnew Python API - so it never reaches
                            // either board edge and needs no extra allowance
                            // here; see the USB slot's own comment in
                            // shell() for which wall it actually overhangs
                            // toward)

// standoff: cylindrical post rising from the floor to the PCB's back
// surface, with a pilot hole for an M3 heat-set insert (common brass
// insert OD ~4.0-4.2mm; using 4.2mm for an easy press-fit) opening from
// the TOP of the post (the PCB-facing end, now the accessible side) - the
// screw drives down from above, through the PCB, into it. Tall enough for
// the 6mm-deep insert plus a 2mm floor of material below it.
standoff_od = 8;
insert_hole_d = 4.2;
insert_depth = 6;
standoff_h = insert_depth + 2;

// ---- Sliding cover (replaces a solid ceiling) ----
// Dovetail rail on each long wall's top edge (protruding upward, past
// shell_h) mating with a groove cut into the cover.
cover_t = 5;                     // thick enough to fully bury the dovetail
                                   // rail's height (plus dovetail_clearance)
                                   // and still leave a solid ~1.7mm roof
                                   // above the groove - 4mm left under 1mm
                                   // there, too thin to be sturdy
dovetail_h = 3;                   // height the rail rises above shell_h
dovetail_base_w = 1.2;            // rail width where it meets the wall
dovetail_tip_w = 3.2;             // rail width at its widest (the top),
                                   // measured inward from the wall's own
                                   // outer face - only the inner face
                                   // tapers, so this is also how far the
                                   // rail reaches past the wall's inner
                                   // surface at its widest point. (tip_w -
                                   // base_w) / dovetail_h is the taper
                                   // angle's tangent (~34 degrees here);
                                   // keep this comfortably under the ~45
                                   // degree self-supporting limit so the
                                   // wall side prints with no overhang
dovetail_clearance = 0.4;         // per-side slack on the cover's groove
                                   // so it isn't a press fit - biased
                                   // toward generous since the taper
                                   // compounds ordinary FDM inaccuracy: a
                                   // height error of e off shifts the
                                   // effective width by e*tan(34 degrees)
                                   // on top of plain XY error. Loose
                                   // rather than binding is the safe
                                   // failure mode here; tighten later
                                   // once a real printer's tolerances are
                                   // known
stop_margin = 3;                  // where each rail starts, leaving this
                                   // much solid wall length in front of it
endstop_t = 3.5;                   // thickness (Y) of the full-width block
                                   // that actually stops the cover at
                                   // stop_margin - the rail simply ending
                                   // there isn't itself a physical stop,
                                   // just the end of the taper engagement.
                                   // A plain tuned number, not derived
                                   // from wall_t - wall_t itself (2.4mm)
                                   // and 1.5x it (3.6mm) were both tried
                                   // and rejected (too thin, too big
                                   // respectively); this exact value
                                   // (3.5mm) was the one previously
                                   // accepted without complaint
lock_bump = 1.2;                   // extra width added to the rail's tip,
                                   // locally, right where the cover sits
                                   // when closed - no separate moving
                                   // part, just enough interference that
                                   // the cover's groove has to flex a
                                   // touch to pass it, which is what
                                   // keeps the lid from sliding open on
                                   // its own. Has to clear the groove's
                                   // own 2*dovetail_clearance (0.8mm) of
                                   // built-in slack before it touches
                                   // anything at all, so this needs to be
                                   // bigger than that, not just "a bit
                                   // wider than the rail"
lock_bump_len = 5;                 // Y-length the bump ramps up and back
                                   // down over - a step straight to full
                                   // width would just act as a second,
                                   // unwanted endstop instead of
                                   // resistance you can slide through
lock_bump_y0 = stop_margin + 3;    // starts just past the endstop, so it
                                    // sits right in the closed position

// ---- Derived ----
inner_w = pcb_w + 2 * xy_clearance;
inner_h = pcb_h + 2 * xy_clearance;
outer_w = inner_w + 2 * wall_t;
outer_h = inner_h + 2 * wall_t;
shell_h = floor_t + standoff_h + pcb_t + component_clearance;  // the groove
                                   // is cut into the wall's own thickness,
                                   // not into extra interior height, so it
                                   // doesn't add to this the way the old
                                   // internal rail mechanism did

// PCB origin, in shell coordinates: xy_clearance from the left/front walls'
// inner faces
pcb_x0 = wall_t + xy_clearance;
pcb_y0 = wall_t + xy_clearance;

// X carries straight over (shell_x = pcb_x0 + kicad_x), but Y needs a
// flip (shell_y = pcb_y0 + (pcb_h - kicad_y)) - NOT a 180-degree rotation
// of the board (X is untouched), and NOT a mirror of the board either.
// It's a coordinate-convention mismatch: KiCad's plot is Y-down (screen/
// image convention), while looking down at the shell from above is
// naturally Y-up (graph convention). Cross-checked directly: X_kicad *
// Y_kicad (right-hand rule, using KiCad's own X-right/Y-down axes) points
// INTO the board, away from someone looking at the component side - so
// carrying kicad_y straight over without the flip quietly looks at the
// board from the wrong side. Verified against desk.kicad_pcb's actual
// plot, not just derived - see U1/TB1/TB4 below.
function pcb_y(kicad_y) = pcb_y0 + (pcb_h - kicad_y);

// wire cutouts - generous per explicit instruction ("liberal, size-wise").
// Sized to the full usable interior height, centered within it.
cutout_h = shell_h - floor_t;
cutout_z = floor_t + cutout_h / 2;

// TB4+TB5 and TB1+TB2 are each wired with a single shared pigtail off-board
// (motor+supply, and handset, respectively - see README §6.4) - the screw
// terminals themselves stay fully internal, wired before the enclosure goes
// on, so they need no external access at all. Just a round pass-through per
// pigtail bundle, generously sized rather than fitted to a wire gauge.
// Positions verified directly against desk.kicad_pcb via the pcbnew Python
// API (footprint bounding boxes), not assumed, and passed through pcb_y()
// (see above): TB4+TB5 sit at PCB x:49.8-73.4, y:99.6-111.3 (both +15
// from the whole-board shift - see conversation), which puts them
// against the FRONT wall (x-center ~61.6 is just carried over, only y
// decided which wall). TB1+TB2 sit at PCB x:73.6-85.3, y:57.8-85 - still
// the RIGHT wall (x wasn't flipped), y-center ~56.4 (was mistyped 43.6
// here before this pass - the range was always right, the center wasn't)
// - the same wall U1's USB slot lands on below (matching the "relocated
// to clear U1's USB edge" reasoning).
pigtail_hole_d = 10;

// mounting ears ("pig ears"): one flange centered on each short (front/
// back) wall, flush with the floor (z=0), for screwing the shell down to
// the desk - the floor is the face that mounts, so that's where these sit.
ear_t = 4;           // flange thickness - thicker than wall_t since a
                      // single screw pulls straight down through a small
                      // area here, not spread across a whole wall
ear_r = 6;            // radius of the tab's rounded ends
ear_reach = 10;       // distance from the wall face to the screw hole's
                      // center
ear_hole_d = 4.5;     // clearance for a #8 / M4 wood screw into the desk

module mounting_ear(x, y0, y1) {
    // a rounded tab running along Y from y0 (embedded in the wall, for a
    // solid joint) to y1 (the tip, holding the screw hole)
    hull() {
        translate([x, y0, 0]) cylinder(r = ear_r, h = ear_t, $fn = 32);
        translate([x, y1, 0]) cylinder(r = ear_r, h = ear_t, $fn = 32);
    }
}

module wall_hole_x(y, z, from_left) {
    // round pass-through in the X direction (left or right wall)
    x0 = from_left ? -0.5 : outer_w - wall_t - 0.5;
    translate([x0, y, z])
        rotate([0, 90, 0])
            cylinder(d = pigtail_hole_d, h = wall_t + 1, $fn = 32);
}

module wall_hole_y(x, z, from_front) {
    // round pass-through in the Y direction (front or back wall)
    y0 = from_front ? -0.5 : outer_h - wall_t - 0.5;
    translate([x, y0, z])
        rotate([-90, 0, 0])
            cylinder(d = pigtail_hole_d, h = wall_t + 1, $fn = 32);
}

// U1's USB-C cutout - a rounded rectangle in the wall's own visible face
// (Y-Z plane: along-wall by height), extruded straight through the wall
// thickness (X, which needs no rounding - it's a plain through-hole in
// that direction). Built as the hull of four corner cylinders whose axis
// runs along X, so the rounding actually shows up on the opening you can
// see, not on the (invisible) wall-penetration direction.
module rounded_wall_slot(x0, depth, y0, w, z0, h, r) {
    hull() {
        for (dy = [r, w - r])
            for (dz = [r, h - r])
                translate([x0, y0 + dy, z0 + dz])
                    rotate([0, 90, 0])
                        cylinder(r = r, h = depth, $fn = 24);
    }
}

// dovetail rail protruding up from a long wall's top edge. Only the
// inner face (facing the box interior) tapers - narrow where it meets
// the wall (z=shell_h), widening to its full width by z=shell_h+
// dovetail_h; the outer face stays flush with the wall's own outer
// surface the whole way up. A symmetric taper (widening on both faces)
// would overhang past the wall on the outer side and deeper into the
// interior on the inner side than necessary - one sloped face is all the
// interlock needs. hull() of two same-length boxes at different
// widths/heights (both pinned to the same outer edge) produces this
// wedge, extruded along Y. The rail's base also starts 0.5mm below
// shell_h, embedding slightly into the wall instead of just touching its
// top face exactly - an exactly-coincident seam between two separately-
// unioned solids is a classic z-fighting/artifact trigger, same as the
// cut-boundary issue noted below. Starts stop_margin in from the front
// (leaving solid wall there, which is what stops the cover when closed)
// and ends flush with the back wall - running out of rail there doubles
// as the open-end stop, and the cover comes free by tilting it up once
// slid back far enough to mostly clear the taper. No lead-in chamfer at
// that open end for now (a version tapering the width was tried and
// dropped - a horizontal taper there was wanted instead, but simplest is
// to leave it out entirely and file the opening by hand if it turns out
// too tight).
rail_embed = 0.5;
module dovetail_rail(from_left) {
    y0 = stop_margin;
    y1 = outer_h;
    x_outer = from_left ? 0 : outer_w;
    x0_base = from_left ? x_outer : x_outer - dovetail_base_w;
    x0_tip = from_left ? x_outer : x_outer - dovetail_tip_w;
    hull() {
        translate([x0_base, y0, shell_h - rail_embed])
            cube([dovetail_base_w, y1 - y0, 0.01]);
        translate([x0_tip, y0, shell_h + dovetail_h])
            cube([dovetail_tip_w, y1 - y0, 0.01]);
    }
}

// full-width block right where the rail starts - what the cover actually
// bumps into when closed. The rail simply ending at stop_margin isn't a
// physical stop by itself, just the end of the taper engagement; this is
// tall enough (up to shell_h+cover_t) to block the cover's full
// cross-section, not just the rib. Clamped to y=0: endstop_t (3.5) is
// larger than stop_margin (3), so placing it purely by "endstop_t back
// from stop_margin" pushed its start to y=-0.5 - 0.5mm past the front
// wall's own outer face, into thin air. Starting at y=0 instead just
// means the block is stop_margin thick here rather than the full
// endstop_t, which is fine - it still fully blocks the cover.
module endstop() {
    y0 = max(0, stop_margin - endstop_t);
    translate([0, y0, shell_h])
        cube([outer_w, stop_margin - y0, cover_t]);
}

// local detent: a smooth ramp up to a peak and back down again, right at
// the rail's own tip height, where the cover sits when closed - see
// lock_bump above. hull() of a flat slab (matching the rail's existing
// tip cross-section exactly, so it blends in with no seam) and a single
// raised, wider point at the midpoint produces a tent/pyramid shape - the
// interference builds up and releases gradually along Y as the cover
// slides through, rather than the abrupt step a simple two-slab hull
// would give (which would just act as a second, unwanted endstop instead
// of resistance you can slide past).
module dovetail_bump(from_left) {
    y0 = lock_bump_y0;
    y_mid = y0 + lock_bump_len / 2;
    y1 = y0 + lock_bump_len;
    x_outer = from_left ? 0 : outer_w;
    w_tip = dovetail_tip_w;
    w_peak = dovetail_tip_w + lock_bump;
    x0_tip = from_left ? x_outer : x_outer - w_tip;
    x0_peak = from_left ? x_outer : x_outer - w_peak;
    z_tip = shell_h + dovetail_h;
    hull() {
        translate([x0_tip, y0, z_tip - 0.6])
            cube([w_tip, y1 - y0, 0.01]);
        translate([x0_peak, y_mid, z_tip])
            cube([w_peak, 0.01, 0.01]);
    }
}

// matching groove for the cover - the same one-sided taper, enlarged by
// dovetail_clearance on every side, cut the full length of the cover.
// Cutting this into an otherwise flat, bed-supported panel costs nothing
// printability-wise regardless of its shape - unlike the wall side, there
// is no overhang concern here at all.
module dovetail_groove(from_left) {
    c = dovetail_clearance;
    y0 = -1;
    y1 = cover_length + 1;
    x_outer = from_left ? -c : outer_w + c;
    bw = dovetail_base_w + 2 * c;
    tw = dovetail_tip_w + 2 * c;
    x0_base = from_left ? x_outer : x_outer - bw;
    x0_tip = from_left ? x_outer : x_outer - tw;
    hull() {
        translate([x0_base, y0, -c])
            cube([bw, y1 - y0, 0.01]);
        translate([x0_tip, y0, dovetail_h + c])
            cube([tw, y1 - y0, 0.01]);
    }
}

cover_width = outer_w;
// matches the rail's actual usable run (stop_margin to outer_h) rather
// than the old outer_h-1 - that let the cover overhang past the back by
// about stop_margin's worth once it could actually reach a defined
// closed position against the new endstop() below
cover_length = outer_h - stop_margin - 0.5;

// origin-positioned so its underside sits at local z=0 (aligning with the
// dovetail rail's base when assembled at global z=shell_h) - a separate
// printed part, not fused to shell(). Export it on its own via
// `openscad --render -o cover.stl -D 'part="cover"' shell.scad`.
// render() forces this to be fully resolved (CGAL) once rather than
// live-differenced every frame by OpenSCAD's F5 preview - the same
// OpenCSG-preview issue noted on shell() below applies here too (a
// difference() against two hull()-built cuts), and showed up as stray
// disconnected-looking fragments in preview before this was added.
module cover() {
    render() difference() {
        cube([cover_width, cover_length, cover_t]);
        dovetail_groove(true);
        dovetail_groove(false);
    }
}

// render() forces this whole shape to be fully resolved (CGAL) once,
// rather than live-differenced every frame by OpenSCAD's F5 preview
// (OpenCSG, a real-time stencil-buffer trick, not a true boolean). This
// model's difference() has enough simultaneous cuts - the interior
// hollow, ear holes, wall holes, a 4-cylinder hull for the USB slot - to
// exceed what OpenCSG can correctly composite on many graphics drivers,
// which shows up as dense diagonal hatching/corruption on the cut faces
// in preview. Has no effect on --render/STL output, which was always
// correct - this only fixes what the interactive preview looks like.
module shell() {
    render() difference() {
        union() {
            cube([outer_w, outer_h, shell_h]);
            mounting_ear(outer_w / 2, wall_t / 2, -ear_reach);
            mounting_ear(outer_w / 2, outer_h - wall_t / 2, outer_h + ear_reach);
            dovetail_rail(true);
            dovetail_rail(false);
            endstop();
            dovetail_bump(true);
            dovetail_bump(false);
        }

        // hollow interior: cut from just above the floor all the way up
        // through the open top, leaving a solid floor_t slab at the
        // bottom. Stops exactly at shell_h, not past it - it used to
        // overshoot 1mm to dodge a z-fighting artifact in OpenSCAD's
        // preview where this cut's top face landed exactly on the outer
        // cube's top face, but that overshoot started biting a real ~1mm
        // notch into endstop() and dovetail_rail() once those were added
        // (both sit right at/above shell_h and extend past x=wall_t).
        // shell()'s own render() below already resolves the exact-
        // coincidence case cleanly, so the overshoot is just harmful now.
        translate([wall_t, wall_t, floor_t])
            cube([inner_w, inner_h, shell_h - floor_t]);

        // mounting ear screw holes
        translate([outer_w / 2, -ear_reach, -0.5])
            cylinder(d = ear_hole_d, h = ear_t + 1, $fn = 24);
        translate([outer_w / 2, outer_h + ear_reach, -0.5])
            cylinder(d = ear_hole_d, h = ear_t + 1, $fn = 24);

        // TB4+TB5 shared pigtail (motor+supply): front wall, at their
        // actual PCB x-center (~61.6, after the whole board shifted
        // +15/+15 to clear the drawing-sheet border - see conversation)
        // - x isn't flipped, only y decided the wall
        wall_hole_y(pcb_x0 + 61.6, cutout_z, true);

        // TB1+TB2 shared pigtail (handset): right wall, at their actual
        // PCB y-center (~71.4, same +15 shift) run through pcb_y()
        wall_hole_x(pcb_y(71.4), cutout_z, false);

        // U1 USB-C: checked directly against desk.kicad_pcb via the pcbnew
        // Python API rather than assumed - U1's courtyard overhangs the
        // pin-header block by 8.5mm past the pin-1 end (low PCB-x) versus
        // 4mm past the pin-22 end (high PCB-x, where TB1/TB2 sit). The
        // small overhang is the USB-C connector; the big one is antenna
        // clearance - so the slot belongs on the right wall, the same one
        // TB1/TB2 land on above (matching the "relocated to clear U1's USB
        // edge" reasoning). Positioned within U1's PCB y:28.4-56.8 span
        // (also +15 from the board shift - see conversation), run through
        // pcb_y(). "Liberal" sizing applies mostly along the wall (y) and
        // only a little vertically (z) - the opening doesn't need to be
        // tall, just wide enough for comfortable cable access. Bottom
        // sits just above the PCB's own top (component) surface - nothing
        // below that needs to be reachable through this wall.
        usb_slot_z0 = floor_t + standoff_h + pcb_t + 1;
        usb_slot_h = 8;
        rounded_wall_slot(outer_w - wall_t - 1, wall_t + 2, pcb_y(52), 20, usb_slot_z0, usb_slot_h, 2);
    }

    // four standoffs, rising from the floor to the PCB's back surface
    for (pos = [[hole_inset, hole_inset],
                [pcb_w - hole_inset, hole_inset],
                [hole_inset, pcb_h - hole_inset],
                [pcb_w - hole_inset, pcb_h - hole_inset]]) {
        translate([pcb_x0 + pos[0], pcb_y0 + pos[1], floor_t]) {
            difference() {
                cylinder(d = standoff_od, h = standoff_h, $fn = 32);
                // pilot hole for the heat-set insert, opening from the top
                // (PCB-facing) end - the screw drives down from the
                // accessible component side, through the PCB, into it
                translate([0, 0, standoff_h - insert_depth])
                    cylinder(d = insert_hole_d, h = insert_depth + 0.5, $fn = 24);
            }
        }
    }
}

// which part to view/emit - override via `-D 'part="shell"'` or
// `-D 'part="cover"'` to get just that part (for STL export - each is a
// separate printed piece). Default ("preview") shows both, side by side
// rather than assembled: assembled placement puts the cover's groove
// exactly flush against the dovetail rail's faces, and that coincident
// geometry is a classic cause of z-fighting/flicker in OpenSCAD's F5
// preview (harmless for actual --render/STL output, which fully resolves
// the booleans, but distracting to look at and easy to mistake for a real
// modeling bug).
part = "preview";

if (part == "shell") {
    shell();
} else if (part == "cover") {
    cover();
} else {
    shell();
    translate([outer_w + 10, 0, 0])
        cover();
}
