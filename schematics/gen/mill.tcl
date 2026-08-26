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

set cutout_dia      0.8     ;# TODO: pick an actual end mill you own
set cutout_margin   0.0
set cutout_gapsize  0.6
set cutout_cut_z    -1.8    ;# TODO: calibrate - through-cut depth
set cutout_feedrate 80      ;# TODO: calibrate

set gerber_dir "@@GERBER_DIR@@"
set out_dir    "@@OUT_DIR@@"

# --- Front copper isolation --------------------------------------------------
open_gerber $gerber_dir/desk-F_Cu.gtl -outname top_copper
isolate top_copper -dia $iso_dia -passes $iso_passes -overlap $iso_overlap -combine 1 -outname top_iso
cncjob top_iso -z_cut $iso_cut_z -z_move $iso_travel_z -feedrate $iso_feedrate -dia $iso_dia -spindlespeed 0 -outname top_iso_cnc
write_gcode top_iso_cnc $out_dir/top_isolation.nc

# --- Back copper isolation ---------------------------------------------------
open_gerber $gerber_dir/desk-B_Cu.gbl -outname bottom_copper
isolate bottom_copper -dia $iso_dia -passes $iso_passes -overlap $iso_overlap -combine 1 -outname bottom_iso
cncjob bottom_iso -z_cut $iso_cut_z -z_move $iso_travel_z -feedrate $iso_feedrate -dia $iso_dia -spindlespeed 0 -outname bottom_iso_cnc
write_gcode bottom_iso_cnc $out_dir/bottom_isolation.nc

# --- Drilling -----------------------------------------------------------------
open_excellon $gerber_dir/desk.drl -outname drills
drillcncjob drills -drilled_dias all -drillz $drill_cut_z -travelz $drill_travel_z -feedrate_z $drill_feedrate -spindlespeed 0 -outname drill_cnc
write_gcode drill_cnc $out_dir/drill.nc

# --- Board outline cutout ------------------------------------------------------
open_gerber $gerber_dir/desk-Edge_Cuts.gm1 -outname outline
cutout outline -dia $cutout_dia -margin $cutout_margin -gapsize $cutout_gapsize -gaps 4
cncjob outline_cutout -z_cut $cutout_cut_z -z_move $iso_travel_z -feedrate $cutout_feedrate -dia $cutout_dia -spindlespeed 0 -outname cutout_cnc
write_gcode cutout_cnc $out_dir/cutout.nc

save_project $out_dir/mill.FlatPrj

# Headless mode does not exit on its own once the script finishes - it just
# idles as a live Qt event loop. Without this the `make mill` invocation
# (and any CI/script wrapping it) hangs forever.
quit_app
