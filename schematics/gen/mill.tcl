# FlatCAM Tcl Shell script - drives Gerber -> G-code for milling on the
# Snapmaker A350 CNC module at the hackerspace.
#
# Command/option names below are verified directly against this Evo fork's
# own tclCommands/*.py (flatcam.org/manual/cmdreference.html documents an
# older FlatCAM lineage and got several option names wrong for this fork -
# e.g. cncjob's tool-diameter option is -dia here, not -tooldia). If a step
# still errors out, check the matching tclCommands/TclCommand<Name>.py first.
#
# @@GERBER_DIR@@ / @@OUT_DIR@@ are substituted with absolute paths by the
# `mill` Makefile target - this file is a template, not run directly.

# --- User-tunable milling parameters ----------------------------------------
# Bit: Genmitsu 70V15 V-bit, 0.1mm tip diameter, 15 degree included angle
# (see SHOPPING_LIST.md). Cut depth / feedrate below are UNCALIBRATED
# placeholders - dial these in empirically on offcut test coupons before
# cutting the real board. The isolation gap actually milled depends on cut
# depth (a V-bit gets wider as it goes deeper), not just the tip diameter.
set iso_dia         0.1     ;# TODO: calibrate against test coupon
set iso_passes      1
set iso_overlap     0.6
set iso_cut_z       -0.1    ;# TODO: calibrate - mm, negative = into copper
set iso_feedrate    80      ;# TODO: calibrate - mm/min, XY
set iso_travel_z    2.0

set drill_cut_z     -1.8    ;# TODO: calibrate - through FR4 + margin
set drill_feedrate  80      ;# TODO: calibrate
set drill_travel_z  2.0
# The design has 7 distinct hole diameters (0.8-3.2mm - the original 6
# 0.6mm holes were vias, not component leads, so they were widened to 0.8mm
# instead of needing a bit smaller than anything owned - see conversation).
# Rather than physically swap through 7 bits with no auto tool-changer, mill
# every hole as its own circular toolpath with ONE bit (milldrills, below)
# instead of plunge-drilling at each bit's own diameter - a single owned
# 0.8mm end mill (from the Genmitsu 0.8-3mm set, SHOPPING_LIST.md) now
# covers every hole in the design, including the 3.2mm ones (milling a
# circle wider than the bit is exactly what this technique is for). NOT the
# isolation V-bit: a V-bit's cutting width changes with depth, which is
# exactly wrong for boring a hole that needs a consistent diameter through
# the full board thickness.
set drill_mill_dia  0.8      ;# smallest bit in the owned Genmitsu end mill set

set gerber_dir "@@GERBER_DIR@@"
set out_dir    "@@OUT_DIR@@"

# The blank is a pre-cut 70x100mm piece - the same size as the board itself
# (SHOPPING_LIST.md), not an oversized sheet that needs a separate cutout
# pass to trim away. That means there's no real "centering within extra
# stock margin" to get right - the offset step below is pure alignment
# (put the design's own outline flush with the blank's physical edges),
# not centering. It still matters for the flip, though: the registration
# jig (enclosure/mill_jig.scad) holds this exact blank size, and correct
# front/back registration across the physical flip depends on the design's
# outline actually landing flush with the blank's edges in software - any
# offset error `e` here doubles into a `2e` front/back trace misalignment
# after the flip (see the mirror step below), so this still needs to be
# exact, not approximate, even though there's no margin left to be sloppy
# within.
set stock_width  70.0
set stock_height 100.0

# Opened early: the bottom-copper mirror step below needs the true board
# outline as its reference (not a copper-only bounding box, which isn't
# necessarily symmetric - see the mirror step's comment).
open_gerber $gerber_dir/desk-Edge_Cuts.gm1 -outname outline
open_gerber $gerber_dir/desk-F_Cu.gtl -outname top_copper
open_gerber $gerber_dir/desk-B_Cu.gbl -outname bottom_copper
open_excellon $gerber_dir/desk.drl -outname drills

# KiCad exports B_Cu the same way fab houses want it: as seen from the top,
# looking through the board, NOT physically mirrored - fab houses handle the
# mirroring themselves during lamination. Milling by hand means flipping the
# blank yourself, so this file must be pre-mirrored to match, or the milled
# bottom traces come out backwards and won't line up with drilled holes.
#
# Physical flip convention this assumes: flip the blank left-right about its
# own vertical centerline, like turning a page (not top-to-bottom). Mirror
# axis 'X' here means "flip X coordinates" (see camlib.py's mirror() - the
# Tcl wrapper's -axis naming is inverted from that, confirmed by reading
# TclCommandMirror.py directly, not assumed). -box outline anchors the
# mirror to the board outline's center, not bottom_copper's own bounding box
# - those can differ if copper isn't placed symmetrically on the board, which
# would silently misalign the mirrored traces against the drilled holes.
# Verified end to end against the actual Gerbers, not just by inspection: a
# known B_Cu pad landed exactly at its predicted mirrored coordinates in the
# generated G-code and nowhere near its original ones (see conversation).
mirror bottom_copper -axis X -box outline

# Re-anchor everything to the jig's coordinate frame: outline's own bounding
# box (still in its original Gerber-space position at this point) moves so
# its left edge sits `margin_x` from job X=0 (currently ~0 itself, since
# stock_width matches the board's own width almost exactly) and its bottom
# edge sits at job Y=0 - i.e. after this, the blank should occupy job-space
# X:[0,70] Y:[0,100] exactly, matching the jig pocket's own dimensions. All
# four objects move together so their relative alignment (front copper,
# mirrored back copper, drills, outline) is preserved.
set b [lindex [bounds outline] 0]
set outline_xmin [lindex $b 0]
set outline_ymin [lindex $b 1]
set outline_xmax [lindex $b 2]
set board_width [expr {$outline_xmax - $outline_xmin}]
set margin_x [expr {($stock_width - $board_width) / 2.0}]
set dx [expr {$margin_x - $outline_xmin}]
set dy [expr {0.0 - $outline_ymin}]
offset outline top_copper bottom_copper drills -x $dx -y $dy

# --- Front copper isolation --------------------------------------------------
isolate top_copper -dia $iso_dia -passes $iso_passes -overlap $iso_overlap -combine 1 -outname top_iso
cncjob top_iso -z_cut $iso_cut_z -z_move $iso_travel_z -feedrate $iso_feedrate -dia $iso_dia -spindlespeed 0 -outname top_iso_cnc
write_gcode top_iso_cnc $out_dir/top_isolation.nc

# --- Back copper isolation ---------------------------------------------------
isolate bottom_copper -dia $iso_dia -passes $iso_passes -overlap $iso_overlap -combine 1 -outname bottom_iso
cncjob bottom_iso -z_cut $iso_cut_z -z_move $iso_travel_z -feedrate $iso_feedrate -dia $iso_dia -spindlespeed 0 -outname bottom_iso_cnc
write_gcode bottom_iso_cnc $out_dir/bottom_isolation.nc

# --- Drilling -----------------------------------------------------------------
# Not mirrored: drilled holes go straight through the board, so the same
# hole positions are correct from either face.
#
# milldrills (not drillcncjob - see drill_mill_dia's comment above) mills
# each of the 8 hole diameters as its own correctly-sized circle using one
# small bit, then a normal cncjob turns that geometry into G-code exactly
# like the isolation passes above.
milldrills drills -milled_dias all -tooldia $drill_mill_dia -outname drills_mill
cncjob drills_mill -z_cut $drill_cut_z -z_move $drill_travel_z -feedrate $drill_feedrate -dia $drill_mill_dia -spindlespeed 0 -outname drill_cnc
write_gcode drill_cnc $out_dir/drill.nc

save_project $out_dir/mill.FlatPrj

# Headless mode does not exit on its own once the script finishes - it just
# idles as a live Qt event loop. Without this the `make mill` invocation
# (and any CI/script wrapping it) hangs forever.
quit_app
