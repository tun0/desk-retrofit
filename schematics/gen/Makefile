SCH := ../desk.kicad_sch
PDF := ../desk.pdf
SVG := ../desk.svg
PCB := ../desk.kicad_pcb
GERBER_DIR := ../gerbers
GCODE_DIR := ../gerbers/gcode
FLATCAM := $(abspath ../../tools/flatcam.sh)
MILL_TCL := mill.generated.tcl

CHECKS := find_shorts.py find_diagonals.py find_crossings.py find_body_crossings.py

.PHONY: all clean check gerbers mill
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
# Feed the output to FlatCAM (confirmed to work for Snapmaker PCB milling,
# unlike pcb2gcode - see conversation), not KiCad's own Gcode tooling.
gerbers: $(PCB)
	mkdir -p $(GERBER_DIR)
	kicad-cli pcb export gerbers --layers F.Cu,B.Cu,Edge.Cuts -o $(GERBER_DIR)/ $(PCB)
	kicad-cli pcb export drill -o $(GERBER_DIR)/ $(PCB)

# Runs FlatCAM headlessly against mill.tcl (isolation/drill -> raw G-code -
# no separate cutout pass, the blank is pre-cut to the board's own 70x100mm
# size, see mill.tcl), then rewrites each output with the header the
# Snapmaker touchscreen needs (see snapmaker_header.py - raw FlatCAM output
# crashes it). mill.tcl is a template; mill.generated.tcl (gitignored) has
# real paths substituted in.
mill: gerbers
	mkdir -p $(GCODE_DIR)
	sed -e 's|@@GERBER_DIR@@|$(abspath $(GERBER_DIR))|g' \
	    -e 's|@@OUT_DIR@@|$(abspath $(GCODE_DIR))|g' \
	    mill.tcl > $(MILL_TCL)
	# quit_app (end of mill.tcl) reliably triggers Qt shutdown, but FlatCAM's
	# worker-pool teardown afterwards doesn't reliably exit the process - by
	# then write_gcode/save_project have already run, so the outputs below
	# are complete regardless. Bound it instead of trusting a clean exit.
	timeout --kill-after=10 300 $(FLATCAM) --shellfile=$(abspath $(MILL_TCL)) --headless=1 || true
	python3 snapmaker_header.py $(GCODE_DIR)/top_isolation.nc $(GCODE_DIR)/top_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/bottom_isolation.nc $(GCODE_DIR)/bottom_isolation.snapmaker.nc
	python3 snapmaker_header.py $(GCODE_DIR)/drill.nc $(GCODE_DIR)/drill.snapmaker.nc

clean:
	rm -f $(PDF) $(SVG)
	rm -rf $(GERBER_DIR) $(MILL_TCL)
