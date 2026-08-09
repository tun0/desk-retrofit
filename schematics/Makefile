PYSRC := $(wildcard sch_*.py)
KICAD_SCH := $(PYSRC:sch_%.py=desk_%.kicad_sch)
PDF := $(KICAD_SCH:.kicad_sch=.pdf)
SVG := $(KICAD_SCH:.kicad_sch=.svg)

.PHONY: all clean
.PRECIOUS: $(KICAD_SCH)
all: $(KICAD_SCH) $(PDF) $(SVG)

desk_%.kicad_sch: sch_%.py schlib.py symbols.py
	python3 $<

%.pdf: %.kicad_sch
	kicad-cli sch export pdf $<

%.svg: %.kicad_sch
	kicad-cli sch export svg $<

clean:
	rm -f $(PDF) $(SVG)
