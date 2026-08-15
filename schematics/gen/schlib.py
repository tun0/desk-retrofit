#!/usr/bin/env python3
"""Minimal schematic drawing library that emits real KiCad schematics:
conventional symbol graphics, deliberate placement, drawn wires, junctions.

Unlike the earlier generators this does NOT rely on a label stub per pin.
Wires are routed between actual pin coordinates.
"""
import re as _re
import uuid as _uuid

VERSION = 20230121
NS = _uuid.UUID("2b9f4d17-8c3a-4e51-a0d2-77e1b5c9f402")
_c = [0]


def uid(tag=""):
    _c[0] += 1
    return str(_uuid.uuid5(NS, f"{tag}:{_c[0]}"))


def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


F = "(effects (font (size 1.27 1.27)))"
FH = "(effects (font (size 1.27 1.27)) hide)"
FS = "(effects (font (size 1.0 1.0)))"
STROKE = "(stroke (width 0.2032) (type default))"
NOFILL = "(fill (type none))"
BGFILL = "(fill (type background))"


class Sym:
    """name, pins: list of (number, name, etype, x, y, angle, length),
    graphics: list of raw s-expression strings in symbol coordinates."""

    def __init__(self, name, prefix, pins, graphics, hide_names=True,
                 hide_numbers=True, ref_dy=8.89, val_dy=-8.89,
                 ref_dx=0.0, val_dx=0.0, power=False, justify=None):
        self.name = name
        self.prefix = prefix
        self.pins = pins
        self.graphics = graphics
        self.hide_names = hide_names
        self.hide_numbers = hide_numbers
        self.ref_dy = ref_dy
        self.val_dy = val_dy
        self.ref_dx = ref_dx
        self.val_dx = val_dx
        # Default text justification when a place() call doesn't pass its
        # own - lets an imported symbol carry the real part's own label
        # style (e.g. "beside, left-justified") without every call site
        # needing to repeat it.
        self.justify = justify
        # Without this, separate placements of e.g. GND are just ordinary
        # components that happen to share a value string - Kicad only
        # merges them into one global net when the symbol itself is
        # flagged as a power symbol (found by diffing against a real
        # Kicad-placed power symbol; every GND/rail tap in this project
        # was silently floating on its own isolated net before this).
        self.power = power

    def offset(self, number):
        for pin in self.pins:
            if pin[0] == number:
                return pin[3], pin[4]
        raise KeyError(f"{self.name} has no pin {number}")

    def _header(self):
        return [f'    (symbol "L:{self.name}"'] + \
               (["      (power global)"] if self.power else []) + \
               [f'      (pin_names (offset 0.762)'
                + (" hide" if self.hide_names else "") + ")",
                "      (pin_numbers" +
                (" hide" if self.hide_numbers else "") + ")",
                "      (in_bom yes) (on_board yes)",
                f'      (property "Reference" "{self.prefix}" '
                f"(at 0 {self.ref_dy:.2f} 0) {F})",
                f'      (property "Value" "{self.name}" '
                f"(at 0 {self.val_dy:.2f} 0) {F})",
                f'      (property "Footprint" "" (at 0 0 0) {FH})',
                f'      (property "Datasheet" "" (at 0 0 0) {FH})']

    @staticmethod
    def _pin_lines(pins):
        o = []
        for pin in pins:
            num, nm, et, x, y, a, ln = pin[:7]
            style = pin[7] if len(pin) > 7 else "line"
            o.append(f"        (pin {et} {style} (at {x:.2f} {y:.2f} {a}) "
                     f"(length {ln:.2f})")
            o.append(f'          (name "{esc(nm)}" {F})')
            o.append(f'          (number "{esc(num)}" {F}))')
        return o

    def definition(self):
        o = self._header()
        o.append(f'      (symbol "{self.name}_0_1"')
        o += ["        " + g for g in self.graphics]
        o.append("      )")
        o.append(f'      (symbol "{self.name}_1_1"')
        o += self._pin_lines(self.pins)
        o.append("      )")
        o.append("    )")
        return "\n".join(o)


def _find_balanced(text, start):
    """start indexes the '(' that opens the block; returns the index one
    past its matching ')'."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced parens")


class ImportedSym(Sym):
    """A real Kicad library symbol, embedded verbatim - only the
    top-level symbol name is renamed to our "L:" embedding convention;
    Kicad's own sub-unit names (e.g. "Relay_SPDT_1_1") are left bare.
    Prefixing those too is what broke this the first time: Kicad looks
    up a unit's drawing by the bare part name regardless of what nickname
    the top-level lib_id uses, so a prefixed sub-unit name couldn't be
    found and the file failed to load.

    Verbatim means every visual detail - fill colour, inverted-pin
    bubbles, arcs, exact default label placement - is Kicad's own
    authored data, not our reconstruction of it. No separate graphics
    parsing is needed at all; only pins are pulled out, and only because
    place()/pin() need real coordinates to route against.

    Real parts aren't sacred: pins_by_unit is a plain dict of plain
    (number, name, etype, x, y, angle, length, style) tuples, editable
    exactly like a hand-drawn Sym's pin list (reorder them, move one to
    the other side, whatever routing needs) - definition() re-syncs the
    embedded (at ...)/(length ...) for each pin from whatever's in
    pins_by_unit right before rendering, so an edit there is guaranteed
    to match what's actually drawn instead of silently drifting from it.
    """

    def __init__(self, name, raw, pins_by_unit, prefix="U",
                 ref_dy=10.0, val_dy=-10.0, ref_dx=0.0, val_dx=0.0,
                 justify=None):
        pins = pins_by_unit.get(1, next(iter(pins_by_unit.values()), []))
        super().__init__(name, prefix, pins, [], ref_dy=ref_dy,
                          val_dy=val_dy, ref_dx=ref_dx, val_dx=val_dx,
                          justify=justify)
        self.pins_by_unit = pins_by_unit
        self._raw = raw

    def offset(self, number, unit=1):
        for pin in self.pins_by_unit.get(unit, []):
            if pin[0] == number:
                return pin[3], pin[4]
        raise KeyError(f"{self.name} unit {unit} has no pin {number}")

    def definition(self):
        flat = {}
        for pins in self.pins_by_unit.values():
            for pin in pins:
                flat[pin[0]] = pin

        def _sub(m):
            pre, etype, mid1, x, y, a, mid2, ln, tail, num = m.groups()
            if num in flat:
                pin = flat[num]
                etype = pin[2]
                _, _, _, x, y, a, ln = pin[:7]
            else:
                x, y, ln = float(x), float(y), float(ln)
            return f"{pre}{etype}{mid1}{x:.2f} {y:.2f} {a}{mid2}{ln:.2f}{tail}"
        return _PIN_BLOCK_RE.sub(_sub, self._raw)


_PIN_RE = _re.compile(
    r"\(pin (\w+) (\w+)\s*"  # etype, then graphic style (line/inverted/
    # clock/... - inverted draws the little bubble on an active-low pin;
    # kept (not just matched-and-dropped) so pins_by_unit reflects it,
    # though the verbatim raw text is what actually draws it either way.
    r"\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)\s*"
    r"\(length ([\d.]+)\).*?"
    r'\(name "([^"]*)".*?'
    r'\(number "([^"]*)"', _re.S)

# Same shape as _PIN_RE but grouped for in-place substitution in the raw
# text: etype split out on its own (editable the same way position is -
# e.g. overriding a real part's "output" pin to "power_out" so Kicad's
# ERC treats it as a real power source), then x/y/angle/length, then
# everything up to (and including) the number that identifies which pin
# this is - definition() uses that to look up the current position.
_PIN_BLOCK_RE = _re.compile(
    r'(\(pin )(\w+)( \w+\s*\(at )([\-\d.]+) ([\-\d.]+) (\d+)(\)\s*\(length )'
    r'([\d.]+)(\).*?\(number "([^"]*)")', _re.S)


def _parse_label_offset(block, prop_name):
    """Pull a top-level "Reference"/"Value" property's own (at dx dy a)
    and justify out of a real Kicad symbol block - this is Kicad's own
    authored default label position for the part (what you get before
    ever dragging the label), so it's a better starting point than
    guessing. Only reliable for parts with one fixed representation
    (a single unit/style): multi-unit ICs autoplace each unit's labels
    against that unit's own bounding box, which this static value can't
    capture - callers of import_symbol() still pass explicit ref_dy/
    val_dy for those (see MONO/AND2 in symbols.py)."""
    m = _re.search(r'\(property "' + prop_name + r'" "[^"]*"\s*'
                   r'\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)', block)
    if not m:
        return None
    end = _find_balanced(block, m.start())
    justify_m = _re.search(r"\(justify (\w+)", block[m.start():end])
    return (float(m.group(1)), float(m.group(2)),
            justify_m.group(1) if justify_m else None)


def import_symbol(path, name, prefix="U", ref_dy=None, val_dy=None,
                   ref_dx=None, val_dx=None):
    """Load `name` verbatim out of a real Kicad library file (e.g. one of
    Kicad's own global libraries under /usr/share/kicad/symbols/) instead
    of hand-drawing an equivalent - the project stays self-contained (no
    external lib dependency at open-time) because the block is embedded
    the same way a hand-drawn Sym's definition() is, just copied rather
    than generated. Pin name/number visibility comes from whatever the
    real part itself specifies (unlike a hand-drawn Sym, there's no
    hide_names/hide_numbers override here - overriding would mean
    patching Kicad's own pin_names/pin_numbers block, which isn't worth
    doing when every part encountered so far already defaults to a
    sensible visibility).

    ref_dy/val_dy/ref_dx/val_dx: leave as None to use the label position
    the real part's own library entry specifies; pass a value to override
    it (needed for multi-unit parts - see _parse_label_offset)."""
    text = open(path).read()
    m = _re.search(r'\(symbol "' + _re.escape(name) + r'"\s', text)
    if not m:
        raise KeyError(f'"{name}" not found in {path}')
    end = _find_balanced(text, m.start())
    block = text[m.start():end]
    raw = _re.sub(r'^\(symbol "' + _re.escape(name) + r'"',
                  f'(symbol "L:{name}"', block, count=1)

    # Sub-symbols are named "{name}_{unit}_{style}" - unit >=1 is a real
    # unit (a gate, a coil+contacts, shared power pins); which style
    # number actually carries a given unit's pins varies per part (some
    # put them under style 0, others style 1), so every style is
    # scanned and the first one with any pins is kept - Kicad duplicates
    # the same pin list verbatim across every style of a unit, so "first
    # one found" is never wrong.
    pins_by_unit = {}
    for sm in _re.finditer(r'\(symbol "' + _re.escape(name) +
                            r'_(\d+)_\d+"\s', block):
        unit = int(sm.group(1))
        sub_end = _find_balanced(block, sm.start())
        sub = block[sm.start():sub_end]
        pins = [(num, nm, et, float(x), float(y), int(a), float(ln), style)
                for et, style, x, y, a, ln, nm, num
                in _PIN_RE.findall(sub)]
        if pins and unit not in pins_by_unit:
            pins_by_unit[unit] = pins
    # Unit 0 means "common to every unit" - normally just shared
    # graphics with no pins of its own, but at least one real part
    # (Espressif's ESP32-S3-DevKitC) splits a single unit's pins across
    # its own "_0_1" and "_1_1" blocks instead of putting them all under
    # the real unit, so unit 0's pins (if any) are folded into every
    # other unit rather than dropped.
    if 0 in pins_by_unit:
        common = pins_by_unit.pop(0)
        if pins_by_unit:
            for unit in pins_by_unit:
                pins_by_unit[unit] = pins_by_unit[unit] + common
        else:
            pins_by_unit[1] = common
    if not pins_by_unit:
        raise ValueError(f'"{name}" in {path} has no pins')

    ref_lbl = _parse_label_offset(block, "Reference")
    val_lbl = _parse_label_offset(block, "Value")
    if ref_dx is None:
        ref_dx = ref_lbl[0] if ref_lbl else 0.0
    if ref_dy is None:
        ref_dy = ref_lbl[1] if ref_lbl else 10.0
    if val_dx is None:
        val_dx = val_lbl[0] if val_lbl else 0.0
    if val_dy is None:
        val_dy = val_lbl[1] if val_lbl else -10.0
    justify = ref_lbl[2] if ref_lbl else None

    return ImportedSym(name, raw, pins_by_unit, prefix, ref_dy, val_dy,
                        ref_dx, val_dx, justify)


# --- graphic helpers --------------------------------------------------------
def poly(pts, fill=NOFILL):
    p = " ".join(f"(xy {x:.2f} {y:.2f})" for x, y in pts)
    return f"(polyline (pts {p}) {STROKE} {fill})"


def circ(cx, cy, r, fill=NOFILL):
    return (f"(circle (center {cx:.2f} {cy:.2f}) (radius {r:.2f}) "
            f"{STROKE} {fill})")


def rect(x1, y1, x2, y2, fill=NOFILL):
    return (f"(rectangle (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f}) "
            f"{STROKE} {fill})")


def arc(sx, sy, mx, my, ex, ey, fill=NOFILL):
    """A three-point arc (start/mid/end) - Kicad's own representation, not
    a start+radius+angle one, so points parsed straight out of a real
    symbol can be re-emitted as-is with no conversion."""
    return (f"(arc (start {sx:.2f} {sy:.2f}) (mid {mx:.2f} {my:.2f}) "
            f"(end {ex:.2f} {ey:.2f}) {STROKE} {fill})")


def stext(t, x, y, size=1.27):
    return (f'(text "{esc(t)}" (at {x:.2f} {y:.2f} 0) '
            f"(effects (font (size {size} {size}))))")


GRID = 1.27  # Kicad's default fine grid (50 mil) - every symbol offset in
# symbols.py is already a multiple of this; snapping here catches anything
# arithmetic in sch.py produces that isn't (e.g. a /2 midpoint), so
# nothing needs hand-checking against the grid before drawing it.


def _snap(v):
    return round(round(v / GRID) * GRID, 2)


def _snap_pt(pt):
    return (_snap(pt[0]), _snap(pt[1]))


def _rotate(px, py, angle):
    if angle == 90:
        return -py, px
    if angle == 180:
        return -px, -py
    if angle == 270:
        return py, -px
    return px, py


class Schematic:
    def __init__(self, project, title, company="", paper="A3"):
        self.project = project
        self.title = title
        self.company = company
        self.paper = paper
        self.root = uid("root" + project)
        self.body = []
        self.used = {}
        self.placed = {}

    # -- placement ----------------------------------------------------------
    def place(self, sym, ref, value, x, y, ref_at=None, val_at=None,
              hide_ref=False, hide_val=False, mirror=None, angle=0, unit=1,
              justify=None):
        """mirror: None, "x" (flip vertically) or "y" (flip horizontally) -
        lets a two-pin part be wired straight instead of routed back
        across itself when its fixed pin layout is backwards for a
        given spot (e.g. a diode that needs the opposite orientation
        of its neighbour). angle: 0/90/180/270 - same idea, but turns
        the whole pin row instead of flipping it, for a part whose pins
        need to run along the other axis at this spot. unit: for a
        genuinely multi-unit part (e.g. one logic package with several
        gates, each its own unit) - place() is called once per unit, all
        sharing `ref`; single-unit parts never need to pass this."""
        x, y = _snap(x), _snap(y)
        self.used[sym.name] = sym
        self.placed.setdefault(ref, {})[unit] = (sym, x, y, mirror, angle)
        # Text angle counter-rotates the instance's own rotation - Kicad
        # otherwise renders Reference/Value sideways or upside-down
        # along with the symbol, which is not how rotated parts are
        # normally drawn (the part turns, the text stays upright). The
        # default offset itself still turns with the part, so it keeps
        # its position (e.g. "below the body") whichever way it faces.
        text_angle = (360 - angle) % 360
        if ref_at:
            rx, ry = _snap_pt(ref_at)
        else:
            rdx, rdy = _rotate(sym.ref_dx, sym.ref_dy, angle)
            rx, ry = _snap_pt((x + rdx, y - rdy))
        if val_at:
            vx, vy = _snap_pt(val_at)
        else:
            vdx, vdy = _rotate(sym.val_dx, sym.val_dy, angle)
            vx, vy = _snap_pt((x + vdx, y - vdy))
        if justify is None:
            justify = sym.justify
        just_clause = f" (justify {justify})" if justify else ""
        rf = FH if hide_ref else \
            f"(effects (font (size 1.27 1.27)){just_clause})"
        vf = FH if hide_val else \
            f"(effects (font (size 1.0 1.0)){just_clause})"
        mirror_clause = f" (mirror {mirror})" if mirror else ""
        b = [f'  (symbol (lib_id "L:{sym.name}") (at {x:.2f} {y:.2f} {angle})'
             f'{mirror_clause} '
             f"(unit {unit})",
             "    (in_bom yes) (on_board yes) (dnp no)",
             f'    (uuid "{uid("i")}")',
             f'    (property "Reference" "{esc(ref)}" '
             f"(at {rx:.2f} {ry:.2f} {text_angle}) {rf})",
             f'    (property "Value" "{esc(value)}" '
             f"(at {vx:.2f} {vy:.2f} {text_angle}) {vf})",
             f'    (property "Footprint" "" (at {x:.2f} {y:.2f} 0) {FH})',
             f'    (property "Datasheet" "" (at {x:.2f} {y:.2f} 0) {FH})']
        unit_pins = getattr(sym, "pins_by_unit", {}).get(unit, sym.pins)
        for pin in unit_pins:
            b.append(f'    (pin "{pin[0]}" (uuid "{uid("p")}"))')
        b += ["    (instances",
              f'      (project "{esc(self.project)}"',
              f'        (path "/{self.root}" (reference "{esc(ref)}") '
              f"(unit {unit}))", "      )", "    )", "  )"]
        self.body.append("\n".join(b))

    def pin(self, ref, number, unit=1):
        sym, x, y, mirror, angle = self.placed[ref][unit]
        px, py = sym.offset(number, unit) if isinstance(sym, ImportedSym) \
            else sym.offset(number)
        if mirror == "y":
            px = -px
        elif mirror == "x":
            py = -py
        px, py = _rotate(px, py, angle)
        return _snap_pt((x + px, y - py))

    # -- connectivity -------------------------------------------------------
    def wire(self, *pts):
        pts = [_snap_pt(p) for p in pts]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            # Two consecutive points can land on the same spot after
            # snapping (or just because two components' pins happen to
            # coincide) - drawing that segment anyway produces an
            # invisible zero-length wire, harmless electrically but
            # pointless.
            if (x1, y1) == (x2, y2):
                continue
            self.body.append(
                f"  (wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f}))\n"
                f"    {STROKE}\n    (uuid \"{uid('w')}\")\n  )")

    def hv(self, a, b):
        """Route a to b horizontally then vertically."""
        self.wire(a, (b[0], a[1]), b)

    def vh(self, a, b):
        self.wire(a, (a[0], b[1]), b)

    def junction(self, *pts):
        for x, y in pts:
            x, y = _snap(x), _snap(y)
            self.body.append(
                f"  (junction (at {x:.2f} {y:.2f}) (diameter 0) "
                f"(color 0 0 0 0)\n    (uuid \"{uid('j')}\")\n  )")

    def label(self, name, x, y, angle=0, justify="left bottom"):
        x, y = _snap(x), _snap(y)
        self.body.append(
            f'  (label "{esc(name)}" (at {x:.2f} {y:.2f} {angle})\n'
            f"    (effects (font (size 1.27 1.27)) (justify {justify}))\n"
            f"    (uuid \"{uid('l')}\")\n  )")

    def glabel(self, name, x, y, angle=0, shape="bidirectional"):
        # A label rotated 180 has its connection tip on the right, with
        # the wire approaching from that side, so the text must grow left
        # (right-justified) instead of running back over the wire.
        x, y = _snap(x), _snap(y)
        justify = "right" if angle == 180 else "left"
        self.body.append(
            f'  (global_label "{esc(name)}" (shape {shape}) '
            f"(at {x:.2f} {y:.2f} {angle}) (fields_autoplaced)\n"
            f"    (effects (font (size 1.27 1.27)) (justify {justify}))\n"
            f"    (uuid \"{uid('g')}\")\n  )")

    def note(self, text, x, y, size=1.27):
        x, y = _snap(x), _snap(y)
        self.body.append(
            f'  (text "{esc(text)}" (at {x:.2f} {y:.2f} 0)\n'
            f"    (effects (font (size {size} {size})) "
            f"(justify left bottom))\n"
            f"    (uuid \"{uid('t')}\")\n  )")

    def box(self, x1, y1, x2, y2):
        x1, y1 = _snap(x1), _snap(y1)
        x2, y2 = _snap(x2), _snap(y2)
        self.body.append(
            f"  (rectangle (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f})\n"
            f"    (stroke (width 0.1) (type dash)) (fill (type none))\n"
            f"    (uuid \"{uid('r')}\")\n  )")

    # -- output -------------------------------------------------------------
    def render(self):
        o = [f'(kicad_sch (version {VERSION}) (generator "eeschema")',
             f'  (uuid "{self.root}")',
             f'  (paper "{self.paper}")',
             "  (title_block",
             f'    (title "{esc(self.title)}")',
             f'    (company "{esc(self.company)}")',
             "  )",
             "  (lib_symbols"]
        for name in sorted(self.used):
            o.append(self.used[name].definition())
        o.append("  )")
        o += self.body
        o += ["  (sheet_instances", '    (path "/" (page "1"))', "  )", ")"]
        return "\n".join(o) + "\n"
