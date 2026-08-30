SCH := ../desk.kicad_sch
PDF := ../desk.pdf
SVG := ../desk.svg
PCB := ../desk.kicad_pcb
GERBER_DIR := ../gerbers
GCODE_DIR := ../gerbers/gcode
FLATCAM := $(abspath ../../tools/flatcam.sh)
MILL_TCL := mill.generated.tcl
PCB2GCODE := $(abspath ../../tools/pcb2gcode-src/build/pcb2gcode)

CHECKS := find_shorts.py find_diagonals.py find_crossings.py find_body_crossings.py

.PHONY: all clean check gerbers mill mill-pcb2gcode mill-flatcam verify
.PRECIOUS: $(SCH)
all: $(SCH) $(PDF) $(SVG)

# Each check re-imports sch.py fresh via _trace.py, so they don't need
# $(SCH) as a prerequisite - they trace the generator directly, not the
# file it wrote.
check:
	@for c in $(CHECKS); do echo "== $$c =="; python3 $$c; done

$(SCH): sch.py schlib.py symbols.py
	python3 sch.py $(SCH)

$(PDF): $(SCH)
	kicad-cli sch export pdf -o $(PDF) $(SCH)

$(SVG): $(SCH)
	# svg export's -o always names a directory, never a file (unlike pdf) -
	# cd to the target dir first so the flat "desk.svg" it writes lands in
	# the right place.
	cd .. && kicad-cli sch export svg desk.kicad_sch


# For isolation milling: F.Cu/B.Cu (copper), Edge.Cuts (outline). Not part
# of `all` - these are for a real milling run, not every-edit regeneration.
# Feed the output to custom_isolate.py (`mill`), pcb2gcode (`mill-pcb2gcode`)
# or FlatCAM (`mill-flatcam`) - see README §5 / APPENDIX §7 - not KiCad's
# own Gcode tooling.
gerbers: $(PCB)
	mkdir -p $(GERBER_DIR)
	kicad-cli pcb export gerbers --layers F.Cu,B.Cu,Edge.Cuts -o $(GERBER_DIR)/ $(PCB)
	kicad-cli pcb export drill -o $(GERBER_DIR)/ $(PCB)

# custom_isolate.py generates the isolation toolpath directly from KiCad's
# own copper/clearance boundary (the same SVG render verify_isolation.py
# already trusts), instead of trusting FlatCAM's or pcb2gcode's own
# internal polygon-offset algorithm - both showed real, confirmed bugs on
# this board (FlatCAM: 3; pcb2gcode --voronoi: 2). Extensive spot-checking
# found none in this generator - see its own docstring and APPENDIX §7.1
# for the full investigation. This is now the default `mill`; both older
# pipelines are kept working as explicit fallbacks (`make mill-pcb2gcode`,
# `make mill-flatcam`).
#
# Drilling still goes through pcb2gcode (see mill-pcb2gcode below for the
# coordinate-frame flags and why they're set that way) - only its isolation
# output is discarded (never referenced below), since milldrilling hasn't
# shown any of the isolation-specific bugs this investigation found and
# pcb2gcode's own coordinate frame (with the x/y-offset correction) is
# already independently verified.
mill: gerbers
	mkdir -p $(GCODE_DIR)
	mkdir -p $(COPPER_SVG_DIR)
	# _only variants (no Edge.Cuts) are what custom_isolate.py itself reads -
	# see its docstring: kicad-cli draws Edge.Cuts as a visible stroke that
	# would get misclassified as copper. The plain f_cu.svg/b_cu.svg (with
	# Edge.Cuts, for board-edge context only) are for `verify`'s own
	# rendering, which determines off-board geometrically instead.
	kicad-cli pcb export svg --layers F.Cu --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/f_cu_only.svg $(PCB)
	kicad-cli pcb export svg --layers B.Cu --mirror --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/b_cu_only.svg $(PCB)
	kicad-cli pcb export svg --layers F.Cu,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/f_cu.svg $(PCB)
	kicad-cli pcb export svg --layers B.Cu,Edge.Cuts --mirror --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/b_cu.svg $(PCB)
	$(FLATCAM_PY) custom_isolate.py $(COPPER_SVG_DIR)/f_cu_only.svg 70 100 $(GCODE_DIR)/top_isolation.nc $(GERBER_DIR)/desk.drl
	$(FLATCAM_PY) custom_isolate.py $(COPPER_SVG_DIR)/b_cu_only.svg 70 100 $(GCODE_DIR)/bottom_isolation.nc $(GERBER_DIR)/desk.drl --mirror
	$(PCB2GCODE) \
	    --front $(GERBER_DIR)/desk-F_Cu.gtl --back $(GERBER_DIR)/desk-B_Cu.gbl \
	    --drill $(GERBER_DIR)/desk.drl \
	    --outline $(GERBER_DIR)/desk-Edge_Cuts.gm1 --cutter-diameter 1.0 \
	    --zcut -1.8 --cut-feed 80 --cut-speed 10000 --cut-infeed 1.8 \
	    --metric --metricoutput --zero-start --mirror-axis 35 \
	    --x-offset -1.05 --y-offset -1.05 \
	    --zsafe 2.0 --zchange 10.0 --zwork -0.1 \
	    --mill-feed 80 --mill-speed 10000 \
	    --mill-diameters 0.1 --isolation-width 0.22 --milling-overlap 40% \
	    --min-milldrill-hole-diameter 0 --milldrill-diameter 0.8 \
	    --zdrill -1.8 --drill-feed 80 --drill-speed 10000 \
	    --front-output pcb2gcode_front_unused.ngc --back-output pcb2gcode_back_unused.ngc \
	    --milldrill-output drill.nc \
	    --output-dir $(GCODE_DIR)
	python3 snapmaker_header.py $(GCODE_DIR)/top_isolation.nc $(GCODE_DIR)/top_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/bottom_isolation.nc $(GCODE_DIR)/bottom_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/drill.nc $(GCODE_DIR)/drill.snapmaker.nc

# pcb2gcode's isolation was found to be measurably more complete than
# FlatCAM's (see README §5 / APPENDIX §7.1 for the full investigation:
# three distinct FlatCAM isolate() bugs were found and confirmed, the last
# of which - a path-ordering detour silently skipping a short loop-closing
# segment - can't be patched around generically). Superseded as the
# default by custom_isolate.py above (see APPENDIX §7.1 again - two more
# bugs found in pcb2gcode's own --voronoi mode motivated moving off
# trusting third-party polygon-offset algorithms at all); kept working as
# an explicit fallback.
#
# Coordinate frame - do not change these flags without re-reading APPENDIX
# §7 first, this took a full empirical derivation to get right:
# --outline (with a placeholder --cutter-diameter, --zcut etc - outline.ngc
# itself is never used, the blank is pre-cut same as mill.tcl) is required
# so --zero-start anchors to the true 70x100mm board rather than just the
# copper's own bounding box. But pcb2gcode's own outline-bounding-box
# computation inflates that box outward by (cutter-diameter + 0.05mm) in
# +X/+Y - confirmed empirically by tracing a known drilled hole's exact
# coordinates through the pipeline, not documented anywhere - so
# --x-offset/--y-offset must cancel exactly that (-1.05 for a 1.0mm
# cutter-diameter placeholder). Get this wrong and every coordinate is off
# by ~1mm against the milling jig, silently. --mirror-axis 35 is half the
# TRUE board width (70mm), only correct once --outline fixes the bounding
# box above.
mill-pcb2gcode: gerbers
	mkdir -p $(GCODE_DIR)
	$(PCB2GCODE) \
	    --front $(GERBER_DIR)/desk-F_Cu.gtl --back $(GERBER_DIR)/desk-B_Cu.gbl \
	    --drill $(GERBER_DIR)/desk.drl \
	    --outline $(GERBER_DIR)/desk-Edge_Cuts.gm1 --cutter-diameter 1.0 \
	    --zcut -1.8 --cut-feed 80 --cut-speed 10000 --cut-infeed 1.8 \
	    --metric --metricoutput --zero-start --mirror-axis 35 \
	    --x-offset -1.05 --y-offset -1.05 \
	    --zsafe 2.0 --zchange 10.0 --zwork -0.1 \
	    --mill-feed 80 --mill-speed 10000 \
	    --mill-diameters 0.1 --isolation-width 0.22 --milling-overlap 40% \
	    --min-milldrill-hole-diameter 0 --milldrill-diameter 0.8 \
	    --zdrill -1.8 --drill-feed 80 --drill-speed 10000 \
	    --front-output top_isolation.nc --back-output bottom_isolation.nc \
	    --milldrill-output drill.nc \
	    --output-dir $(GCODE_DIR)
	# Needed by `verify` below (same copper render both mill pipelines share).
	mkdir -p $(COPPER_SVG_DIR)
	kicad-cli pcb export svg --layers F.Cu,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/f_cu.svg $(PCB)
	kicad-cli pcb export svg --layers B.Cu,Edge.Cuts --mirror --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/b_cu.svg $(PCB)
	# Unlike FlatCAM (see mill-flatcam below), pcb2gcode retracts to Z-safe
	# before every disjoint isolation loop as a matter of its own G-code
	# structure (confirmed directly: retract count matches loop count) -
	# no evidence of FlatCAM's silent same-Z gouge bug, so
	# fix_travel_jumps.py's fix-in-place mutation is NOT run here. This was
	# actually checked this session (retract/loop-count audit + full-board
	# visual inspection via verify_isolation.py), not assumed.
	python3 snapmaker_header.py $(GCODE_DIR)/top_isolation.nc $(GCODE_DIR)/top_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/bottom_isolation.nc $(GCODE_DIR)/bottom_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/drill.nc $(GCODE_DIR)/drill.snapmaker.nc

# Old FlatCAM-based pipeline - kept working as an explicit fallback (see
# comment on `mill` above). Runs FlatCAM headlessly against mill.tcl
# (isolation/drill -> raw G-code - no separate cutout pass, the blank is
# pre-cut to the board's own 70x100mm size, see mill.tcl), then rewrites
# each output with the header the Snapmaker touchscreen needs (see
# snapmaker_header.py - raw FlatCAM output crashes it). mill.tcl is a
# template; mill.generated.tcl (gitignored) has real paths substituted in.
mill-flatcam: gerbers
	mkdir -p $(GCODE_DIR)
	sed -e 's|@@GERBER_DIR@@|$(abspath $(GERBER_DIR))|g' \
	    -e 's|@@OUT_DIR@@|$(abspath $(GCODE_DIR))|g' \
	    mill.tcl > $(MILL_TCL)
	# quit_app (end of mill.tcl) reliably triggers Qt shutdown, but FlatCAM's
	# worker-pool teardown afterwards doesn't reliably exit the process - by
	# then write_gcode/save_project have already run, so the outputs below
	# are complete regardless. Bound it instead of trusting a clean exit.
	timeout --kill-after=10 300 $(FLATCAM) --shellfile=$(abspath $(MILL_TCL)) --headless=1 || true
	# Needed by fix_travel_jumps.py below (geometry-aware, needs the design's
	# own copper render) - generated here, not just in `verify`, since this
	# step now runs before that target does.
	mkdir -p $(COPPER_SVG_DIR)
	kicad-cli pcb export svg --layers F.Cu,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/f_cu.svg $(PCB)
	kicad-cli pcb export svg --layers B.Cu,Edge.Cuts --mirror --page-size-mode 2 --exclude-drawing-sheet --mode-single -o $(COPPER_SVG_DIR)/b_cu.svg $(PCB)
	# Real FlatCAM bug, not a precaution: isolating a fill zone with holes
	# in it (e.g. a ground pour with isolated pads/vias) can silently omit
	# the retract between separate isolation loops, leaving a straight
	# uncontrolled gouge in material connecting them - see conversation and
	# fix_travel_jumps.py's own docstring for the full traced root cause.
	# A pure move-length threshold turned out unable to tell a genuine bogus
	# gouge from a genuine long straight cut (a board-edge-parallel run needs
	# few tessellation points) - fix_travel_jumps.py is now geometry-aware,
	# checking each candidate against the design's own copper render, so it
	# needs the copper SVGs above and the board size as arguments.
	# Confirmed drill.nc (from milldrills, not isolate) doesn't have this -
	# only isolation output needs it.
	$(FLATCAM_PY) fix_travel_jumps.py $(GCODE_DIR)/top_isolation.nc $(GCODE_DIR)/top_isolation.nc $(COPPER_SVG_DIR)/f_cu.svg 70 100
	$(FLATCAM_PY) fix_travel_jumps.py $(GCODE_DIR)/bottom_isolation.nc $(GCODE_DIR)/bottom_isolation.nc $(COPPER_SVG_DIR)/b_cu.svg 70 100
	python3 snapmaker_header.py $(GCODE_DIR)/top_isolation.nc $(GCODE_DIR)/top_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/bottom_isolation.nc $(GCODE_DIR)/bottom_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/drill.nc $(GCODE_DIR)/drill.snapmaker.nc

FLATCAM_PY := $(abspath ../../tools/flatcam-env/bin/python)
COPPER_SVG_DIR := $(GCODE_DIR)/copper_svg

# Confirms, per pixel, whether the actual toolpath (real post-fix G-code,
# not an idealized simulation) cuts through real as-designed copper -
# orange - versus just travelling over already-bare substrate - gray. A
# plain "copper minus toolpath" render can't make that distinction (white
# means "no copper" whether that's because the mill removed it or because
# it was never there), which is exactly what's needed to actually confirm
# isolation happens where it should, e.g. near board corners - see
# conversation and verify_isolation.py's own docstring.
# tool_dia/board_w/board_h args below must match mill.tcl's iso_dia and the
# board's actual size (70x100mm). The last four numbers are a zoomed crop
# (mm, x0 y0 x1 y1) - full-board renders compress a 0.1mm toolpath line to
# near-invisibility. Edge.Cuts is still included for reference/context in
# the SVG, but off-board is NOT determined from it: kicad-cli's Edge.Cuts
# export does not reliably fill the whole board interior opaque (confirmed
# directly - a point clearly mid-board, between two traces, rendered fully
# transparent, identical to genuinely off-board space), so
# verify_isolation.py determines off-board from the known board_w/board_h
# rectangle instead (the board is confirmed a plain rectangle, no rounded
# corners - see conversation).
# f_cu.svg/b_cu.svg are already generated by `mill` - not regenerated here.
# To check a fallback pipeline side by side instead, run
# `make mill-pcb2gcode` or `make mill-flatcam` first (each regenerates its
# own copper SVGs), then call verify_isolation.py directly with the same
# args as above, pointed at that pipeline's output.
verify: mill
	$(FLATCAM_PY) verify_isolation.py $(COPPER_SVG_DIR)/f_cu.svg $(GCODE_DIR)/top_isolation.nc 0.1 70 100 $(GCODE_DIR)/top_isolation_check.png -3 75 25 103
	$(FLATCAM_PY) verify_isolation.py $(COPPER_SVG_DIR)/b_cu.svg $(GCODE_DIR)/bottom_isolation.nc 0.1 70 100 $(GCODE_DIR)/bottom_isolation_check.png -3 75 25 103

clean:
	rm -f $(PDF) $(SVG)
	rm -rf $(GERBER_DIR) $(MILL_TCL)
