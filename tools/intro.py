"""Generate public/intro.js: the site's mark, the round monogram that turns into the wordmark.

The circle pulses until a pointer reaches it or it is pressed; then, once, it shrinks into
the full stop while the я travels left and shrinks with it, its top deforming into the a and its bottom into
the y (the tail growing as the arms tilt), sno slides in and the tagline types out behind
a caret that keeps blinking. Then the full stop breathes in its turn, and shies from a
pointer: out of the word and about the screen, never caught, until left alone it wanders
home. Every shape comes from the typefaces' own outlines, as in
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
R = 220            # the circle's radius
LETTER = brand.letter(2 * R)  # the я in it, its size as in the kit
LANDED = 220       # the я's size once it reaches ya, where it deforms
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

    # The я, drawn centred where ya will sit at the size it lands at; the script carries it
    # there from the circle, shrinking it from the monogram's size on the way.
    g = outline(brand.UNBOUNDED_HEAVY, 0x44F, LANDED, 0, 0).bounds
    ox, oy = ya_c[0] - (g[0] + g[2]) / 2, ya_c[1] - (g[1] + g[3]) / 2
    cyr = outline(brand.UNBOUNDED_HEAVY, 0x44F, LANDED, ox, oy)
    x0, y0, x1, y1 = cyr.bounds
    cut = y0 + (y1 - y0) * CUT
    upper = single(cyr.intersection(box(x0 - 1, y0 - 1, x1 + 1, cut + 0.75)))  # a hair of overlap: no seam
    lower = box(x0 - 1, cut - 0.75, x1 + 1, y1 + 1)
    (body, leg), _ = strokes(brand.UNBOUNDED_HEAVY, 0x44F, LANDED, ox, oy)
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
        "ya": [round(ya_c[0], 2), round(ya_c[1], 2)],
        "grow": round(LETTER / LANDED, 4),
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
             f'<circle class="dot" cx="{n(dot_c[0])}" cy="{n(dot_c[1])}" r="{n(dot_r)}" '
             'data-bind-transform="dotRingT" data-bind-opacity="dotRingO" pointer-events="none"/>',
             '<g data-bind-transform="cyrT" data-bind-fill="cyrFill" data-bind-opacity="morphO">'
             '<path data-bind-d="top"/><path data-bind-d="leg"/><path data-bind-d="stem"/></g>',
             f'<g class="ink" transform="translate({n(mx)} {n(my)})">',
             '<g data-bind-opacity="yaO">' + "".join(f'<path d="{g[0]}"/>' for g in mark[:2]) + "</g>"]
    for i, g in enumerate(mark[2:5]):
        parts.append(f'<path d="{g[0]}" data-bind-transform="l{i}T" data-bind-opacity="l{i}O"/>')
    parts.append(f'</g><g data-bind-transform="stopT" pointer-events="none"><path class="dot" '
                 f'transform="translate({n(mx)} {n(my)})" d="{mark[5][0]}" data-bind-opacity="stopO"/></g>')
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
    const g = 1 + (DATA.grow - 1) * (1 - move);
    v.cyrT = `translate(${(DATA.from[0] * (1 - move)).toFixed(2)} ${(DATA.from[1] * (1 - move)).toFixed(2)}) ` +
      `translate(${DATA.ya[0]} ${DATA.ya[1]}) scale(${g.toFixed(4)}) translate(${-DATA.ya[0]} ${-DATA.ya[1]})`;
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
    v.stopT = v.dotRingT = '';
    v.dotRingO = 0;
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

  // Once it has played, the full stop breathes as the circle did. Come near and it shies:
  // out of the word and about the screen, sliding off the walls and darting across a
  // pointer that corners it, never caught. Left alone a while, it wanders home.
  const after = bound.filter(([, , key]) => ['stopT', 'dotRingT', 'dotRingO', 'caretO'].includes(key));
  const ALONE = 2500;
  const dot = { home: true, x: 0, y: 0, vx: 0, vy: 0, seen: 0, rest: 0 };
  let pointer = null;
  // A touch counts only for a moment, as there is no pointer between touches.
  const aim = (e) => {
    pointer = { x: e.clientX, y: e.clientY, until: e.pointerType === 'touch' ? performance.now() + 300 : Infinity };
  };
  addEventListener('pointermove', aim);
  addEventListener('pointerdown', aim);
  document.addEventListener('pointerout', (e) => { if (!e.relatedTarget && e.pointerType !== 'touch') pointer = null; });
  function chase(now, dt) {
    const box = button.getBoundingClientRect();
    const k = box.width / DATA.W;
    const hx = box.left + DATA.dot[0] * k, hy = box.top + DATA.dot[1] * k, r = DATA.dot[2] * k;
    const near = Math.max(72, 6 * r), w = innerWidth, h = innerHeight;
    if (pointer && (now > pointer.until || still.matches)) pointer = null;
    if (dot.home) { dot.x = hx; dot.y = hy; }
    const dx = pointer ? dot.x - pointer.x : 0, dy = pointer ? dot.y - pointer.y : 0;
    const d = pointer ? Math.hypot(dx, dy) || 0.01 : Infinity;
    if (d < near) { dot.home = false; dot.seen = now; }
    if (!dot.home) {
      const fleeing = now - dot.seen < ALONE;
      if (fleeing) {
        // Away from the pointer, and off a wall it is about to touch, so a cornered dot
        // slides out.
        let ax = 0, ay = 0;
        if (d < near) { const f = 4000 * (1 - d / near) / d; ax += dx * f; ay += dy * f; }
        const pad = 2 * r + 16;
        const wall = (p, size) => Math.max(0, 1 - (p - r) / pad) - Math.max(0, 1 - (size - r - p) / pad);
        const wx = wall(dot.x, w), wy = wall(dot.y, h);
        ax += 5000 * wx;
        ay += 5000 * wy;
        // Nearly caught, it darts across the pointer's path: on along its way, or, cornered,
        // off the wall.
        if (d < near * 0.4 && Math.hypot(dot.vx, dot.vy) < 450) {
          let px = -dy / d, py = dx / d;
          const [ux, uy] = wx || wy ? [wx, wy] : [dot.vx, dot.vy];
          if (px * ux + py * uy < 0 || (!ux && !uy && Math.random() < 0.5)) { px = -px; py = -py; }
          dot.vx = px * 700 + dx / d * 250;
          dot.vy = py * 700 + dy / d * 250;
        }
        const drag = Math.exp(-3.5 * dt);
        dot.vx = (dot.vx + ax * dt) * drag;
        dot.vy = (dot.vy + ay * dt) * drag;
      } else {
        dot.vx += ((hx - dot.x) * 12 - dot.vx * 7) * dt;
        dot.vy += ((hy - dot.y) * 12 - dot.vy * 7) * dt;
      }
      const v = Math.hypot(dot.vx, dot.vy);
      if (v > 900) { dot.vx *= 900 / v; dot.vy *= 900 / v; }
      dot.x += dot.vx * dt;
      dot.y += dot.vy * dt;
      if (fleeing) {
        if (dot.x < r) { dot.x = r; dot.vx = Math.abs(dot.vx) * 0.4; }
        if (dot.x > w - r) { dot.x = w - r; dot.vx = -Math.abs(dot.vx) * 0.4; }
        if (dot.y < r) { dot.y = r; dot.vy = Math.abs(dot.vy) * 0.4; }
        if (dot.y > h - r) { dot.y = h - r; dot.vy = -Math.abs(dot.vy) * 0.4; }
      } else if (Math.hypot(hx - dot.x, hy - dot.y) < 0.5 && v < 4) {
        dot.home = true;
        dot.vx = dot.vy = 0;
      }
    }
    // It breathes, and sends out rings, only at home.
    dot.rest += ((dot.home && !still.matches ? 1 : 0) - dot.rest) * (1 - Math.exp(-3 * dt));
    const ox = (dot.x - hx) / k, oy = (dot.y - hy) / k;
    const b = (now - born) / BREATH;
    const q = out(b % 1);
    const at = (s) => `translate(${ox.toFixed(2)} ${oy.toFixed(2)}) translate(${DATA.dot[0]} ${DATA.dot[1]}) ` +
      `scale(${s.toFixed(4)}) translate(${-DATA.dot[0]} ${-DATA.dot[1]})`;
    return {
      stopT: at(1 + 0.1 * (0.5 - 0.5 * Math.cos(b * 2 * Math.PI)) * dot.rest),
      dotRingT: at(1 + 1.4 * q),
      dotRingO: (0.3 * (1 - q) * dot.rest).toFixed(3),
    };
  }

  let request = 0;
  const schedule = () => {
    if (!request) request = requestAnimationFrame((now) => { request = 0; draw(now); });
  };
  let roaming = false;
  let then = 0;
  function draw(now) {
    if (roaming) return;
    const p = phase(now);
    apply(bound, { ...frame(p, pulse(now), lit(now), colours), ...ring(now) });
    if (still.matches) return;
    if (p < 1 || now - started < 400) {
      schedule();
    } else {
      // A pointer left resting from before must move again to count.
      roaming = true;
      pointer = null;
      then = now;
      requestAnimationFrame(roam);
    }
  }
  function roam(now) {
    const dt = Math.min(1 / 30, (now - then) / 1000);
    then = now;
    apply(after, { ...chase(now, dt), caretO: lit(now) ? 1 : 0 });
    requestAnimationFrame(roam);
  }

  function play() {
    if (started !== null) return;
    started = performance.now();
    button.setAttribute('aria-disabled', 'true');
    schedule();
  }
  // A pointer already resting on the mark when the page loads would set it off before
  // anyone saw the circle: hover counts only after a breath's hold, and if the pointer is
  // still there when the hold ends, it plays then. A press always plays at once.
  const HOLD = 1200;
  let held = true;
  setTimeout(() => {
    held = false;
    if (matchMedia('(hover: hover)').matches && button.matches(':hover')) play();
  }, HOLD);
  button.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse' && !held) play(); });
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
