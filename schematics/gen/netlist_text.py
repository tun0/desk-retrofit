#!/usr/bin/env python3
"""Render a .kicad_sch as plain, deterministically-ordered text: component
list + net list, derived from Kicad's own netlist export (not from the
generator source), so it reflects actual connectivity.

Two uses:
  1. A human-readable reference for understanding the circuit, or
     rebuilding it by hand, without opening Kicad.
  2. Diffing: Kicad has no schematic-vs-schematic diff tool, but two
     variants (or two commits) of the same design can be compared by
     running this on each and diffing the text output - real electrical
     differences show up as added/removed/changed lines; layout-only
     changes (pin position, routing) don't, since none of that is in
     Kicad's netlist.

Usage:
    python3 netlist_text.py desk.kicad_sch
    python3 netlist_text.py desk.kicad_sch > a.txt
    # ... change the design ...
    python3 netlist_text.py desk.kicad_sch > b.txt
    diff a.txt b.txt
"""
import subprocess
import sys
import tempfile

import defusedxml.ElementTree as ET


def netlist_xml(sch_path):
    with tempfile.NamedTemporaryFile(suffix=".xml") as tmp:
        subprocess.run(
            ["kicad-cli", "sch", "export", "netlist", "--format",
             "kicadxml", "-o", tmp.name, sch_path],
            check=True, capture_output=True)
        return ET.parse(tmp.name).getroot()


def render(root):
    out = []
    out.append("# COMPONENTS")
    comps = root.find("components")
    rows = []
    for c in comps.findall("comp"):
        ref = c.get("ref")
        value_el = c.find("value")
        value = value_el.text if value_el is not None and \
            value_el.text else ""
        rows.append((ref, value))
    for ref, value in sorted(rows, key=lambda r: r[0]):
        out.append(f"{ref}: {value}")

    out.append("")
    out.append("# NETS")
    nets = root.find("nets")
    net_rows = []
    for n in nets.findall("net"):
        name = n.get("name")
        pins = sorted(f"{nd.get('ref')}.{nd.get('pin')}"
                      for nd in n.findall("node"))
        if pins:
            net_rows.append((name, pins))
    for name, pins in sorted(net_rows, key=lambda r: r[0]):
        out.append(f"{name}: {', '.join(pins)}")
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <schematic.kicad_sch>",
              file=sys.stderr)
        sys.exit(1)
    root = netlist_xml(sys.argv[1])
    sys.stdout.write(render(root))


if __name__ == "__main__":
    main()
