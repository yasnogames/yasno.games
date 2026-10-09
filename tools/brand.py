"""Generate the Yasno logo files from the typefaces' own outlines.

Every mark is shaped with HarfBuzz and written as SVG paths, so no SVG needs
a font installed; every PNG is rendered from those SVGs, so the two never
disagree. Output goes under public/: the brand kit in public/brand/, plus the
favicon, the touch icon and the link preview the page names.

    python -I tools/brand.py
"""
import pathlib

import resvg_py
import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
PUBLIC = ROOT / "public"
BRAND = PUBLIC / "brand"

INK = "#121417"
PAPER = "#F5F5F2"
MUTED = "#4A4F57"
MUTED_ON_DARK = "#B4B9C0"
WHITE = "#FFFFFF"
ACCENT = "#2B6CF6"
ACCENT_ON_DARK = "#5B8DFF"


def number(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Typeface:
    def __init__(self, file, weight):
        self.face = hb.Face(hb.Blob.from_file_path(str(FONTS / file)))
        self.font = hb.Font(self.face)
        self.font.set_variations({"wght": weight})


class Run:
    """One line of text as outlines, baseline at y = 0, y pointing down.

    `fills` gives each glyph its colour, in order; the last entry repeats.
    `tracking` is letter-spacing in em, as CSS applies it between glyphs.
    """

    def __init__(self, typeface, text, size, tracking, fills):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(typeface.font, buf, {})
        scale = size / typeface.face.upem
        x = 0.0
        self.paths = []
        bounds = None
        for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
            t = (scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale)
            svg = SVGPathPen(None, ntos=number)
            box = BoundsPen(None)
            typeface.font.draw_glyph_with_pen(info.codepoint, TransformPen(svg, t))
            typeface.font.draw_glyph_with_pen(info.codepoint, TransformPen(box, t))
            if box.bounds:
                self.paths.append((svg.getCommands(), fills[min(i, len(fills) - 1)]))
                bounds = box.bounds if bounds is None else union(bounds, box.bounds)
            x += pos.x_advance * scale + tracking * size
        self.bounds = bounds

    def svg(self, dx, dy):
        body = "".join(f'<path fill="{fill}" d="{d}"/>' for d, fill in self.paths)
        return f'<g transform="translate({number(dx)} {number(dy)})">{body}</g>'


def union(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def stack(runs, gap):
    """Lines centred on x = 0, the first ink top at y = 0, `gap` between inks."""
    parts, y, bounds = [], 0.0, None
    for run in runs:
        x0, y0, x1, y1 = run.bounds
        dx, dy = -(x0 + x1) / 2, y - y0
        parts.append(run.svg(dx, dy))
        placed = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
        bounds = placed if bounds is None else union(bounds, placed)
        y = placed[3] + gap
    return "".join(parts), bounds


def document(width, height, body, background=None, view=None):
    view = view or (0, 0, width, height)
    ground = f'<rect width="{number(width)}" height="{number(height)}" fill="{background}"/>' if background else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(width)}" height="{number(height)}" '
        f'viewBox="{" ".join(number(v) for v in view)}">{ground}{body}</svg>\n'
    )


def fitted(width, height, body, bounds, fraction, background=None, area=None):
    """`body` scaled to fill `fraction` of the frame's width or height, centred.
    `area`, a width and height, fits it to that much of the middle instead."""
    x0, y0, x1, y1 = bounds
    aw, ah = area or (width, height)
    k = min(aw * fraction / (x1 - x0), ah * fraction / (y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    g = (f'<g transform="translate({number(width / 2)} {number(height / 2)}) scale({k:.5f}) '
         f'translate({number(-cx)} {number(-cy)})">{body}</g>')
    return document(width, height, g, background)


UNBOUNDED_BOLD = Typeface("Unbounded.ttf", 700)
UNBOUNDED_HEAVY = Typeface("Unbounded.ttf", 800)
MONO = Typeface("JetBrainsMono.ttf", 400)


def wordmark(letters, dot):
    run = Run(UNBOUNDED_BOLD, "yasno.", 1000, -0.03, [letters] * 5 + [dot])
    x0, y0, x1, y1 = run.bounds
    return document(x1 - x0, y1 - y0, run.svg(0, 0), view=(x0, y0, x1 - x0, y1 - y0))


def monogram(ground, letter, dot=None, square=False):
    """я in a circle or a square 1000 across, centred on its ink at half the frame's height
    in type. A `dot` sets я. instead; the circle needs none, being the dot itself."""
    run = Run(UNBOUNDED_HEAVY, "я." if dot else "я", 500, -0.04, [letter, dot])
    x0, y0, x1, y1 = run.bounds
    shape = (f'<rect width="1000" height="1000" fill="{ground}"/>' if square
             else f'<circle cx="500" cy="500" r="500" fill="{ground}"/>')
    return document(1000, 1000, shape + run.svg(500 - (x0 + x1) / 2, 500 - (y0 + y1) / 2))


def signature(letters, dot, muted):
    """The wordmark over the tagline."""
    mark = Run(UNBOUNDED_BOLD, "yasno.", 1000, -0.03, [letters] * 5 + [dot])
    line = Run(MONO, "games. got it.", 180, 0.02, [muted])
    return stack([mark, line], 190)


def preview():
    """The link preview: the signature on paper, 1200 x 630."""
    body, bounds = signature(INK, ACCENT, MUTED)
    return fitted(1200, 630, body, bounds, 0.62, PAPER)


def banner(ground, letters, dot, muted):
    """The YouTube channel banner, 2560 x 1440: the signature inside the 1235 x 338
    middle that every device shows; TVs show the whole frame, phones only that."""
    body, bounds = signature(letters, dot, muted)
    return fitted(2560, 1440, body, bounds, 0.86, ground, area=(1235, 338))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def render(path, svg, size):
    path.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=size, height=size)))


def main():
    files = {
        BRAND / "yasno-wordmark.svg": wordmark(INK, ACCENT),
        BRAND / "yasno-wordmark-reversed.svg": wordmark(PAPER, ACCENT_ON_DARK),
        BRAND / "yasno-monogram.svg": monogram(ACCENT, WHITE),
        BRAND / "yasno-monogram-square.svg": monogram(PAPER, INK, ACCENT, square=True),
        BRAND / "yasno-monogram-square-reversed.svg": monogram(INK, PAPER, ACCENT_ON_DARK, square=True),
        PUBLIC / "favicon.svg": monogram(ACCENT, WHITE),
    }
    for path, svg in files.items():
        write(path, svg)
    for name, svg in (("yasno-banner", banner(PAPER, INK, ACCENT, MUTED)),
                      ("yasno-banner-reversed", banner(INK, PAPER, ACCENT_ON_DARK, MUTED_ON_DARK))):
        (BRAND / f"{name}.png").write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg)))

    for name in ("yasno-monogram", "yasno-monogram-square", "yasno-monogram-square-reversed"):
        render(BRAND / f"{name}.png", files[BRAND / f"{name}.svg"], 1024)
    # iOS cuts its own corners, so the touch icon is a square edge to edge.
    render(PUBLIC / "apple-touch-icon.png", files[BRAND / "yasno-monogram-square.svg"], 180)
    (PUBLIC / "og.png").write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=preview())))


if __name__ == "__main__":
    main()
