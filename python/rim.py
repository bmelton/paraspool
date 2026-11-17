# /// script
# requires-python = ">=3.10"
# dependencies = ["manifold3d>=3", "fonttools"]
# ///
"""Paraspool rim adapter, rendered in Python with manifold3d (no OpenSCAD needed).

Port of openscad/src/rim.scad. Same parameters, same geometry; label text comes
from the bundled stencil font via fontTools.

    uv run python/rim.py --diameter 199.5 --label POLYMAKER -o paraspool.stl
"""
from __future__ import annotations

import io
import struct
from pathlib import Path

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from manifold3d import CrossSection, FillRule, Manifold

DEFAULT_FONT = Path(__file__).resolve().parent.parent / "openscad" / "fonts" / "AllertaStencil-Regular.ttf"
SEGMENTS = 200  # $fn in rim.scad
CURVE_STEPS = 8  # line segments per bezier in glyph outlines


class _FlatPen(BasePen):
    """Flattens glyph outlines into polylines (BasePen splits quads/cubics into single curves)."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours: list[list[tuple[float, float]]] = []

    def _moveTo(self, p):
        self.contours.append([p])

    def _lineTo(self, p):
        self.contours[-1].append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.contours[-1][-1]
        for i in range(1, CURVE_STEPS + 1):
            t = i / CURVE_STEPS
            u = 1 - t
            self.contours[-1].append(tuple(
                u * u * u * a + 3 * u * u * t * b + 3 * u * t * t * c + t * t * t * d
                for a, b, c, d in zip(p0, p1, p2, p3)))

    def _closePath(self):
        pass

    def _endPath(self):
        pass


def text_section(text: str, size: float, font: bytes | str | Path = DEFAULT_FONT) -> CrossSection:
    """2D text like OpenSCAD text(halign="center", valign="center").

    OpenSCAD sizes type at 100 dpi, so `size` points -> em of size*100/72 mm.
    """
    tt = TTFont(io.BytesIO(font) if isinstance(font, bytes) else str(font))
    scale = size * 100 / 72 / tt["head"].unitsPerEm
    cmap, hmtx, glyphs = tt.getBestCmap(), tt["hmtx"], tt.getGlyphSet()
    # ponytail: no kerning; OpenSCAD shapes with HarfBuzz, differences are sub-mm
    contours, x = [], 0.0
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        pen = _FlatPen(glyphs)
        glyphs[name].draw(pen)
        contours += [[(x + px, py) for px, py in c] for c in pen.contours if len(c) >= 3]
        x += hmtx[name][0]
    if not contours:
        return CrossSection()
    cs = CrossSection([np.array(c, dtype=float) * scale for c in contours], FillRule.NonZero)
    (x0, y0), (x1, y1) = np.array(cs.bounds()).reshape(2, 2)
    return cs.translate((-x * scale / 2, -(y0 + y1) / 2))


def build(diameter: float, label: str = "", *, tolerance: float = 0.4, rim_width: float = 6, lip_height: float = 6,
          wall_thickness: float = 1, font_size: float = 8, plate_depth: float = 17,
          font: bytes | str | Path = DEFAULT_FONT) -> Manifold:
    """The L-profile ring plus (if label) the stencil nameplate, mirroring rim.scad."""
    lip_inner_d = diameter + tolerance
    lip_outer_d = lip_inner_d + wall_thickness * 2
    hole_d = lip_inner_d - rim_width * 2
    circ = lambda d: CrossSection.circle(d / 2, SEGMENTS)

    ring = Manifold.extrude(circ(lip_outer_d) - circ(hole_d), wall_thickness) + \
        Manifold.extrude(circ(lip_outer_d) - circ(lip_inner_d), lip_height)
    if not label:
        return ring

    plate = CrossSection.square((lip_outer_d, plate_depth)).translate((-lip_outer_d / 2, -hole_d / 2)) ^ circ(hole_d)
    stencil = text_section(label, font_size, font).mirror((1, 0)).translate((0, -hole_d / 2 + plate_depth / 2))
    return ring + Manifold.extrude(plate - stencil, wall_thickness)


def triangles(m: Manifold) -> np.ndarray:
    """(n, 3, 3) float32 vertex array."""
    mesh = m.to_mesh()
    return np.asarray(mesh.vert_properties, dtype=np.float32)[np.asarray(mesh.tri_verts), :3]


def stl_bytes(m: Manifold) -> bytes:
    tri = triangles(m)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(tri), dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    rec["n"], rec["v"] = n, tri.reshape(-1, 9)
    return b"paraspool".ljust(80, b"\0") + struct.pack("<I", len(tri)) + rec.tobytes()


def _selfcheck():
    # Reference numbers come from rendering rim.scad with OpenSCAD 2025 (Manifold backend).
    m = build(199.5, "POLYMAKER")
    assert m.status().name == "NoError"
    assert np.allclose(m.bounding_box(), [-100.95, -100.95, 0, 100.95, 100.95, 6], atol=1e-3), m.bounding_box()
    assert abs(m.volume() - 8498.3) < 2, m.volume()
    t = Manifold.extrude(text_section("POLYMAKER", 8), 1)
    assert np.allclose(t.bounding_box(), [-32.606, -4.085, 0, 32.834, 4.085, 1], atol=0.01), t.bounding_box()
    assert build(200).volume() < m.volume()  # ring only, no plate
    print(f"selfcheck ok: {m.num_tri()} tris, volume {m.volume():.0f} mm^3")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--diameter", type=float, help="spool diameter in mm (omit to run the self-check)")
    ap.add_argument("--label", default="")
    ap.add_argument("-o", "--out", default="paraspool.stl")
    for k, d in (("tolerance", 0.4), ("rim-width", 6), ("lip-height", 6), ("wall-thickness", 1), ("font-size", 8), ("plate-depth", 17)):
        ap.add_argument("--" + k, type=float, default=d)
    a = ap.parse_args()
    if a.diameter is None:
        _selfcheck()
    else:
        m = build(a.diameter, a.label, tolerance=a.tolerance, rim_width=a.rim_width, lip_height=a.lip_height,
                  wall_thickness=a.wall_thickness, font_size=a.font_size, plate_depth=a.plate_depth)
        Path(a.out).write_bytes(stl_bytes(m))
        print(f"wrote {a.out} ({m.num_tri()} triangles)")
