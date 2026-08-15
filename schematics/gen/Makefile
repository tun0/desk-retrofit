SCH := ../desk.kicad_sch
PDF := ../desk.pdf
SVG := ../desk.svg

CHECKS := find_shorts.py find_diagonals.py find_crossings.py find_body_crossings.py

.PHONY: all clean check
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

clean:
	rm -f $(PDF) $(SVG)
