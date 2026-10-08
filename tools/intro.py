"""Generate public/intro.js: the site's mark, the round monogram that turns into the wordmark.

The circle pulses until a pointer reaches it or it is pressed; then, once, it shrinks into
the full stop while the я travels left, its top deforming into the a and its bottom into
the y (the tail growing as the arms tilt), sno slides in and the tagline types out behind
a caret that keeps blinking. Every shape comes from the typefaces' own outlines, as in
brand.py; the script only interpolates between them.

    python -I tools/intro.py
"""
import json
import math
import pathlib
import sys

import uharfbuzz as hb
from fontTools.pens.basePen import decomposeQuadraticSegment
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I leaves tools/ off the path
import brand  # noqa: E402
from brand import number as n  # noqa: E402

W, H = 1200, 540   # the drawing's frame
R = 220            # the circle's radius; the я is set at the same size, as in the kit
D = 6.5            # seconds the whole transform would take from the very start
SAMPLES = 260      # points per outline while it deforms
CUT = 0.62         # where the я splits into top and bottom, as a share of its height

# The timeline, as shares of D. The transform starts at START, skipping the hold.
START = 0.08
MOVE = [0.10, 0.36]        # circle into the dot, я over to where ya sits
INK = [0.10, 0.22]         # я from white to ink as the circle leaves it
MORPH = [0.36, 0.52]       # top into a, bottom into y, tail growing all the while
SLIDE = [0.50, 0.05, 0.10]  # s, n, o: first start, stagger, each one's length
CARET = 0.68
TYPE = [0.72, 0.018]       # first character, then one per step


def glyphs(typeface, text, size, tracking):
    """Each character: (path d, ink bounds or None, pen x before, pen x after)."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(typeface.font, buf, {})
    scale = size / typeface.face.upem
    x, out = 0.0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        t = (scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale)
        svg, bounds = SVGPathPen(None, ntos=n), BoundsPen(None)
        typeface.font.draw_glyph_with_pen(info.codepoint, TransformPen(svg, t))
        typeface.font.draw_glyph_with_pen(info.codepoint, TransformPen(bounds, t))
        start = x
        x += pos.x_advance * scale + tracking * size
        out.append((svg.getCommands(), bounds.bounds, start, x))
    return out


def strokes(typeface, codepoint, size, ox, oy):
    """A glyph's contours as polygons, (solids largest first, holes): the pieces the type
    designer drew, which for y are its two strokes and for я its body and leg."""
    scale = size / typeface.face.upem
    rec = RecordingPen()
    typeface.font.draw_glyph_with_pen(typeface.font.get_nominal_glyph(codepoint),
                                      TransformPen(rec, (scale, 0, 0, -scale, ox, oy)))
    rings, pts = [], []
    for op, args in rec.value:
        if op == "moveTo":
            pts = [args[0]]
        elif op == "lineTo":
            pts.append(args[0])
        elif op == "qCurveTo":
            for ctrl, on in decomposeQuadraticSegment(args):
                p0 = pts[-1]
                for k in range(1, 17):
                    t = k / 16
                    pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t * t * on[0],
                                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t * t * on[1]))
        elif op == "closePath":
            rings.append(pts)
    signed = lambda r: sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:] + r[:1]))
    solid = signed(max(rings, key=lambda r: abs(signed(r)))) > 0
    rings.sort(key=lambda r: -abs(signed(r)))
    return ([Polygon(r).buffer(0) for r in rings if (signed(r) > 0) == solid],
            [Polygon(r).buffer(0) for r in rings if (signed(r) > 0) != solid])


def outline(typeface, codepoint, size, ox, oy):
    """A glyph as one shape, its contours filled nonzero."""
    solids, holes = strokes(typeface, codepoint, size, ox, oy)
    fill = unary_union(solids)
    return fill.difference(unary_union(holes)) if holes else fill


def single(shape):
    """The one polygon in `shape`, wound so that nonzero fill cuts its holes."""
    assert shape.geom_type == "Polygon", shape.geom_type
    return orient(shape, 1.0)


def resample(coords, count):
    """`count` points spaced evenly along a closed ring."""
    ring = list(coords)
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    loop = ring + ring[:1]
    seg = [math.dist(a, b) for a, b in zip(loop, loop[1:])]
    total, out, i, run = sum(seg), [], 0, 0.0
    for k in range(count):
        want = total * k / count
        while i < len(seg) - 1 and run + seg[i] < want:
            run += seg[i]
            i += 1
        t = (want - run) / seg[i] if seg[i] else 0
        a, b = loop[i], loop[i + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def align(src, dst):
    """`dst` started at the point that lines it up closest with `src`."""
    best = min(range(len(dst)), key=lambda s: sum(
        (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for p, q in zip(src, dst[s:] + dst[:s])))
    return dst[best:] + dst[:best]


def flat(ring):
    return [round(v, 1) for p in ring for v in p]


def piece(src, dst, baseline=None):
    """`src` deforming into `dst`, ring for ring (outer, then holes).

    With a `baseline`, the part of `dst` below it is a tail that grows out of the stroke's
    foot as the rest deforms, like a pen drawing it: its two edges are measured from the
    foot to its tip, and each point the growing tip has not reached waits at the tip."""
    assert len(src.interiors) == len(dst.interiors), (len(src.interiors), len(dst.interiors))
    out = {"s": [], "d": [], "A": [], "B": [], "at": []}
    for s, t in zip([src.exterior, *src.interiors], [dst.exterior, *dst.interiors]):
        s = resample(s.coords, SAMPLES)
        t = align(s, resample(t.coords, SAMPLES))
        at, edge_a, edge_b = [0] * len(t), [], []
        below = [p[1] > baseline for p in t] if baseline else []
        if any(below):
            start = next(i for i in range(len(t)) if below[i] and not below[i - 1])
            run = []
            while below[(start + len(run)) % len(t)]:
                run.append((start + len(run)) % len(t))
            assert sum(below) == len(run), "the tail must be one run"
            tip = min(range(len(run)), key=lambda m: t[run[m]][0])
            for edge, ids in ((edge_a, run[:tip + 1]), (edge_b, run[tip:][::-1])):
                lengths = [0.0]
                for i, j in zip(ids, ids[1:]):
                    lengths.append(lengths[-1] + math.dist(t[i], t[j]))
                for i, length in zip(ids, lengths):
                    at[i] = round(length / lengths[-1], 3)
                edge.extend(ids)
        out["s"].append(flat(s))
        out["d"].append(flat(t))
        out["A"].append(edge_a)
        out["B"].append(edge_b)
        out["at"].append(at)
    return out


def ink(gs):
    bs = [g[1] for g in gs if g[1]]
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def centre(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def build():
    # The wordmark over the tagline, centred as one block, 36 between their inks.
    mark = glyphs(brand.UNBOUNDED_BOLD, "yasno.", 190, -0.03)
    line = glyphs(brand.MONO, "games. got it.", 34, 0.02)
    mb, lb = ink(mark), ink(line)
    gap = 36
    top = (H - ((mb[3] - mb[1]) + gap + (lb[3] - lb[1]))) / 2
    mx, my = W / 2 - (mb[0] + mb[2]) / 2, top - mb[1]
    lx, ly = W / 2 - (lb[0] + lb[2]) / 2, top + (mb[3] - mb[1]) + gap - lb[1]

    ya_c = centre(ink(mark[:2]))
    ya_c = (ya_c[0] + mx, ya_c[1] + my)
    dot_b = mark[5][1]
    dot_c = (centre(dot_b)[0] + mx, centre(dot_b)[1] + my)
    dot_r = ((dot_b[2] - dot_b[0]) + (dot_b[3] - dot_b[1])) / 4

    # The я, drawn centred where ya will sit; the script carries it there from the circle.
    g = outline(brand.UNBOUNDED_HEAVY, 0x44F, R, 0, 0).bounds
    ox, oy = ya_c[0] - (g[0] + g[2]) / 2, ya_c[1] - (g[1] + g[3]) / 2
    cyr = outline(brand.UNBOUNDED_HEAVY, 0x44F, R, ox, oy)
    x0, y0, x1, y1 = cyr.bounds
    cut = y0 + (y1 - y0) * CUT
    upper = single(cyr.intersection(box(x0 - 1, y0 - 1, x1 + 1, cut + 0.75)))  # a hair of overlap: no seam
    lower = box(x0 - 1, cut - 0.75, x1 + 1, y1 + 1)
    (body, leg), _ = strokes(brand.UNBOUNDED_HEAVY, 0x44F, R, ox, oy)
    # The y's two strokes: the left arm, and the right arm that runs on into the tail.
    (right, left), _ = strokes(brand.UNBOUNDED_BOLD, ord("y"), 190, mx + mark[0][2], my)
    a = single(outline(brand.UNBOUNDED_BOLD, ord("a"), 190, mx + mark[1][2], my))
    morph = {
        "top": piece(upper, a),
        "leg": piece(single(leg.intersection(lower)), single(left)),
        "stem": piece(single(body.intersection(lower)), single(right), baseline=left.bounds[3]),
    }

    data = {
        "W": W, "H": H, "D": D, "R": R, "start": START,
        "dot": [round(dot_c[0], 2), round(dot_c[1], 2), round(dot_r, 2)],
        "from": [round(W / 2 - ya_c[0], 2), round(H / 2 - ya_c[1], 2)],
        "morph": morph,
        "typed": [round(g[2], 2) for g in line] + [round(line[-1][3], 2)],
        "glyphs": len(line),
        "t": {"move": MOVE, "ink": INK, "morph": MORPH, "slide": SLIDE, "caret": CARET, "type": TYPE},
    }

    # The drawing. data-bind-<attribute>="<key>" takes that key of each frame. Colours come
    # from the page's theme through the classes.
    parts = [f'<svg viewBox="0 0 {W} {H}" aria-hidden="true" focusable="false">',
             f'<circle class="ring" cx="{n(W / 2)}" cy="{n(H / 2)}" r="{R}" data-bind-transform="ringT" '
             'data-bind-opacity="ringO"/>',
             f'<circle cx="{n(W / 2)}" cy="{n(H / 2)}" r="{R}" data-bind-transform="discT" '
             'data-bind-fill="discFill" data-bind-opacity="discO"/>',
             '<g data-bind-transform="cyrT" data-bind-fill="cyrFill" data-bind-opacity="morphO">'
             '<path data-bind-d="top"/><path data-bind-d="leg"/><path data-bind-d="stem"/></g>',
             f'<g class="ink" transform="translate({n(mx)} {n(my)})">',
             '<g data-bind-opacity="yaO">' + "".join(f'<path d="{g[0]}"/>' for g in mark[:2]) + "</g>"]
    for i, g in enumerate(mark[2:5]):
        parts.append(f'<path d="{g[0]}" data-bind-transform="l{i}T" data-bind-opacity="l{i}O"/>')
    parts.append(f'<path class="dot" d="{mark[5][0]}" data-bind-opacity="stopO"/></g>')
    parts.append(f'<g class="muted" transform="translate({n(lx)} {n(ly)})">')
    for i, g in enumerate(line):
        if g[1]:
            parts.append(f'<path d="{g[0]}" data-bind-opacity="t{i}"/>')
    parts.append('<g data-bind-transform="caretT" data-bind-opacity="caretO">'
                 f'<rect x="2" y="{n(lb[1])}" width="3" height="{n(lb[3] - lb[1])}"/></g></g></svg>')
    return data, "".join(parts)


SCRIPT = """// Generated by tools/intro.py; edit that, never this file.
(() => {
  const DATA = __DATA__;
  const SVG = __SVG__;
  const T = DATA.t;

  const ease = (t) => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const out = (t) => 1 - Math.pow(1 - t, 3);
  const seg = (p, a, b) => Math.min(1, Math.max(0, (p - a) / (b - a)));
  const mix = (a, b, k) => `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * k)).join(', ')})`;

  // One deforming piece at p: each point moves from start to end; points of a growing
  // tail head for the tip until it has passed them.
  function shape(P, p) {
    const k = ease(seg(p, T.morph[0], T.morph[1]));
    return P.s.map((src, j) => {
      const dst = P.d[j], at = P.at[j];
      const tip = (edge) => {
        for (let m = 1; m < edge.length; m++) {
          const i0 = edge[m - 1], i1 = edge[m];
          if (at[i1] >= k) {
            const f = at[i1] > at[i0] ? (k - at[i0]) / (at[i1] - at[i0]) : 0;
            return [dst[2 * i0] + (dst[2 * i1] - dst[2 * i0]) * f, dst[2 * i0 + 1] + (dst[2 * i1 + 1] - dst[2 * i0 + 1]) * f];
          }
        }
        const last = edge[edge.length - 1];
        return [dst[2 * last], dst[2 * last + 1]];
      };
      const front = new Map();
      if (P.A[j].length) {
        const a = tip(P.A[j]), b = tip(P.B[j]);
        for (const i of P.B[j]) front.set(i, b);
        for (const i of P.A[j]) front.set(i, a);
      }
      let d = 'M';
      for (let i = 0; i < src.length; i += 2) {
        let tx = dst[i], ty = dst[i + 1];
        if (front.has(i / 2) && at[i / 2] > k) [tx, ty] = front.get(i / 2);
        d += (i ? ' L' : '') + (src[i] + (tx - src[i]) * k).toFixed(1) + ' ' + (src[i + 1] + (ty - src[i + 1]) * k).toFixed(1);
      }
      return d + ' Z';
    }).join(' ');
  }

  // Every bound value at p, with the circle scaled by pulse and the caret lit or not.
  function frame(p, pulse, lit, c) {
    const v = {};
    const move = ease(seg(p, T.move[0], T.move[1]));
    const cx = DATA.W / 2 + (DATA.dot[0] - DATA.W / 2) * move;
    const cy = DATA.H / 2 + (DATA.dot[1] - DATA.H / 2) * move;
    const s = (1 + (DATA.dot[2] / DATA.R - 1) * move) * pulse;
    v.discT = `translate(${cx.toFixed(2)} ${cy.toFixed(2)}) scale(${s.toFixed(4)}) translate(${-DATA.W / 2} ${-DATA.H / 2})`;
    v.discFill = mix(c.accent, c.dot, move);
    const landed = p >= T.move[1];
    v.discO = landed ? 0 : 1;
    v.stopO = landed ? 1 : 0;
    v.cyrT = `translate(${(DATA.from[0] * (1 - move)).toFixed(2)} ${(DATA.from[1] * (1 - move)).toFixed(2)})`;
    v.cyrFill = mix([255, 255, 255], c.ink, seg(p, T.ink[0], T.ink[1]));
    for (const key in DATA.morph) v[key] = shape(DATA.morph[key], p);
    const done = p >= T.morph[1];
    v.morphO = done ? 0 : 1;
    v.yaO = done ? 1 : 0;
    for (let i = 0; i < 3; i++) {
      const a = T.slide[0] + i * T.slide[1];
      const q = out(seg(p, a, a + T.slide[2]));
      v['l' + i + 'T'] = `translate(${((1 - q) * -48).toFixed(2)} 0)`;
      v['l' + i + 'O'] = q.toFixed(3);
    }
    let typed = 0;
    for (let i = 0; i < DATA.glyphs; i++) {
      const on = p >= T.type[0] + i * T.type[1];
      v['t' + i] = on ? 1 : 0;
      if (on) typed = i + 1;
    }
    v.caretT = `translate(${DATA.typed[typed]} 0)`;
    v.caretO = p < T.caret ? 0 : (typed > 0 && typed < DATA.glyphs) || lit ? 1 : 0;
    return v;
  }

  const hero = document.querySelector('.hero');
  if (!hero) return;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'mark';
  button.setAttribute('aria-label', 'Play the Yasno Games logo');
  button.innerHTML = SVG;
  hero.append(button);
  const bound = [...button.querySelectorAll('*')].flatMap((el) =>
    [...el.attributes].filter((a) => a.name.startsWith('data-bind-')).map((a) => [el, a.name.slice(10), a.value]));
  const caret = bound.filter(([, , key]) => key === 'caretO');

  const still = matchMedia('(prefers-reduced-motion: reduce)');
  const rgb = (name) => {
    const hex = getComputedStyle(document.documentElement).getPropertyValue(name).trim().replace('#', '');
    return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  };
  let colours;
  const theme = () => { colours = { ink: rgb('--ink'), accent: rgb('--accent'), dot: rgb('--dot') }; };
  theme();

  const born = performance.now();
  let started = null;
  let waiting = null;
  const phase = (now) => started === null ? 0 : still.matches ? 1 : Math.min(1, DATA.start + (now - started) / 1000 / DATA.D);
  // While it waits it breathes about 3%, and each breath sends a ring out from behind it,
  // asking to be touched; both fade as the transform starts.
  const BREATH = 2400;
  const fade = (now) => still.matches ? 0 : started === null ? 1 : Math.max(0, 1 - (now - started) / 400);
  const pulse = (now) => 1 + 0.03 * (0.5 - 0.5 * Math.cos((now - born) / BREATH * 2 * Math.PI)) * fade(now);
  const ring = (now) => {
    const q = out(((now - born) / BREATH) % 1);
    const s = 1 + 0.45 * q;
    return {
      ringT: `translate(${DATA.W / 2} ${DATA.H / 2}) scale(${s.toFixed(4)}) translate(${-DATA.W / 2} ${-DATA.H / 2})`,
      ringO: (0.3 * (1 - q) * fade(now)).toFixed(3),
    };
  };
  const lit = (now) => still.matches || Math.floor(now / 530) % 2 === 0;
  const apply = (list, v) => { for (const [el, attr, key] of list) el.setAttribute(attr, v[key]); };

  let request = 0;
  const schedule = () => {
    if (!request) request = requestAnimationFrame((now) => { request = 0; draw(now); });
  };
  function draw(now) {
    const p = phase(now);
    apply(bound, { ...frame(p, pulse(now), lit(now), colours), ...ring(now) });
    if (p < 1 || (started !== null && now - started < 400)) {
      if (!still.matches) schedule();
    } else {
      blink();
    }
  }
  // Once it has played, only the caret moves.
  function blink() {
    if (still.matches) return;
    clearTimeout(waiting);
    waiting = setTimeout(() => {
      const now = performance.now();
      apply(caret, { caretO: lit(now) ? 1 : 0 });
      blink();
    }, 530 - performance.now() % 530);
  }

  function play() {
    if (started !== null) return;
    started = performance.now();
    button.setAttribute('aria-disabled', 'true');
    schedule();
  }
  button.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') play(); });
  button.addEventListener('click', play);
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { theme(); schedule(); });
  draw(born);
})();
"""


def main():
    data, svg = build()
    script = (SCRIPT.replace("__DATA__", json.dumps(data, separators=(",", ":")))
              .replace("__SVG__", json.dumps(svg)))
    brand.write(brand.PUBLIC / "intro.js", script)


if __name__ == "__main__":
    main()
