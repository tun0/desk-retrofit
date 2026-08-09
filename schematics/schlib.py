#!/usr/bin/env python3
"""Minimal schematic drawing library that emits real KiCad schematics:
conventional symbol graphics, deliberate placement, drawn wires, junctions.

Unlike the earlier generators this does NOT rely on a label stub per pin.
Wires are routed between actual pin coordinates.
"""
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
                 ref_dx=0.0, val_dx=0.0):
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

    def offset(self, number):
        for num, nm, et, x, y, a, ln in self.pins:
            if num == number:
                return x, y
        raise KeyError(f"{self.name} has no pin {number}")

    def definition(self):
        o = [f'    (symbol "L:{self.name}"',
             f'      (pin_names (offset 0.762)'
             + (" hide" if self.hide_names else "") + ")",
             "      (pin_numbers" + (" hide" if self.hide_numbers else "")
             + ")",
             "      (in_bom yes) (on_board yes)",
             f'      (property "Reference" "{self.prefix}" '
             f"(at 0 {self.ref_dy:.2f} 0) {F})",
             f'      (property "Value" "{self.name}" '
             f"(at 0 {self.val_dy:.2f} 0) {F})",
             f'      (property "Footprint" "" (at 0 0 0) {FH})',
             f'      (property "Datasheet" "" (at 0 0 0) {FH})',
             f'      (symbol "{self.name}_0_1"']
        o += ["        " + g for g in self.graphics]
        o.append("      )")
        o.append(f'      (symbol "{self.name}_1_1"')
        for num, nm, et, x, y, a, ln in self.pins:
            o.append(f"        (pin {et} line (at {x:.2f} {y:.2f} {a}) "
                     f"(length {ln:.2f})")
            o.append(f'          (name "{esc(nm)}" {F})')
            o.append(f'          (number "{esc(num)}" {F}))')
        o.append("      )")
        o.append("    )")
        return "\n".join(o)


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


def stext(t, x, y, size=1.27):
    return (f'(text "{esc(t)}" (at {x:.2f} {y:.2f} 0) '
            f"(effects (font (size {size} {size}))))")


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
              hide_ref=False, hide_val=False):
        self.used[sym.name] = sym
        self.placed[ref] = (sym, x, y)
        rx, ry = ref_at if ref_at else (x + sym.ref_dx, y - sym.ref_dy)
        vx, vy = val_at if val_at else (x + sym.val_dx, y - sym.val_dy)
        rf = FH if hide_ref else F
        vf = FH if hide_val else FS
        b = [f'  (symbol (lib_id "L:{sym.name}") (at {x:.2f} {y:.2f} 0) '
             f"(unit 1)",
             "    (in_bom yes) (on_board yes) (dnp no)",
             f'    (uuid "{uid("i")}")',
             f'    (property "Reference" "{esc(ref)}" '
             f"(at {rx:.2f} {ry:.2f} 0) {rf})",
             f'    (property "Value" "{esc(value)}" '
             f"(at {vx:.2f} {vy:.2f} 0) {vf})",
             f'    (property "Footprint" "" (at {x:.2f} {y:.2f} 0) {FH})',
             f'    (property "Datasheet" "" (at {x:.2f} {y:.2f} 0) {FH})']
        for num, nm, et, px, py, a, ln in sym.pins:
            b.append(f'    (pin "{num}" (uuid "{uid("p")}"))')
        b += ["    (instances",
              f'      (project "{esc(self.project)}"',
              f'        (path "/{self.root}" (reference "{esc(ref)}") '
              f"(unit 1))", "      )", "    )", "  )"]
        self.body.append("\n".join(b))

    def pin(self, ref, number):
        sym, x, y = self.placed[ref]
        px, py = sym.offset(number)
        return (round(x + px, 2), round(y - py, 2))

    # -- connectivity -------------------------------------------------------
    def wire(self, *pts):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
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
            self.body.append(
                f"  (junction (at {x:.2f} {y:.2f}) (diameter 0) "
                f"(color 0 0 0 0)\n    (uuid \"{uid('j')}\")\n  )")

    def label(self, name, x, y, angle=0, justify="left bottom"):
        self.body.append(
            f'  (label "{esc(name)}" (at {x:.2f} {y:.2f} {angle})\n'
            f"    (effects (font (size 1.27 1.27)) (justify {justify}))\n"
            f"    (uuid \"{uid('l')}\")\n  )")

    def glabel(self, name, x, y, angle=0, shape="bidirectional"):
        self.body.append(
            f'  (global_label "{esc(name)}" (shape {shape}) '
            f"(at {x:.2f} {y:.2f} {angle}) (fields_autoplaced)\n"
            f"    (effects (font (size 1.27 1.27)) (justify left))\n"
            f"    (uuid \"{uid('g')}\")\n  )")

    def note(self, text, x, y, size=1.27):
        self.body.append(
            f'  (text "{esc(text)}" (at {x:.2f} {y:.2f} 0)\n'
            f"    (effects (font (size {size} {size})) "
            f"(justify left bottom))\n"
            f"    (uuid \"{uid('t')}\")\n  )")

    def box(self, x1, y1, x2, y2):
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
