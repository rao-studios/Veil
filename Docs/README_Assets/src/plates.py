"""Renders Veil's plates in the Rao plate style (AII's Docs/README_Assets/src/plates.py, after Braid's
across.py): Veil8 at a generation step, VeilGarde's watermark on a finished generation, and a picture
found in the wild.

    python3 -I docs/README_Assets/src/plates.py docs/README_Assets [target …]

Inputs:  this folder's rr-mark.png; Playfair Display Italic from ~/Library/Fonts.
Outputs: veil8-step.png, garde-sign.png, garde-wild.png in argv[1].

What each plate draws follows the code. The step: IngestPipeline and VeilLayer (docs/PIPELINE.md),
SDExecutor's predicted-clean previews, Veil8's SPEC.md (rgb-veil8), the attribution matrix and the
block gate (docs/ATTRIBUTION.md), τ 0.945 (docs/CALIBRATION.md). The watermark: VeilGarde's
Sources/VeilWatermark (WarpConstants, WarpResidual, TileCodes, Sectioning, WatermarkSignature,
Matcher) and its acceptance of 2026-10-19 (Docs/site/08-watermark.html); detection's numbers are
VeilGarde v1's README table (2026-10-21). Veil does not sign generations yet: the second plate is a
proposal and says so. Pictures, words, codes and scores are illustrative; shapes and rules are the code's.
"""

import math
import os
import random
import sys
import tempfile

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1])
PLAYFAIR = os.path.expanduser("~/Library/Fonts/PlayfairDisplay-Italic-VariableFont_wght.ttf")

# AII's plate colours, and Veil8's strands.
BLUE, GREEN, ORANGE, GOLD, LINE, VIOLET = "#5e8fda", "#28a883", "#d8773f", "#c7a659", "#cbc8c0", "#a88bd6"
RED = "#d9645a"
DIAL = "#8b8a84"
MONO = "Menlo, 'SF Mono', monospace"
SANS = "-apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif"
W = 1600
LETTERS = "cdefhiklmnoprstw"                 # Veil8Parameters.standard's digits, c = 0 … w = 15


# MARK: Marks (AII's)

def arrowhead(x, y, direction, colour):
    if direction in ("up", "down"):
        d = 1 if direction == "up" else -1
        return (f'<path d="M{x - 7},{y + d * 9} L{x},{y} L{x + 7},{y + d * 9}" fill="none" stroke="{colour}" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    d = 1 if direction == "left" else -1
    return (f'<path d="M{x + d * 9},{y - 7} L{x},{y} L{x + d * 9},{y + 7}" fill="none" stroke="{colour}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')


def reply(x0, x1, y, colour, width=2.2):
    """A hand-off: solid, from x0 to x1."""
    return (f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{colour}" stroke-width="{width}" stroke-linecap="round"/>'
            + arrowhead(x1, y, "right" if x1 > x0 else "left", colour))


def vertical(x, y0, y1, colour=GOLD, dashed=True, both=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    s = (f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{colour}" stroke-width="1.8"{dash} stroke-linecap="round"/>'
         + arrowhead(x, y1, "down" if y1 > y0 else "up", colour))
    return s + (arrowhead(x, y0, "up" if y1 > y0 else "down", colour) if both else "")


def dotted(x0, y0, x1, y1, colour=GOLD, opacity=.6):
    return (f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{colour}" stroke-opacity="{opacity}" '
            f'stroke-width="1.2" stroke-dasharray="2 4" stroke-linecap="round"/>')


def card(left, top, width, height, inner, cls=""):
    return (f'<div class="card {cls}" style="left:{left}px; top:{top}px; width:{width}px; height:{height}px">'
            f'{inner}</div>')


def head(name, colour, machine=""):
    dot = f'<i class="dot" style="background:{colour}"></i>' if colour else ""
    right = f'<span class="machine">{machine}</span>' if machine else ""
    return f'<div class="head"><span>{dot}<b>{name}</b></span>{right}</div>'


def step(*numbers):
    return "".join(f'<span class="step">{n}</span>' for n in numbers)


def lab(x, y, width, title, code="", align="center"):
    """A stage's name under its drawing: centred on x, or from x."""
    left = x - width / 2 if align == "center" else x
    code = f"<code>{code}</code>" if code else ""
    return f'<div class="lab" style="left:{left}px; top:{y}px; width:{width}px; text-align:{align}"><b>{title}</b>{code}</div>'


# The header's rhythm, shared by Rao's plates: the mark's ink sits 70 px from the top and the left; every
# header line's ink starts at the mark's left edge (an italic first glyph overhangs by its own amount, so
# the page measures it); the title's ink starts 70 px under the mark's; what follows starts HEADER_GAP px
# under the subtitle's baseline, and the page grows or shrinks to keep its foot.
INK, TITLE_INK, HEADER_GAP = 70.5, 174, 54
HEADER_JS = """<script>
document.fonts.ready.then(() => {
  const ctx = document.createElement("canvas").getContext("2d");
  const measure = (el) => {
    const cs = getComputedStyle(el), text = el.textContent.trim();
    ctx.font = `italic ${cs.fontWeight} ${cs.fontSize} Playfair`;
    const probe = document.createElement("span");
    probe.style.cssText = "display:inline-block; width:0; height:0";
    el.prepend(probe);
    const baseline = probe.getBoundingClientRect().bottom;
    probe.remove();
    return {left: parseFloat(cs.paddingLeft), top: parseFloat(cs.top), baseline,
            ink: baseline - ctx.measureText(text).actualBoundingBoxAscent, overhang: ctx.measureText(text[0]).actualBoundingBoxLeft};
  };
  const title = document.querySelector(".title"), sub = document.querySelector(".sub");
  const t = measure(title), s = measure(sub), dy = __TITLE_INK__ - t.ink;
  for (const [el, m] of [[title, t], [sub, s]]) {
    el.style.left = (__INK__ - m.left + m.overhang) + "px";
    el.style.top = (m.top + dy) + "px";
  }
  const header = ".mark, .caption, .title, .sub, script, style", rest = [...document.body.children].filter((el) => !el.matches(header));
  let first = Infinity;
  for (const el of rest) {
    const r = el.getBoundingClientRect();
    if (el instanceof SVGSVGElement) {
      const b = el.getBBox();
      if (b.width || b.height) first = Math.min(first, r.top + b.y);
    } else if (r.width && r.height) first = Math.min(first, r.top);
  }
  const shift = Math.round(s.baseline + dy + __GAP__ - first);
  for (const el of rest) el.style.translate = `0 ${shift}px`;
  const height = parseFloat(getComputedStyle(document.body).height) + shift;
  document.documentElement.style.height = document.body.style.height = height + "px";
  document.body.dataset.height = height;
});
</script>""".replace("__INK__", str(INK)).replace("__TITLE_INK__", str(TITLE_INK)).replace("__GAP__", str(HEADER_GAP))


def plate(name, height, caption, title, sub, body, tag):
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Playfair"; font-style: italic; font-weight: 400 900; src: url("file://{PLAYFAIR}") format("truetype"), local("Playfair Display Italic"); }}
html, body {{ margin: 0; width: {W}px; height: {height}px; overflow: hidden; }}
body {{ position: relative; font-family: "Playfair", Georgia, serif; font-style: italic; color: #a29f97; font-variant-numeric: lining-nums;
       background: radial-gradient(ellipse 90% 100% at 22% 20%, #20201c 0%, #191917 45%, #121211 100%); }}
.mark {{ position: absolute; left: 62.5px; top: 60px; width: 64px; }}
.caption {{ position: absolute; left: 150px; top: 78px; letter-spacing: .3em; font-size: 15px; color: #8b8a84; }}
.title {{ position: absolute; left: 39.5px; padding-left: 40px; top: 162px; font-size: 104px; line-height: 1; font-weight: 500; letter-spacing: -.005em; padding-right: 30px; padding-bottom: 32px;
         background: linear-gradient(100deg, #8d9097 0%, #c8cad0 35%, #f2f3f6 58%, #b6b9c1 100%);
         -webkit-background-clip: text; background-clip: text; color: transparent; white-space: nowrap; }}
.sub {{ position: absolute; left: 69px; top: 280px; font-size: 32px; color: #9b9991; white-space: nowrap; }}
svg {{ position: absolute; left: 0; top: 0; }}
.card {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); border-radius: 14px;
        background: rgba(255,255,255,.028); padding: 16px 20px; }}
.card.inner {{ padding: 12px 14px; }}
.card.proposed {{ border-style: dashed; border-color: rgba(199,166,89,.45); }}
.card p {{ margin: 8px 0 0; font-size: 16px; line-height: 1.34; color: #a29f97; }}
.card.inner p {{ margin-top: 5px; font-size: 15px; }}
.card b {{ font-weight: 400; color: #ecebe5; }}
.card code {{ font-family: {MONO}; font-style: normal; font-size: 12.5px; color: #c3c0b7; }}
.head {{ display: flex; justify-content: space-between; align-items: baseline; }}
.head b {{ font-size: 26px; }}
.card.inner .head b {{ font-size: 20px; }}
.machine {{ font-size: 11.5px; letter-spacing: .22em; color: #77756f; white-space: nowrap; }}
.dot {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 10px; transform: translateY(-2px); }}
.step {{ display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; margin-right: 9px; border: 1.6px solid {GOLD};
        border-radius: 50%; font-family: {SANS}; font-style: normal; font-weight: 600; font-size: 12px; color: {GOLD}; transform: translateY(-1px); flex: none; }}
.lab {{ position: absolute; display: flex; flex-direction: column; }}
.lab b {{ font-weight: 400; font-size: 18px; color: #ecebe5; }}
.lab code {{ font-family: {MONO}; font-style: normal; font-size: 12px; color: #8b8a84; margin-top: 3px; white-space: nowrap; }}
.wire {{ position: absolute; font-family: {MONO}; font-style: normal; font-size: 12px; color: #a7a49b; white-space: nowrap; }}
.note {{ position: absolute; font-size: 16px; line-height: 1.36; color: #a29f97; }}
.note b {{ font-weight: 400; color: #ecebe5; }}
.rows {{ display: grid; row-gap: 0; margin-top: 10px; }}
.rows > div {{ display: grid; column-gap: 12px; align-items: baseline; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,.07); font-size: 15.5px; }}
.rows > div:last-child {{ border-bottom: 0; }}
.rows b {{ font-weight: 400; color: #ecebe5; }}
.rows code {{ font-size: 12px; color: #8b8a84; white-space: nowrap; }}
.tag {{ position: absolute; right: 70px; top: {height - 52}px; font-size: 18px; color: #8b8a84; }}
</style></head><body>
<img class="mark" src="rr-mark.png">
<div class="caption">{caption}</div>
<div class="title">{title}</div>
<div class="sub">{sub}</div>
{body}
<div class="tag">{tag}</div>
{HEADER_JS}
</body></html>"""
    return name, height, page


# MARK: Pictures (illustrative, drawn here)

def clamp(v):
    return max(0, min(255, int(round(v))))


def hexrgb(c):
    return "#%02x%02x%02x" % tuple(clamp(v) for v in c)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def scene(sun=(10.5, 5.2), sky=((44, 48, 104), (226, 142, 84)), land=((34, 74, 62), (16, 32, 30)), seed=3, n=16):
    """A small painting, one colour a tile: a sky to the horizon, a sun, a ridge, its foot."""
    rng = random.Random(seed)
    ridge = [9.2 + 1.6 * math.sin(c * .55 + seed) + .8 * math.sin(c * 1.3 + 2 * seed) for c in range(n)]
    grid = []
    for r in range(n):
        row = []
        for c in range(n):
            if r + .5 < ridge[c]:
                t = min(1, (r + .5) / ridge[c]) ** 1.6
                col = mix(sky[0], sky[1], t)
                d = math.hypot(c + .5 - sun[0], r + .5 - sun[1])
                if d < 2.4:
                    col = mix(col, (246, 206, 120), max(0, min(1, (2.4 - d) / 1.1)))
                elif d < 4:
                    col = mix(col, (238, 170, 100), .25 * (4 - d) / 1.6)
            else:
                col = mix(land[0], land[1], min(1, (r + .5 - ridge[c]) / (n - ridge[c])))
            jitter = rng.uniform(-7, 7)
            row.append(tuple(v + jitter for v in col))
        grid.append(row)
    return grid


def estimate(grid, rng, contrast=.82, noise=16):
    """x̂0 mid-run: a softened, noisier reading of where the loop is heading."""
    n = len(grid)
    mean = [sum(grid[r][c][k] for r in range(n) for c in range(n)) / n / n for k in range(3)]
    out = []
    for r in range(n):
        row = []
        for c in range(n):
            nb = [grid[rr][cc] for rr in range(max(0, r - 1), min(n, r + 2)) for cc in range(max(0, c - 1), min(n, c + 2))]
            soft = [sum(p[k] for p in nb) / len(nb) for k in range(3)]
            v = [(.55 * grid[r][c][k] + .45 * soft[k]) for k in range(3)]
            row.append(tuple(mean[k] + (v[k] - mean[k]) * contrast + rng.gauss(0, noise) for k in range(3)))
        out.append(row)
    return out


def mosaic(x, y, grid, cell, gap=1, opacity=1):
    s = []
    for r, row in enumerate(grid):
        for c, col in enumerate(row):
            if col is None:
                continue
            s.append(f'<rect x="{x + c * cell}" y="{y + r * cell}" width="{cell - gap}" height="{cell - gap}" rx="1" '
                     f'fill="{hexrgb(col)}" fill-opacity="{opacity}"/>')
    return "".join(s)


def tile_pixels(grid, r, c, rng, noise=9, size=32):
    """One tile's pixels: its neighbours' colours blended across it, with grain."""
    n = len(grid)

    def at(rr, cc):
        return grid[max(0, min(n - 1, rr))][max(0, min(n - 1, cc))]

    out = []
    for y in range(size):
        row = []
        for x in range(size):
            fy, fx = (y + .5) / size - .5, (x + .5) / size - .5
            r0, c0 = (r - 1 if fy < 0 else r), (c - 1 if fx < 0 else c)
            ty, tx = (fy + 1 if fy < 0 else fy), (fx + 1 if fx < 0 else fx)
            top = mix(at(r0, c0), at(r0, c0 + 1), tx)
            bot = mix(at(r0 + 1, c0), at(r0 + 1, c0 + 1), tx)
            g = rng.gauss(0, noise)
            row.append(tuple(v + g for v in mix(top, bot, ty)))
        out.append(row)
    return out


def frame(x, y, size, colour="rgba(255,255,255,.16)"):
    return f'<rect x="{x - .5}" y="{y - .5}" width="{size + 1}" height="{size + 1}" rx="3" fill="none" stroke="{colour}"/>'


def barcode(x, y, w, h, values, colour):
    """A vector, drawn as its first numbers: one bar each, up or down from the middle."""
    s, bw = [], w / len(values)
    mid = y + h / 2
    s.append(f'<line x1="{x}" y1="{mid}" x2="{x + w}" y2="{mid}" stroke="rgba(255,255,255,.12)"/>')
    for i, v in enumerate(values):
        bh = abs(v) * h / 2
        top = mid - bh if v > 0 else mid
        s.append(f'<rect x="{x + i * bw + .6}" y="{top:.1f}" width="{bw - 1.2:.1f}" height="{max(1, bh):.1f}" fill="{colour}" fill-opacity=".8"/>')
    return "".join(s)


# MARK: Veil8 at a step

TAU = 0.945


def heat_grid(rng, n=16):
    """The attribution matrix's tiles: a reproduced region lit, look-alikes scattered, a flat sky corner."""
    cats = []
    for r in range(n):
        row = []
        for c in range(n):
            if r <= 1 and c <= 3 or r == 0 and c <= 6:
                row.append("flat")
            elif 3 <= r <= 12 and 5 <= c <= 14 and rng.random() > .1:
                row.append("attributed")
            elif rng.random() < .07:
                row.append("incoherent")
            else:
                row.append("below")
        cats.append(row)
    return cats


HEAT = {"attributed": (GOLD, .9), "incoherent": (ORANGE, .55), "below": ("#4a4944", .7)}


def heat(x, y, cats, cell):
    s = ['<defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<line x1="0" y1="0" x2="0" y2="5" stroke="#6d6b65" stroke-width="1.4"/></pattern></defs>']
    for r, row in enumerate(cats):
        for c, cat in enumerate(row):
            px, py = x + c * cell, y + r * cell
            if cat == "flat":
                s.append(f'<rect x="{px}" y="{py}" width="{cell - 1}" height="{cell - 1}" fill="url(#hatch)"/>')
            else:
                colour, op = HEAT[cat]
                s.append(f'<rect x="{px}" y="{py}" width="{cell - 1}" height="{cell - 1}" rx="1" fill="{colour}" fill-opacity="{op}"/>')
    return "".join(s)


def edge_tile(grid):
    """The tile the ridge crosses most sharply, near the middle: one with something in it to show."""
    def diff(a, b):
        return sum(abs(a[k] - b[k]) for k in range(3))
    return max(((r, c) for r in range(5, 11) for c in range(5, 12)), key=lambda rc: diff(grid[rc[0] - 1][rc[1]], grid[rc[0] + 1][rc[1]]))


def words(rng, count):
    return [rng.choice(LETTERS) + rng.choice(LETTERS) for _ in range(count)]


def word_lines(ws, moved, per_line):
    lines = []
    for i in range(0, len(ws), per_line):
        lines.append(" ".join(f'<i class="mv">{w}</i>' if (i + j) in moved else w for j, w in enumerate(ws[i:i + per_line])))
    return "<br>".join(lines)


def veil8_step():
    rng = random.Random(8)
    pic = scene()
    est = estimate(pic, random.Random(11))
    s, labels = [], []
    TR, TC = edge_tile(pic)                                 # the tile followed through both roads
    A, B, SZ = 452, 722, 128                                # the two roads' tops, and the drawings' size
    C0, C1, C2, C2W, C3, C3W, C4 = 262, 446, 634, 300, 996, 128, 1186

    for top, grid, noise in ((A, pic, 7), (B, est, 13)):
        s.append(mosaic(C0, top, grid, 8))
        s.append(frame(C0, top, SZ))
        s.append(f'<rect x="{C0 + TC * 8 - 1}" y="{top + TR * 8 - 1}" width="10" height="10" fill="none" stroke="{GOLD}" stroke-width="1.6"/>')
        s.append(dotted(C0 + TC * 8 + 9, top + TR * 8, C1, top) + dotted(C0 + TC * 8 + 9, top + TR * 8 + 9, C1, top + SZ))
        s.append(mosaic(C1, top, tile_pixels(grid, TR, TC, random.Random(5), noise), 4, gap=0))
        s.append(frame(C1, top, SZ, GOLD))
        mid = top + SZ / 2
        for x0, x1 in ((C0 + SZ + 8, C1 - 10), (C1 + SZ + 10, C2 - 10), (C2 + C2W + 10, C3 - 10), (C3 + C3W + 10, C4 - 10)):
            s.append(reply(x0, x1, mid, DIAL, 1.6))

    # The words: the stored tile's, then the step's, most of them unchanged.
    stored = words(rng, 40)
    moved = set(rng.sample(range(40), 9))
    query = [rng.choice(LETTERS) + rng.choice(LETTERS) if i in moved else w for i, w in enumerate(stored)]
    for top, ws, mv in ((A, stored, set()), (B, query, moved)):
        labels.append(f'<div class="words" style="left:{C2}px; top:{top}px; width:{C2W}px; height:{SZ}px">'
                      f'{word_lines(ws, mv, 10)} …</div>')

    vec = [rng.gauss(0, .38) for _ in range(30)]
    s.append(barcode(C3, A + 14, C3W, SZ - 28, [max(-1, min(1, v)) for v in vec], LINE))
    s.append(barcode(C3, B + 14, C3W, SZ - 28, [max(-1, min(1, v + rng.gauss(0, .07))) for v in vec], GOLD))

    # The lanes' names.
    ticks = []
    for i in range(20):
        checked = i in (9, 19)
        x = 98 + i * 7.2
        ticks.append(f'<line x1="{x}" y1="{B + 104 - (9 if checked else 0)}" x2="{x}" y2="{B + 112}" stroke="{GOLD if checked else "#5d5b56"}" stroke-width="{2 if checked else 1.4}" stroke-linecap="round"/>')
    s.extend(ticks)
    labels.append(f'<div class="lane" style="left:96px; top:{A + 24}px"><b>filed once</b><code>veil ingest</code>'
                  f'<span>a picture to protect, cut, written and kept in Thread</span></div>')
    labels.append(f'<div class="lane" style="left:96px; top:{B + 8}px"><b>at a step</b><code>sd15 · 20 steps</code>'
                  f'<span>the loop pauses for it</span></div>')
    labels.append(f'<div class="wire" style="left:96px; top:{B + 122}px; color:{GOLD}">checks: 10, final</div>')

    under = 140
    labels += [lab(C0 + SZ / 2, A + under, 190, "the canonical image", "≤ 1080 px, padded to 32"),
               lab(C1 + SZ / 2, A + under, 170, "one 32×32 tile", "1,024 pixels"),
               lab(C2 + C2W / 2, A + under, C2W, "rgb-veil8: a word a pixel", "3,071 characters · 1,024 tokens"),
               lab(C3 + C3W / 2, A + under, 200, "one vector", "voyage-4-nano · 1,024 numbers"),
               lab(C0 + SZ / 2, B + under, 190, "x̂0, the clean estimate", "decoded at step 10"),
               lab(C1 + SZ / 2, B + under, 170, "the same cut", "Veil’s Metal tiler"),
               lab(C2 + C2W / 2, B + under, C2W, "words that held, words that moved", "the moved in orange"),
               lab(C3 + C3W / 2, B + under, 200, "its vector", "in Veil’s process")]

    # What the two roads share: each a link between them.
    y0, y1 = A + under + 54, B - 8
    links = [(C1 + SZ / 2, LINE, False, "the same tiles", "flat ones skipped"),
             (C2 + C2W / 2, GOLD, True, "the same key", "this Mac’s, never sent"),
             (C3 + C3W / 2, LINE, False, "the same embedder", "voyage-4@1024"),
             (C4 + 160, BLUE, False, "the exact vectors", "pulled once a session")]
    for x, colour, both, name, code in links:
        s.append(vertical(x, y0, y1, colour, dashed=colour != BLUE, both=both))
        labels.append(f'<div class="link" style="left:{x + 12}px; top:{(y0 + y1) / 2 - 18}px"><b style="color:{colour if colour != LINE else "#ecebe5"}">{name}</b><code>{code}</code></div>')

    thread = (head("Thread", BLUE, "AII-RECORD/1")
              + '<p><code>veil/image/&lt;id&gt;</code>: the caption, then one partition a tile, '
                'each at <code>#xywh=pixel:x,y,32,32</code></p>'
                '<p>beside them: the serializer, the key’s fingerprint, the embedder</p>')
    compare = (head("cosine", GOLD, "DENSESIMILARITY")
               + '<p>each step tile against every protected tile pruning kept, wherever it sits</p>'
                 f'<p><b>a tile counts at τ {TAU}</b></p>')

    body = f"""<style>
.words {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); border-radius: 9px; padding: 13px 14px;
         font-family: {MONO}; font-style: normal; font-size: 14px; line-height: 1.62; letter-spacing: .02em; color: #dcdad3; }}
.words .mv {{ font-style: normal; color: {ORANGE}; }}
.lane {{ position: absolute; width: 150px; display: flex; flex-direction: column; }}
.lane b {{ font-weight: 400; font-size: 21px; color: #ecebe5; }}
.lane code {{ font-family: {MONO}; font-style: normal; font-size: 12px; color: #a7a49b; margin-top: 4px; }}
.lane span {{ font-size: 15px; line-height: 1.3; margin-top: 5px; }}
.link {{ position: absolute; display: flex; flex-direction: column; }}
.link b {{ font-weight: 400; font-size: 16px; }}
.link code {{ font-family: {MONO}; font-style: normal; font-size: 11.5px; color: #8b8a84; margin-top: 1px; white-space: nowrap; }}
</style>
{card(70, 374, 1460, 548, head(step(1) + "Two roads into one space", GOLD, "INGESTPIPELINE · VEILLAYER"))}
{card(C4, A, 1504 - C4, SZ + 30, thread, "inner")}
{card(C4, B, 1504 - C4, SZ + 30, compare, "inner")}
<svg width="{W}" height="1040">{"".join(s)}</svg>
{"".join(labels)}"""
    return plate("veil8-step.png", 1004, "RAO STUDIOS · VEIL · VEIL8 AT A STEP",
                 "Read mid-flight", "the model’s clean estimate, written in the same words as the pictures it must not copy",
                 body, "the pictures and words are illustrative; τ and the geometry are the code’s")


# MARK: Word to verdict (Veil8's word, coherence, the block gate)

def veil8_verdict():
    T = 374
    body = f"""<style>
.bits {{ position: absolute; font-family: {MONO}; font-style: normal; color: #dcdad3; }}
.legend {{ position: absolute; display: grid; grid-template-columns: 18px 1fr; row-gap: 7px; column-gap: 10px; align-items: center; font-size: 15px; width: 230px; }}
.legend i {{ width: 14px; height: 14px; border-radius: 2px; display: block; }}
.legend b {{ font-weight: 400; color: #ecebe5; }}
.gate {{ position: absolute; width: 428px; }}
.gate > div {{ display: grid; grid-template-columns: 1fr auto; column-gap: 12px; align-items: baseline; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,.07); font-size: 15.5px; }}
.gate b {{ font-weight: 400; color: #ecebe5; }}
.gate code {{ font-family: {MONO}; font-style: normal; font-size: 13px; color: {GOLD}; }}
.gate .or {{ font-size: 13px; color: #77756f; border: 0; padding: 0; }}
</style>
{card(70, T, 470, 300, head(step(1) + "One pixel, one word", GOLD, "VEIL8ENCODER"))}
{card(560, T, 470, 300, head(step(2) + "When a tile counts", GOLD, "COHERENCE"))}
{card(1050, T, 480, 300, head(step(3) + "Halt, or go on", GOLD, "BLOCKGATE"))}
<svg width="{W}" height="800">{pixel_word_svg(T)}{heat(586, T + 54, heat_grid(random.Random(4)), 9)}</svg>
{pixel_word_html(T)}
<div class="legend" style="left:756px; top:{T + 58}px">
  <i style="background:{GOLD}"></i><span><b>attributed</b>: at τ, and a neighbour agrees</span>
  <i style="background:{ORANGE}; opacity:.6"></i><span><b>a look-alike</b>: at τ alone, dropped</span>
  <i style="background:#4a4944"></i><span><b>below τ</b></span>
  <i style="background:repeating-linear-gradient(45deg,#6d6b65 0 1.5px,transparent 1.5px 4px)"></i><span><b>flat</b>: never queried</span>
</div>
<div class="note" style="left:586px; top:{T + 230}px; width:424px; font-size:15px">A neighbour agrees when it points to <b>the same picture at the same offset</b>. The smallest copy it sees is two tiles, 64×32 px.</div>
<div class="gate" style="left:1076px; top:{T + 54}px">
  <div><span><b>attributed tiles</b></span><code>≥ 8</code></div>
  <div><span>one group’s <b>share × coverage</b></span><code>≥ 0.35</code></div>
  <div class="or">or</div>
  <div><span>its <b>share</b>, while coverage</span><code>≥ 0.60 · ≥ 0.10</code></div>
</div>
<div class="note" style="left:1076px; top:{T + 204}px; width:430px; font-size:15px"><b>Blocked: the loop stops</b> before the next step, and the verdict names the rule, the group and the value. Before any of it, the corpus probe refuses <b>another key, encoding or embedder</b>.</div>"""
    return plate("veil8-verdict.png", 756, "RAO STUDIOS · VEIL · VEIL8, WORD TO VERDICT",
                 "Word to verdict", "a pixel becomes a word, a tile counts when its neighbours agree, and the gate decides",
                 body, "the words and heat are illustrative; τ, the gate and the geometry are the code’s")


# The pixel-to-word card: a 5×5 RGB window, eight keyed sums, eight bits, two letters.
WORD_BITS = [0, 1, 0, 1, 1, 0, 1, 1]                        # i = 5 (0101), p = 11 (1011)


def pixel_word_svg(top):
    s, x, y, cell = [], 96, top + 66, 17
    rng = random.Random(2)
    for r in range(5):
        for c in range(5):
            for k, colour in enumerate((RED, GREEN, BLUE)):
                s.append(f'<rect x="{x + c * cell + k * 5}" y="{y + r * cell}" width="4.4" height="{cell - 2}" rx="1" '
                         f'fill="{colour}" fill-opacity="{rng.uniform(.3, .95):.2f}"/>')
    s.append(f'<rect x="{x + 2 * cell - 1.5}" y="{y + 2 * cell - 1.5}" width="{cell}" height="{cell}" fill="none" stroke="{GOLD}" stroke-width="1.6"/>')
    s.append(reply(x + 5 * cell + 10, 222, y + 42, DIAL, 1.6))
    for i, b in enumerate(WORD_BITS):
        bx = 232 + i * 25
        s.append(f'<rect x="{bx}" y="{y + 28}" width="21" height="28" rx="4" fill="{GOLD if b else "none"}" fill-opacity=".16" '
                 f'stroke="{GOLD if b else "#5d5b56"}" stroke-opacity="{.8 if b else 1}"/>')
    s.append(f'<line x1="{232 + 4 * 25 - 2}" y1="{y + 22}" x2="{232 + 4 * 25 - 2}" y2="{y + 62}" stroke="#77756f" stroke-dasharray="2 3"/>')
    s.append(reply(436, 462, y + 42, DIAL, 1.6))
    return "".join(s)


def pixel_word_html(top):
    bits = "".join(f'<span style="position:absolute; left:{232 + i * 25}px; width:21px; text-align:center; top:{top + 100}px; '
                   f'font-family:{MONO}; font-style:normal; font-size:14px; color:{GOLD if b else "#8b8a84"}">{b}</span>'
                   for i, b in enumerate(WORD_BITS))
    return (bits
            + f'<div class="wire" style="left:232px; top:{top + 70}px; font-size:11.5px">⌊(Σ G·u + w) / Δ⌋ mod 2</div>'
            + f'<div style="position:absolute; left:470px; top:{top + 84}px; font-size:34px; color:#ecebe5">ip</div>'
            + f'<div class="wire" style="left:96px; top:{top + 158}px; font-size:11.5px">5×5 RGB: 75 values</div>'
            + f'<div class="wire" style="left:232px; top:{top + 126}px; font-size:11.5px">8 keyed bits · 2 of 16 letters</div>'
            + f'<div class="note" style="left:96px; top:{top + 190}px; width:420px; font-size:15px">The weights and the dither come from the key. '
              '<b>75 values become 8 bits</b>: the floor drops what is finer than 32 grey levels, <i>mod 2</i> drops the size. '
              'Many tiles write the same words; none can be read back.</div>')


# MARK: VeilGarde signs the outcome (proposed)

def generation():
    return scene(sun=(4.2, 4.6), sky=((86, 116, 160), (238, 196, 150)), land=((70, 96, 52), (30, 44, 30)), seed=7)


def fragility(rng, n=16):
    """A smooth field of per-tile fragility rates (illustrative)."""
    bumps = [(rng.uniform(0, n), rng.uniform(0, n), rng.uniform(2, 5), rng.uniform(-.25, .3)) for _ in range(7)]
    out = []
    for r in range(n):
        out.append([.4 + sum(a * math.exp(-((r - y) ** 2 + (c - x) ** 2) / (2 * w * w)) for x, y, w, a in bumps) + rng.gauss(0, .05)
                    for c in range(n)])
    return out


NEIGHBOURS = [(0, 1), (1, 0), (1, 1), (-1, 1)]               # TileCodeGrid.neighbours: E, S, SE, NE


def codes(fr):
    """Each tile's nibble: bit k says whether its FR exceeds neighbour k's, masked at the edges."""
    n = len(fr)
    bits, measured = [], 0
    for r in range(n):
        row = []
        for c in range(n):
            v = 0
            for k, (dr, dc) in enumerate(NEIGHBOURS):
                rr, cc = r + dr, c + dc
                if 0 <= rr < n and 0 <= cc < n:
                    measured += 1
                    v |= (fr[r][c] > fr[rr][cc]) << k
            row.append(v)
        bits.append(row)
    return bits, measured


def measured_bits(rows, cols):
    return sum(1 for r in range(rows) for c in range(cols) for dr, dc in NEIGHBOURS if 0 <= r + dr < rows and 0 <= c + dc < cols)


def warps(cx, cy, side, rng, colour=LINE):
    """A tile and the sixteen fixed homographies it is sent through: drawn as its corners pushed."""
    s, h = [], side / 2
    for _ in range(16):
        pts = [(cx + sx * h + rng.uniform(-13, 13), cy + sy * h + rng.uniform(-13, 13)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        s.append('<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f' Z" fill="none" stroke="{colour}" stroke-opacity=".22" stroke-width="1"/>')
    s.append(f'<rect x="{cx - h}" y="{cy - h}" width="{side}" height="{side}" fill="none" stroke="{GOLD}" stroke-width="1.8" rx="2"/>')
    return "".join(s)


def fr_grid(x, y, fr, cell):
    lo, hi = min(map(min, fr)), max(map(max, fr))
    s = []
    for r, row in enumerate(fr):
        for c, v in enumerate(row):
            t = (v - lo) / (hi - lo)
            g = 40 + 200 * t
            s.append(f'<rect x="{x + c * cell}" y="{y + r * cell}" width="{cell - 1}" height="{cell - 1}" rx="1" fill="{hexrgb((g, g * .97, g * .9))}"/>')
    return "".join(s)


def ordinal(x, y, cell):
    """One tile against its forward neighbours: E, S, SE, NE."""
    values = {(1, 1): .41, (1, 2): .37, (2, 1): .52, (2, 2): .29, (0, 2): .44}
    names = {(1, 2): "E", (2, 1): "S", (2, 2): "SE", (0, 2): "NE"}
    s, t = [], []
    for r in range(3):
        for c in range(3):
            px, py = x + c * cell, y + r * cell
            v = values.get((r, c))
            centre = (r, c) == (1, 1)
            s.append(f'<rect x="{px}" y="{py}" width="{cell - 3}" height="{cell - 3}" rx="3" fill="rgba(255,255,255,{.06 if v else .015})" '
                     f'stroke="{GOLD if centre else "rgba(255,255,255,.14)"}" stroke-width="{1.8 if centre else 1}"/>')
            if v:
                t.append(f'<div class="fr" style="left:{px}px; top:{py + (cell - 3) / 2 - 8}px; width:{cell - 3}px">{v:.2f}</div>')
            if (r, c) in names:
                above = v < values[(1, 1)]
                t.append(f'<div class="nb" style="left:{px + 3}px; top:{py + 1}px; color:{GOLD if above else "#77756f"}">{names[(r, c)]}</div>')
    return "".join(s), "".join(t)


def garde_sign():
    rng = random.Random(21)
    gen = generation()
    fr = fragility(random.Random(9))
    nib, bits = codes(fr)
    s, labels = [], []
    Y, SZ = 486, 144
    mid = Y + SZ / 2
    X0, X1, X2, X3, X4, X5 = 100, 300, 512, 718, 920, 1176

    s.append(mosaic(X0, Y, gen, 9))
    s.append(frame(X0, Y, SZ))
    s.append(warps(X1 + 74, mid, 70, rng))
    s.append(fr_grid(X2, Y, fr, 9))
    s.append(frame(X2, Y, SZ))
    o_svg, o_html = ordinal(X3, Y + 2, 46)
    s.append(o_svg)
    sec = [[nib[r][c] for c in range(4)] for r in range(4)]
    for r in range(4):
        for c in range(4):
            s.append(f'<rect x="{X4 + c * 30}" y="{Y + 12 + r * 30}" width="27" height="27" rx="3" fill="rgba(255,255,255,.04)" stroke="rgba(199,166,89,.4)"/>')
            labels.append(f'<div class="nib" style="left:{X4 + c * 30}px; top:{Y + 18 + r * 30}px">{sec[r][c]:x}</div>')
    for x0, x1 in ((X0 + SZ + 10, X1 - 8), (X1 + 158, X2 - 10), (X2 + SZ + 10, X3 - 10), (X3 + 146, X4 - 10), (X4 + 132, X5 - 10)):
        s.append(reply(x0, x1, mid, DIAL, 1.6))
    word = 0
    for r in range(4):
        for c in range(4):
            word |= sec[r][c] << ((r * 4 + c) * 4)

    # Above the frame: the run, checked and not blocked.
    for i in range(20):
        checked = i in (9, 19)
        x = X0 + i * 7.4
        s.append(f'<line x1="{x}" y1="{Y - 30 - (9 if checked else 0)}" x2="{x}" y2="{Y - 22}" stroke="{GREEN if checked else "#5d5b56"}" stroke-width="{2 if checked else 1.4}" stroke-linecap="round"/>')
    labels.append(f'<div class="wire" style="left:{X0 + 150}px; top:{Y - 40}px; color:{GREEN}">checks 10, final: clear</div>')

    under = SZ + 14
    labels += [lab(X0 + SZ / 2, Y + under, 200, "the final frame", "sd15 · 512² · 16×16 tiles"),
               lab(X1 + 74, Y + under, 200, "sixteen warps, and back", "strengths 0.025, 0.05"),
               lab(X2 + SZ / 2, Y + under, 200, "fragility, per tile", "FR: what the stronger loses"),
               lab(X3 + 68, Y + under, 200, "four bits a tile", "above E, S, SE, NE?"),
               lab(X4 + 58, Y + under, 200, "4×4 tiles, one word", f"0x{word:016x}"[:12] + "…"),
               o_html]

    sig = (head("the signature", GOLD, "VW1")
           + f'<p><code>vw1:{"VlcxAAEgBAAAEAAAABAAAAAQ"}…</code></p>'
           + f'<p><code>cid 9f04c2e1d7…</code> SHA-256 of its bytes</p>'
           + f'<p>16 sections · <b>{bits} measured bits</b></p>')
    record = (head("filed with the run", GOLD, "PROPOSED")
              + '<p><code>veil/generation/&lt;cid&gt;</code></p>'
              + '<p>the model, the seed, the size, the checks it passed, and the signature</p>')

    s.append(vertical(X0 + SZ / 2, Y + under + 52, 744, LINE, dashed=False))
    s.append(vertical(X5 + 164, Y + SZ + 30 + 8, 744, GOLD, dashed=True))

    bars = []
    for x, pairs, name in ((96, ((.41, GOLD, "tile"), (.37, LINE, "E")), "signed"), (316, ((.33, GOLD, "tile"), (.30, LINE, "E")), "after a JPEG q75")):
        labels.append(f'<div class="bl" style="left:{x}px; top:1000px">{name}</div>')
        for j, (v, colour, who) in enumerate(pairs):
            y = 1026 + j * 28
            bars.append(f'<rect x="{x}" y="{y}" width="{v * 260:.0f}" height="12" rx="3" fill="{colour}" fill-opacity=".75"/>')
            labels.append(f'<div class="bl" style="left:{x + v * 260 + 8:.0f}px; top:{y - 2}px">{v:.2f} {who}</div>')
        labels.append(f'<div class="wire" style="left:{x}px; top:1084px; color:{GOLD}">bit E: 1</div>')

    body = f"""<style>
.fr {{ position: absolute; text-align: center; font-family: {MONO}; font-style: normal; font-size: 12.5px; color: #dcdad3; }}
.nb {{ position: absolute; font-family: {SANS}; font-style: normal; font-size: 9.5px; font-weight: 600; letter-spacing: .04em; }}
.nib {{ position: absolute; width: 27px; text-align: center; font-family: {MONO}; font-style: normal; font-size: 13px; color: #dcdad3; }}
.out {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.14); border-radius: 10px; padding: 11px 14px; }}
.out b {{ display: block; font-weight: 400; font-size: 19px; color: #ecebe5; }}
.out span {{ display: block; font-size: 15px; line-height: 1.3; color: #a29f97; margin-top: 3px; }}
.rows > div {{ grid-template-columns: 1fr auto auto; }}
.rows .ok {{ font-family: {MONO}; font-style: normal; font-size: 13px; color: {GOLD}; text-align: right; }}
.rows .no {{ font-family: {MONO}; font-style: normal; font-size: 13px; color: {ORANGE}; text-align: right; }}
.bl {{ position: absolute; font-family: {MONO}; font-style: normal; font-size: 11.5px; color: #8b8a84; }}
</style>
{card(70, 374, 1460, 524, head(step(1) + "From the last step to a signature", GOLD, "VEILWATERMARK V1"))}
{card(X5, Y, 1504 - X5, SZ + 30, sig, "inner")}
<div class="out" style="left:{X0 - 4}px; top:756px; width:330px"><b>the image, as rendered</b><span>handed back untouched: nothing is added to its pixels, so there is nothing to find and strip</span></div>
{card(X5, 752, 1504 - X5, 128, record, "inner proposed")}
<div class="note" style="left:520px; top:770px; width:600px; text-align:center">The pixels go one way and the signature the other. <b>Whoever keeps the signature can later recognise the image, or a crop of it</b>: the pattern is what the pixels already are.</div>
{card(70, 922, 470, 300, head(step(2) + "Why the bits are ordinal", GOLD, "TILECODES"))}
{card(560, 922, 470, 300, head(step(3) + "What v1 survives", GOLD, "198 IMAGES"))}
{card(1050, 922, 480, 300, head(step(4) + "Where Veil would sign", GOLD, "PROPOSED"), "proposed")}
<svg width="{W}" height="1400">{"".join(s)}{"".join(bars)}</svg>
{"".join(labels)}
<div class="note" style="left:96px; top:1124px; width:420px; font-size:15px">A re-encode moves a tile and its neighbour together, so <b>the comparison holds where the value moves</b>: the median JPEG at q75 kept 96% of its bits.</div>
<div class="rows" style="position:absolute; left:586px; top:978px; width:420px">
  <div><span>the image against <b>itself</b></span><code>bar 100%</code><span class="ok">100%</span></div>
  <div><span>a <b>half-area crop</b>, offset found</span><code>≥ 60%</code><span class="ok">73.2%</span></div>
  <div><span>a <b>JPEG q75</b>, median score</span><code>≥ 0.75</code><span class="ok">0.958</span></div>
  <div><span><b>crop recall</b> at 0.73</span><code>≥ 80%</code><span class="ok">81.3%</span></div>
  <div><span><b>false matches</b> there</span><code>≤ 5%</code><span class="ok">0%</span></div>
  <div><span>a <b>resize</b>, 0.9× or 0.75×</span><code>out of scope</code><span class="no">none</span></div>
</div>
<div class="note" style="left:1076px; top:984px; width:430px; font-size:15.5px">
  <p style="margin:0 0 9px">After the final check clears, before the frame is handed back: <code style="font-family:{MONO};font-style:normal;font-size:12.5px;color:#c3c0b7">Watermark.sign</code> on the native frame.</p>
  <p style="margin:0 0 9px">A <b>halted run is never signed</b>: it never made an image.</p>
  <p style="margin:0">Generated frames are multiples of 32, so <b>every pixel sits in a tile</b>, and the signature covers all of it.</p>
</div>"""
    return plate("garde-sign.png", 1300, "RAO STUDIOS · VEIL · VEILGARDE’S WATERMARK · PROPOSED",
                 "Signed as it leaves", "a finished generation keeps its pixels; the signature is read off them, and kept",
                 body, "a proposal: Veil does not sign yet. The signature, its numbers and its limits are VeilWatermark v1’s")


# MARK: Found in the wild

REGISTRY = [("veil · this Mac", "1c9e07…", .50, False), ("service A", "a71f3b…", .53, False),
            ("service A", "0be2d4…", .698, False), ("service B", "4d07a9…", .94, True), ("service C", "e3a15c…", .48, False)]
CROP = (3, 2, 12, 13)                                       # the found crop's first row, column, rows and columns, in tiles


def garde_wild():
    rng = random.Random(31)
    gen = generation()
    r0, c0, rows, cols = CROP
    found = [[tuple(round(v / 24) * 24 + rng.uniform(-5, 5) for v in gen[r][c]) for c in range(c0, c0 + cols)] for r in range(r0, r0 + rows)]
    bits = measured_bits(rows, cols)
    score = next(v for _, _, v, hit in REGISTRY if hit)
    z = (score - .5) / math.sqrt(.25 / bits)
    s, labels = [], []

    FX, FY, cell = 100, 566, 11
    s.append(mosaic(FX, FY, found, cell))
    s.append(frame(FX, FY, cols * cell))
    fy_mid = FY + rows * cell / 2
    labels.append(lab(FX, FY + rows * cell + 12, 160, "a crop, re-encoded", "found: no name", align="left"))

    # The fork into two questions.
    UP, LOW = 504, 762
    s.append(f'<path d="M{FX + cols * cell + 8},{fy_mid} L274,{fy_mid} L274,{UP} L292,{UP} M274,{fy_mid} L274,{LOW} L292,{LOW}" fill="none" stroke="{DIAL}" stroke-width="1.6"/>')
    s.append(arrowhead(294, UP, "right", DIAL) + arrowhead(294, LOW, "right", DIAL))

    stages = [("Decode", 104), ("Shared Signals", 150), ("Stack", 92), ("Revisions", 120), ("Result", 98)]
    x = 304
    for i, (name, w) in enumerate(stages):
        s.append(f'<rect x="{x}" y="{UP - 22}" width="{w}" height="44" rx="9" fill="{GREEN}" fill-opacity=".12" stroke="{GREEN}" stroke-opacity=".5"/>')
        labels.append(f'<div class="chipname" style="left:{x}px; top:{UP - 11}px; width:{w}px">{name}</div>')
        x += w
        if i < len(stages) - 1:
            s.append(reply(x + 6, x + 22, UP, DIAL, 1.4))
            x += 28
    s.append(reply(x + 10, 1060, UP, DIAL, 1.6))
    s.append(f'<line x1="1404" y1="{UP}" x2="1468" y2="{UP}" stroke="{LINE}" stroke-width="2"/>'
             f'<circle cx="1482" cy="{UP}" r="13" fill="none" stroke="{GOLD}" stroke-width="2.4"/><circle cx="1482" cy="{UP}" r="4.5" fill="{GOLD}"/>')
    labels.append(f'<div class="verdict" style="left:1072px; top:{UP - 19}px"><span>verdict</span> <b>generated</b> <span>P(AI)</span> <b>0.81</b></div>')
    labels.append(f'<div class="lanehead" style="left:304px; top:{UP - 62}px"><b>detection</b><span class="machine">VEILGARDE ROUTE</span></div>')
    labels.append(f'<div class="note" style="left:304px; top:{UP + 32}px; width:900px; font-size:15.5px">says <b>whether</b>: a probability, read from what generators leave, with no name attached</div>')

    # The watermark lane.
    labels.append(f'<div class="lanehead" style="left:304px; top:{LOW - 102}px"><b>the watermark</b><span class="machine">WATERMARK MATCH</span></div>')
    PX, PY, side = 304, LOW - 52, 104
    s.append(f'<rect x="{PX}" y="{PY}" width="{side}" height="{side}" rx="3" fill="rgba(255,255,255,.03)" stroke="rgba(255,255,255,.2)"/>')
    for py in (0, 8, 16, 24):
        for px in (0, 8, 16, 24):
            s.append(f'<circle cx="{PX + 10 + px * 2.7}" cy="{PY + 10 + py * 2.7}" r="3.4" fill="{GOLD}" fill-opacity="{.95 if (px, py) == (8, 16) else .35}"/>')
    labels.append(lab(PX + side / 2, PY + side + 12, 170, "16 grid phases", "{0, 8, 16, 24}² px"))

    fr = fragility(random.Random(9))
    nib, _ = codes(fr)
    CX, CY, cc = 448, LOW - 52, 26
    for r in range(4):
        for c in range(4):
            s.append(f'<rect x="{CX + c * cc}" y="{CY + r * cc}" width="{cc - 3}" height="{cc - 3}" rx="3" fill="rgba(255,255,255,.04)" stroke="rgba(199,166,89,.4)"/>')
            labels.append(f'<div class="nib" style="left:{CX + c * cc}px; top:{CY + 4 + r * cc}px; width:{cc - 3}px">{nib[r + r0][c + c0]:x}</div>')
    labels.append(lab(CX + 50, PY + side + 12, 130, "its codes", "at each phase"))

    SX, SY = 612, LOW - 56
    for r in range(9):
        for c in range(9):
            s.append(f'<rect x="{SX + c * 13}" y="{SY + r * 13}" width="11" height="11" rx="1.5" fill="rgba(255,255,255,.08)"/>')
    s.append(f'<rect x="{SX + 2 * 13 - 2}" y="{SY + 3 * 13 - 2}" width="{6 * 13 + 3}" height="{5 * 13 + 3}" rx="2" fill="{GOLD}" fill-opacity=".12" stroke="{GOLD}" stroke-width="1.6"/>')
    s.append(f'<path d="M{SX + 2 * 13 + 30},{SY + 3 * 13 + 32} l-16,-14 m16,14 l16,14 m-16,-14 l18,-14 m-18,14 l-18,14" stroke="{GOLD}" stroke-opacity=".45" stroke-width="1"/>')
    labels.append(lab(SX + 58, PY + side + 12, 190, "slid over each signature", "every whole-tile offset"))

    for x0, x1 in ((PX + side + 8, CX - 10), (CX + 4 * cc + 6, SX - 10), (SX + 9 * 13 + 10, 776)):
        s.append(reply(x0, x1, LOW, DIAL, 1.6))

    # The registry's scores.
    RX, RW, ry0, rh = 790, 380, LOW - 74, 31
    bar0, bar1 = RX + 168, RX + RW

    def at(v):
        return bar0 + (v - .4) / .6 * (bar1 - bar0)

    for i, (who, cid, v, hit) in enumerate(REGISTRY):
        y = ry0 + i * rh
        colour = GOLD if hit else "#6d6b65"
        s.append(f'<rect x="{bar0}" y="{y + 7}" width="{at(v) - bar0:.1f}" height="12" rx="3" fill="{colour}" fill-opacity="{.85 if hit else .7}"/>')
        labels.append(f'<div class="reg" style="left:{RX}px; top:{y + 4}px"><b style="color:{"#ecebe5" if hit else "#a29f97"}">{who}</b> <code>{cid}</code></div>')
        labels.append(f'<div class="score" style="left:{at(v) + 6:.0f}px; top:{y + 5}px; color:{GOLD if hit else "#8b8a84"}">{v:.2f}</div>')
    tx = at(.75)
    s.append(f'<line x1="{tx}" y1="{ry0 - 8}" x2="{tx}" y2="{ry0 + len(REGISTRY) * rh + 2}" stroke="{LINE}" stroke-dasharray="3 4" stroke-opacity=".7"/>')
    labels.append(f'<div class="wire" style="left:{tx - 120}px; top:{ry0 + len(REGISTRY) * rh + 6}px; font-size:11.5px">a match: ≥ 0.75 over ≥ 256 bits</div>')
    s.append(reply(RX + RW + 14, 1196, LOW, GOLD, 1.8))

    found_card = (head("service B", GOLD, "SIGNED")
                  + '<p>its run <code>4d07a9…</code></p>'
                  + '<p><b>offset (2, 3) tiles</b>, phase (8, 16)</p>'
                  + f'<p>score <b>{score:.2f}</b> over {bits} bits, z {z:.1f}</p>')

    body = f"""<style>
.chipname {{ position: absolute; text-align: center; font-size: 17px; color: #ecebe5; }}
.verdict {{ position: absolute; font-size: 26px; color: #ecebe5; white-space: nowrap; }}
.verdict span {{ font-size: 18px; color: #8b8a84; margin: 0 4px 0 14px; }}
.verdict span:first-child {{ margin-left: 0; }}
.lanehead {{ position: absolute; width: 1200px; display: flex; gap: 18px; align-items: baseline; }}
.lanehead b {{ font-weight: 400; font-size: 22px; color: #ecebe5; }}
.nib {{ position: absolute; text-align: center; font-family: {MONO}; font-style: normal; font-size: 12.5px; color: #dcdad3; }}
.reg {{ position: absolute; font-size: 15.5px; white-space: nowrap; }}
.reg b {{ font-weight: 400; }}
.reg code {{ font-family: {MONO}; font-style: normal; font-size: 11px; color: #77756f; margin-left: 4px; }}
.score {{ position: absolute; font-family: {MONO}; font-style: normal; font-size: 12px; background: #1d1d1a; padding: 0 3px; }}
.pair {{ position: absolute; display: grid; grid-template-columns: 1fr 1fr; column-gap: 16px; }}
.pair > div {{ border: 1px solid rgba(255,255,255,.09); border-radius: 10px; padding: 11px 14px; }}
.pair b {{ display: block; font-weight: 400; font-size: 19px; color: #ecebe5; }}
.pair code {{ font-family: {MONO}; font-style: normal; font-size: 11.5px; color: #8b8a84; }}
.pair span {{ display: block; font-size: 15px; line-height: 1.34; color: #a29f97; margin-top: 5px; }}
.pair span em {{ font-style: italic; color: #ecebe5; }}
.rows > div {{ grid-template-columns: 30px 1fr; }}
.rows .step {{ margin: 0; }}
</style>
{card(70, 374, 1460, 548, head(step(1) + "One picture, two questions", GOLD, ""))}
{card(1210, LOW - 88, 294, 176, found_card, "inner")}
{card(70, 946, 720, 272, head(step(2) + "Whether, and whose", GOLD, "WHAT EACH CAN SAY"))}
{card(810, 946, 720, 272, head(step(3) + "If generators sign", GOLD, "VEILWATERMARK, ADOPTED"))}
<svg width="{W}" height="1400">{"".join(s)}</svg>
{"".join(labels)}
<div class="pair" style="left:96px; top:998px; width:668px">
  <div><b>detection</b><code>veilgarde route</code><span>A probability, for any picture. Of unseen pictures, v1 calls <em>90.0%</em> of the real ones real and <em>34.5%</em> of the generated ones generated: it reads what generators leave, and misses what it has not learned.</span></div>
  <div><b>the watermark</b><code>watermark match</code><span>A yes with a place, for a signed picture: <em>≥ 0.75 over ≥ 256 bits</em>, and where the crop sat. Across 198 pictures no crop matched a stranger; the best stranger scored <em>0.698</em>.</span></div>
</div>
<div class="rows" style="position:absolute; left:836px; top:996px; width:668px">
  <div><span class="step">1</span><span>each service <b>signs a picture as it is made</b>, and keeps the <code>vw1</code> beside the run</span></div>
  <div><span class="step">2</span><span>a found picture’s codes are <b>matched against the kept signatures</b>; the one that clears 0.75 names its source</span></div>
  <div><span class="step">3</span><span>an <b>untouched copy</b> signs to the same <code>cid</code>: one lookup; a crop or a re-encode takes the slide</span></div>
</div>
<div class="note" style="left:836px; top:1150px; width:668px; font-size:15px">Nothing is added to the pixels, so there is nothing to strip. <b>A resize defeats v1</b>, and matching against millions of signatures needs an index over their section words: both open.</div>"""
    return plate("garde-wild.png", 1300, "RAO STUDIOS · VEIL · VEILGARDE IN THE WILD",
                 "Found in the wild", "a detector can say generated; a signature can say whose",
                 body, "the found picture, the registry and its scores are illustrative; the thresholds and measured numbers are v1’s")


# MARK: Kept, never seen (Veil8 at ingest)

# PIPELINE.md, "What leaves this Mac": per tile a vector, the caption and ontology as text (none with
# --no-ontology), the file's name, the SHA-256 id, and the manifest; the strings are embedded in Veil's
# process and the key never leaves. The inversion: 14.6–15.5 dB PSNR with the key and a trained decoder,
# against 13.2 dB for painting every pixel the average colour.

def smear(grid, passes=2, radius=2, keep=.6):
    """Roughly what a decoder holding the key gets back: local average colours, little else."""
    n = len(grid)
    out = grid
    for _ in range(passes):
        nxt = []
        for r in range(n):
            row = []
            for c in range(n):
                nb = [out[rr][cc] for rr in range(max(0, r - radius), min(n, r + radius + 1)) for cc in range(max(0, c - radius), min(n, c + radius + 1))]
                row.append(tuple(sum(p[k] for p in nb) / len(nb) for k in range(3)))
            nxt.append(row)
        out = nxt
    mean = average(grid)
    return [[tuple(mean[k] + (v[k] - mean[k]) * keep for k in range(3)) for v in row] for row in out]


def average(grid):
    n = len(grid)
    return tuple(sum(grid[r][c][k] for r in range(n) for c in range(n)) / n / n for k in range(3))


def chip(x, y, w, h, text, colour=LINE, fill=.05, dashed=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    svg = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{colour}" fill-opacity="{fill}" stroke="{colour}" stroke-opacity=".55"{dash}/>'
    html = f'<div class="chipt" style="left:{x}px; top:{y}px; width:{w}px; height:{h}px">{text}</div>'
    return svg, html


INGEST_CSS = f"""<style>
.words {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); border-radius: 9px; padding: 13px 14px;
         font-family: {MONO}; font-style: normal; font-size: 13.5px; line-height: 1.62; letter-spacing: .02em; color: #dcdad3; }}
.chipt {{ position: absolute; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 0 8px; }}
.chipt b {{ font-weight: 400; font-size: 16px; color: #ecebe5; line-height: 1.2; }}
.chipt span {{ font-family: {MONO}; font-style: normal; font-size: 11px; color: #8b8a84; margin-top: 3px; }}
.stays {{ position: absolute; font-size: 16px; color: #a29f97; }}
.stays b {{ font-weight: 400; color: {GOLD}; }}
.held > div {{ grid-template-columns: 1fr auto; }}
.held code {{ font-family: {MONO}; font-style: normal; }}
.never {{ margin-top: 14px; padding-top: 10px; border-top: 1px dashed rgba(216,119,63,.4); font-size: 15px; }}
.never > div {{ margin-top: 6px; color: #a29f97; }}
.never b {{ font-weight: 400; color: #ecebe5; }}
.big {{ position: absolute; font-size: 18px; color: #ecebe5; }}
.mono {{ font-family: {MONO}; font-style: normal; }}
.wall {{ position: absolute; width: 164px; font-size: 14.5px; line-height: 1.3; color: #a29f97; text-align: center; }}
.wall b {{ font-weight: 400; color: #ecebe5; }}
.cos {{ position: absolute; width: 116px; display: flex; flex-direction: column; align-items: center; text-align: center; }}
.cos span {{ font-size: 15px; color: #a29f97; }}
.cos b {{ font-family: {MONO}; font-style: normal; font-weight: 400; font-size: 22px; color: {GOLD}; margin-top: 2px; }}
.cos code {{ font-family: {MONO}; font-style: normal; font-size: 10.5px; color: #8b8a84; margin-top: 4px; white-space: normal; line-height: 1.3; }}
</style>"""


def veil8_ingest():
    rng = random.Random(12)
    pic = scene()
    s, labels = [], []

    # The user's Mac, and everything that never leaves it.
    s.append('<rect x="96" y="428" width="934" height="438" rx="12" fill="none" stroke="rgba(199,166,89,.5)" stroke-dasharray="7 6"/>')
    labels.append('<div class="machine" style="position:absolute; left:116px; top:442px; color:#a8925a">THE USER’S MAC</div>')

    Y, SZ = 492, 128
    mid = Y + SZ / 2
    s.append(mosaic(120, Y, pic, 8))
    s.append(frame(120, Y, SZ))
    labels.append(f'<div class="words" style="left:318px; top:{Y}px; width:286px; height:{SZ}px">'
                  + "<br>".join(" ".join(words(rng, 9)) for _ in range(4)) + " …</div>")
    vec = [max(-1, min(1, rng.gauss(0, .6))) for _ in range(26)]
    s.append(barcode(668, Y + 14, 112, SZ - 28, vec, LINE))
    s.append(reply(258, 308, mid, DIAL, 1.6) + reply(612, 658, mid, DIAL, 1.6))
    # The key, into the words and nowhere else.
    s.append(f'<circle cx="461" cy="462" r="7" fill="none" stroke="{GOLD}" stroke-width="2"/>'
             f'<line x1="468" y1="462" x2="492" y2="462" stroke="{GOLD}" stroke-width="2"/><line x1="486" y1="462" x2="486" y2="469" stroke="{GOLD}" stroke-width="2"/>')
    s.append(vertical(461, 470, Y - 4, GOLD, dashed=True))
    labels.append(f'<div class="wire" style="left:500px; top:454px; color:{GOLD}">the key</div>')
    labels += [lab(184, Y + SZ + 12, 200, "the picture", "cut into 32×32 tiles"),
               lab(461, Y + SZ + 12, 286, "rgb-veil8 words", "a word a pixel · no way back"),
               lab(724, Y + SZ + 12, 200, "a vector a tile", "voyage-4-nano, in Veil")]

    # Out across the edge: vectors only.
    s.append(f'<path d="M790,{mid} L1056,{mid} L1056,497 L1090,497" fill="none" stroke="{GOLD}" stroke-width="2.4" stroke-linejoin="round"/>'
             + arrowhead(1092, 497, "right", GOLD))
    labels.append(f'<div class="wire" style="left:878px; top:{mid - 24}px; color:{GOLD}">vectors only</div>')

    # The caption: words about the picture, from the vision model on this Mac, and optional.
    VY = 728
    s.append(mosaic(136, VY, pic, 6))
    s.append(frame(136, VY, 96))
    c1 = chip(270, VY + 22, 196, 52, "<b>the vision model</b><span>on this Mac</span>")
    c2 = chip(500, VY + 14, 290, 68, "<b>“a gold sun over a dark ridge, at dusk”</b><span>sunset · ridge · painting</span>")
    s += [c1[0], c2[0]]
    labels += [c1[1], c2[1]]
    s.append(reply(240, 262, VY + 48, DIAL, 1.6) + reply(474, 492, VY + 48, DIAL, 1.6))
    s.append(f'<path d="M798,{VY + 48} L1078,{VY + 48} L1078,533 L1092,533" fill="none" stroke="{LINE}" stroke-width="1.6" stroke-dasharray="6 5"/>'
             + arrowhead(1092, 533, "right", LINE))
    labels.append(f'<div class="wire" style="left:812px; top:{VY + 56}px">words about it · optional</div>')
    labels.append(f'<div class="wire" style="left:812px; top:{VY + 74}px; color:#77756f">--no-ontology sends none</div>')
    labels.append(f'<div class="stays" style="left:120px; top:{VY + 106}px">stays here: <b>the picture</b> · <b>the key</b> · <b>the tile strings</b> · <b>the file’s place</b></div>')

    index = (head("What the index holds", BLUE, "THREAD")
             + '<div class="rows held">'
               '<div><span><b>a vector a tile</b></span><code>1,024 numbers</code></div>'
               '<div><span><b>the caption and tags</b></span><code>optional</code></div>'
               '<div><span><b>the document id</b></span><code>SHA-256 of the pixels</code></div>'
               '<div><span><b>how it was written</b></span><code>encoding · fingerprint · embedder</code></div>'
               '<div><span><b>the file’s name</b></span><code>never its place</code></div></div>'
             + '<p>Enough to recognise the picture, and to check an exact copy was filed. <b>Not enough to show it.</b></p>'
             + f'<div class="never"><span class="machine" style="color:{ORANGE}">NEVER SENT</span>'
               '<div>✕ <b>the pixels</b></div><div>✕ <b>the key</b>, only its fingerprint</div>'
               '<div>✕ <b>the tile strings</b>: embedded in Veil’s process</div></div>')

    body = f"""{INGEST_CSS}
{card(70, 374, 1460, 512, head(step(1) + "What leaves the picture’s Mac", GOLD, "INGESTPIPELINE"))}
{card(1100, 428, 404, 438, index, "inner")}
<svg width="{W}" height="1000">{"".join(s)}</svg>
{"".join(labels)}"""
    return plate("veil8-ingest.png", 968, "RAO STUDIOS · VEIL · VEIL8 AT INGEST",
                 "Kept, never seen", "a picture becomes words no one can read back; the index can recognise it, never show it",
                 body, "the picture, words and caption are illustrative; what leaves is from docs/PIPELINE.md")


# MARK: No way back (Veil8's words, and a generation step against them)

def veil8_reverse():
    rng = random.Random(12)
    pic = scene()
    vec = [max(-1, min(1, rng.gauss(0, .6))) for _ in range(26)]
    s, labels = [], []

    T = 374
    # Card 1, left: a direct translation reads straight back; a Veil8 word fits thousands of windows.
    swatch = (216, 119, 63)
    s.append(f'<rect x="96" y="{T + 100}" width="36" height="36" rx="4" fill="{hexrgb(swatch)}"/>'
             f'<rect x="318" y="{T + 100}" width="36" height="36" rx="4" fill="{hexrgb(swatch)}"/>')
    s.append(reply(140, 166, T + 118, DIAL, 1.4) + reply(282, 308, T + 118, DIAL, 1.4))
    labels.append(f'<div class="big mono" style="left:176px; top:{T + 105}px">d8 77 3f</div>')
    labels.append(f'<div class="wire" style="left:366px; top:{T + 110}px; color:{GREEN}">the same pixel, exactly</div>')
    labels.append(f'<div class="machine" style="position:absolute; left:96px; top:{T + 74}px">A DIRECT TRANSLATION · WHAT VEIL8 IS NOT</div>')
    labels.append(f'<div class="machine" style="position:absolute; left:96px; top:{T + 162}px; color:{GOLD}">VEIL8 · ONE PIXEL’S WORD</div>')

    def window(x, y, cell, seed):
        r = random.Random(seed)
        return "".join(f'<rect x="{x + c * cell}" y="{y + rr * cell}" width="{cell - 1}" height="{cell - 1}" rx="1" '
                       f'fill="{hexrgb((r.uniform(40, 230), r.uniform(40, 200), r.uniform(40, 220)))}"/>' for rr in range(5) for c in range(5))

    s.append(window(96, T + 186, 12, 2))
    s.append(reply(166, 192, T + 216, DIAL, 1.4) + reply(246, 272, T + 216, DIAL, 1.4))
    labels.append(f'<div style="position:absolute; left:202px; top:{T + 194}px; font-size:32px; color:#ecebe5">ip</div>')
    for i in range(4):
        s.append(window(282 + i * 40, T + 201, 6, 40 + i))
    labels.append(f'<div class="wire" style="left:282px; top:{T + 238}px">all write “ip”, and thousands more</div>')
    labels.append(f'<div class="note" style="left:96px; top:{T + 272}px; width:440px; font-size:15px">A translation keeps every value, so it reads straight back. '
                  'Veil8 keeps <b>8 bits of 75 values</b>, mixed under a key: <b>a measurement, not a translation</b>.</div>')
    s.append(f'<line x1="566" y1="{T + 74}" x2="566" y2="{T + 352}" stroke="rgba(255,255,255,.08)"/>')

    # Card 1, right: the way back from what is held, and what stops each step of it.
    labels.append(f'<div class="machine" style="position:absolute; left:596px; top:{T + 74}px; color:{ORANGE}">THE WAY BACK, FROM WHAT IS HELD</div>')
    NY = T + 102
    s.append(barcode(596, NY, 90, 58, [max(-1, min(1, rng.gauss(0, .6))) for _ in range(18)], LINE))
    labels.append(f'<div class="words" style="left:748px; top:{NY}px; width:122px; height:58px; padding:8px 10px; font-size:12.5px; line-height:1.5">'
                  'ip lk dw rc<br>tw np if wk</div>')
    for i, bit in enumerate(WORD_BITS):
        s.append(f'<rect x="{930 + i * 14}" y="{NY + 18}" width="12" height="22" rx="2" fill="{GOLD if bit else "none"}" fill-opacity=".18" stroke="{GOLD if bit else "#5d5b56"}"/>')
    for rr in range(5):
        for c in range(5):
            s.append(f'<rect x="{1104 + c * 11}" y="{NY + 2 + rr * 11}" width="10" height="10" rx="1" fill="#3a3935"/>')
    labels.append(f'<div style="position:absolute; left:1104px; top:{NY + 8}px; width:55px; text-align:center; font-size:32px; color:#ecebe5">?</div>')
    for x in (718, 900, 1074):
        s.append(f'<line x1="{x}" y1="{NY - 6}" x2="{x}" y2="{NY + 64}" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="4 4" stroke-opacity=".8"/>'
                 f'<path d="M{x - 9},{NY + 20} L{x + 9},{NY + 38} M{x + 9},{NY + 20} L{x - 9},{NY + 38}" stroke="{ORANGE}" stroke-width="2.2" stroke-linecap="round"/>')
    s.append(reply(1168, 1196, NY + 29, DIAL, 1.4))
    s.append(mosaic(1210, NY - 8, smear(pic), 4.5, gap=.5) + frame(1210, NY - 8, 72))
    s.append(f'<rect x="1340" y="{NY - 8}" width="72" height="72" rx="2" fill="{hexrgb(average(pic))}"/>' + frame(1340, NY - 8, 72))
    labels += [lab(641, NY + 72, 120, "a vector"), lab(809, NY + 72, 130, "the words"),
               lab(986, NY + 72, 120, "the bits"), lab(1131, NY + 72, 120, "the pixels"),
               lab(1246, NY + 72, 120, "decoded", "14.6–15.5 dB"), lab(1376, NY + 72, 120, "the average", "13.2 dB")]
    walls = [(718, "<b>The embedder summarises</b> the words in 1,024 numbers; it does not spell them out."),
             (900, "<b>Only the key</b> says which measurement each bit is, and with what weights."),
             (1074, "<b>8 bits for 75 values</b>: the floor and <i>mod 2</i> drop the rest, and thousands of windows fit.")]
    for x, text in walls:
        labels.append(f'<div class="wall" style="left:{x - 82}px; top:{NY + 108}px">{text}</div>')
    labels.append(f'<div class="wall" style="left:1196px; top:{NY + 120}px; width:300px">Even past all three, <b>a smear</b>: barely above painting the average.</div>')
    labels.append(f'<div class="note" style="left:596px; top:{T + 304}px; width:908px; font-size:15px">The measured attack began at the words, <b>holding the key</b>, with a decoder trained on other pictures: '
                  'a step closer than anyone who holds only the vectors.</div>')

    T = 770
    # Card 2: one denoising step, its output, and the comparison with the stored embedding.
    GY = T + 70
    noisy = estimate(pic, random.Random(13), contrast=.35, noise=60)
    est = estimate(pic, random.Random(11))
    s.append(mosaic(96, GY, noisy, 6) + frame(96, GY, 96))
    s.append(mosaic(234, GY, est, 6) + frame(234, GY, 96))
    labels.append(f'<div class="words" style="left:372px; top:{GY}px; width:180px; height:96px; font-size:13px; padding:12px 12px">'
                  + "<br>".join(" ".join(words(random.Random(70 + i), 5)) for i in range(3)) + "</div>")
    s.append(barcode(594, GY + 10, 100, 76, vec, GOLD))
    s.append(barcode(836, GY + 10, 100, 76, [max(-1, min(1, v + random.Random(i).gauss(0, .06))) for i, v in enumerate(vec)], LINE))
    for x0, x1 in ((198, 226), (336, 364), (560, 586)):
        s.append(reply(x0, x1, GY + 48, DIAL, 1.6))
    labels.append(f'<div class="cos" style="left:713px; top:{GY + 14}px"><span>cosine</span><b>0.962</b><code>a tile counts at τ 0.945</code></div>')
    s.append(f'<path d="M944,{GY + 48} L966,{GY + 48} M966,{GY + 20} L966,{GY + 76}" fill="none" stroke="{DIAL}" stroke-width="1.4"/>'
             + reply(966, 986, GY + 20, DIAL, 1.4) + reply(966, 986, GY + 76, DIAL, 1.4))
    g3 = chip(994, GY, 196, 40, "<b>below τ: the next step</b>", GREEN, .1)
    g4 = chip(994, GY + 56, 196, 40, "<b>a copy, tile after tile: halt</b>", GOLD, .12)
    for c in (g3, g4):
        s.append(c[0])
        labels.append(c[1])
    labels += [lab(144, GY + 106, 150, "a denoising step", "step 10 of 20"),
               lab(282, GY + 106, 150, "its output", "x̂0, decoded"),
               lab(462, GY + 106, 180, "the same words", "same key, same Mac"),
               lab(644, GY + 106, 150, "its embedding", "this step’s"),
               lab(886, GY + 106, 190, "the stored embedding", "filed at ingest")]
    labels.append(f'<div class="note" style="left:1222px; top:{T + 72}px; width:282px; font-size:15px">The stored side never changes, and the protected picture <b>is never opened again</b>: the step is measured against its embedding alone.</div>')
    labels.append(f'<div class="note" style="left:96px; top:{T + 232}px; width:1408px; font-size:15px">At each planned step the model’s guess at the finished picture is decoded, written in Veil8 under the same key, embedded, and scored <b>tile by tile against the embeddings stored at ingest</b>. Vector against vector: neither side is ever turned back into a picture.</div>')

    body = f"""{INGEST_CSS}
{card(70, 374, 1460, 372, head(step(1) + "Why there is no way back", GOLD, "THE REVERSE ROUTE"))}
{card(70, 770, 1460, 292, head(step(2) + "At generation: a step against what was stored", GOLD, "VEILLAYER"))}
<svg width="{W}" height="1180">{"".join(s)}</svg>
{"".join(labels)}"""
    return plate("veil8-reverse.png", 1144, "RAO STUDIOS · VEIL · VEIL8, NO WAY BACK",
                 "No way back", "Veil8 measures a picture, it does not translate it; a step is checked vector against vector",
                 body, "the picture, words and smear are illustrative; the decibels are Veil’s measurement (docs/PIPELINE.md)")


# MARK: Weights to pixels (the executor)

# Sources/VeilSD: SDLoad finds the diffusers safetensors, remaps the names onto the ported modules
# (Apple's mlx-swift-examples) and refuses a checkpoint that leaves a parameter unfilled; SDModel keeps
# them resident (fp16, the VAE in fp32); SDExecutor runs the loop; SDPreview decodes, Tiler.rgba8 makes
# bytes, RGBAImage.cgImage() and ImageWriter make the CGImage. UIImage and CVPixelBuffer are not in Veil.

EXEC_CSS = f"""<style>
.box {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); border-radius: 9px; padding: 11px 13px;
       font-family: {MONO}; font-style: normal; font-size: 12px; line-height: 1.7; color: #dcdad3; white-space: pre; }}
.box i {{ font-style: normal; color: #8b8a84; }}
.box em {{ font-style: normal; color: {GOLD}; }}
.box s {{ text-decoration: none; color: {ORANGE}; }}
.lane {{ position: absolute; width: 150px; display: flex; flex-direction: column; }}
.lane b {{ font-weight: 400; font-size: 21px; color: #ecebe5; }}
.lane code {{ font-family: {MONO}; font-style: normal; font-size: 12px; color: #a7a49b; margin-top: 4px; }}
.lane span {{ font-size: 15px; line-height: 1.3; margin-top: 5px; }}
.mod {{ position: absolute; box-sizing: border-box; height: 22px; border-radius: 5px; padding: 0 9px; display: flex; justify-content: space-between; align-items: center;
       font-size: 14.5px; color: #ecebe5; }}
.mod code {{ font-family: {MONO}; font-style: normal; font-size: 11px; color: #a7a49b; }}
.chipt {{ position: absolute; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 0 8px; }}
.chipt b {{ font-weight: 400; font-size: 15px; color: #ecebe5; line-height: 1.2; }}
.chipt span {{ font-family: {MONO}; font-style: normal; font-size: 11px; color: #8b8a84; margin-top: 3px; }}
.big {{ position: absolute; font-size: 18px; color: #ecebe5; }}
.mono {{ font-family: {MONO}; font-style: normal; }}
</style>"""


def noise_grid(seed, n=16, base=(120, 120, 120), spread=70):
    r = random.Random(seed)
    return [[tuple(clamp(base[k] + r.gauss(0, spread)) for k in range(3)) for _ in range(n)] for _ in range(n)]


def latent(x, y, size, grids):
    """Four channels, drawn as four offset squares: the 64×64×4 latent the UNet works in."""
    s = []
    for i, g in enumerate(reversed(grids)):
        off = (len(grids) - 1 - i) * 7
        s.append(mosaic(x + off, y + off, g, size / len(g), gap=0) + frame(x + off, y + off, size, "rgba(255,255,255,.22)"))
    return "".join(s)


def executor():
    pic = scene()
    s, labels = [], []
    A, B, C, H = 494, 760, 1024, 150                        # the three rows' tops, and their drawings' height

    def module(name, x, y, w, h):
        """A stage of the executor: a dashed frame, its name above."""
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" stroke="rgba(199,166,89,.45)" stroke-dasharray="7 6"/>')
        labels.append(f'<div class="lab" style="left:{x - 2}px; top:{y - 30}px"><b style="font-size:21px; color:{GOLD}">{name}</b></div>')


    # Row A, the harness: built once. The folder, a safetensors file's table, the code it fits, the network in memory.
    module("The Harness", 248, A - 14, 1270, H + 28)
    labels.append(f'<div class="lane" style="left:96px; top:{A + 18}px"><b>built once</b><code>prepare()</code>'
                  f'<span>the weights load, and stay</span></div>')
    labels.append(f'<div class="box" style="left:262px; top:{A}px; width:252px; height:{H}px">stable-diffusion-v1-5/\n'
                  '├ tokenizer/    <i>vocab · merges</i>\n├ text_encoder/ <em>.safetensors</em>\n├ unet/         <em>.safetensors</em>\n'
                  '├ vae/          <em>.safetensors</em>\n└ scheduler/    <i>config.json</i></div>')
    labels.append(f'<div class="box" style="left:556px; top:{A}px; width:300px; height:{H}px"><i>the header: a name, a dtype, a shape</i>\n'
                  'conv_in.weight      F16 320·4·3·3\n…attn1.to_q.weight  F16 320·320\n…norm1.bias         F16 320\n'
                  '<i>…then the raw bytes, back to back</i>\n<i>no code, no graph</i></div>')
    labels.append(f'<div class="box" style="left:898px; top:{A}px; width:226px; height:{H}px"><em>UNetModel(config)</em>\n<i>  built empty: random</i>\n'
                  'to_q    → query_proj\n320·4·3·3 → 320·3·3·4\n<i>  channels last</i>\nevery parameter <em>filled</em></div>')
    # The network, resident: the modules the checkpoint filled, and the two that hold no weights.
    s.append(f'<rect x="1166" y="{A}" width="338" height="{H}" rx="9" fill="{BLUE}" fill-opacity=".05" stroke="{BLUE}" stroke-opacity=".5"/>')
    labels.append(f'<div class="machine" style="position:absolute; left:1180px; top:{A + 9}px; color:#7d9fd6">GPU · UNIFIED MEMORY</div>')
    mods = [("tokenizer", "77 ids", LINE, .04), ("CLIP text encoder", "fp16", GOLD, .14), ("UNet", "fp16 · most of the weights", GOLD, .22),
            ("VAE", "fp32", GOLD, .14), ("Euler sampler", "schedule only", LINE, .04)]
    for i, (name, code, colour, fill) in enumerate(mods):
        y = A + 30 + i * 23.5
        s.append(f'<rect x="1180" y="{y}" width="310" height="20" rx="5" fill="{colour}" fill-opacity="{fill}" stroke="{colour}" stroke-opacity=".35"/>')
        labels.append(f'<div class="mod" style="left:1180px; top:{y - 1}px; width:310px">{name}<code>{code}</code></div>')
    for x0, x1 in ((518, 548), (860, 890), (1128, 1158)):
        s.append(reply(x0, x1, A + H / 2, DIAL, 1.6))
    labels += [lab(388, A + H + 24, 252, "the checkpoint", "a folder of numbers"),
               lab(706, A + H + 24, 300, "a safetensors file", "names, dtypes, shapes, bytes"),
               lab(1011, A + H + 24, 226, "the code it fits", "built, renamed, filled"),
               lab(1335, A + H + 24, 338, "the network, resident", "MLX on Metal · ≈ 2.1 GB (sd15)")]

    # Row B: per prompt, the loop. Text to conditioning; noise to a clean latent.
    labels.append(f'<div class="lane" style="left:96px; top:{B + 18}px"><b>per prompt</b><code>generate()</code>'
                  f'<span>512² · 20 steps · guidance 7.5</span></div>')
    labels.append(f'<div class="note" style="left:96px; top:{B + 122}px; width:146px; font-size:13.5px; line-height:1.3"><b>latent</b>: a compressed '
                  f'picture, 64 × 64 × 4 numbers; the model works in it, and the VAE unpacks it to 512 × 512 pixels</div>')
    # The prompt meets the harness: what prepare() loaded reads it, then drives the loop.
    labels.append(f'<div class="wire" style="left:262px; top:{B - 14}px; color:{GOLD}">↑ the harness, put to work on the prompt:</div>'
                  f'<div class="wire" style="left:262px; top:{B + 2}px">its tokenizer and CLIP read it; its UNet drives the carriage</div>')
    c1 = chip(262, B + 34, 170, 82, "<b>“a gold sun over a dark ridge, at dusk”</b><span>and the negative, “”</span>")
    s.append(c1[0])
    labels.append(c1[1])
    labels.append(f'<div class="box" style="left:462px; top:{B + 34}px; width:134px; height:82px; text-align:center; line-height:1.55">49406 320 …\n… 49407\n<i>77 ids a row</i></div>')
    hid = noise_grid(21, n=12, base=(150, 132, 92), spread=46)
    s.append(mosaic(626, B + 27, hid, 8, gap=1) + frame(626, B + 27, 96, "rgba(199,166,89,.5)"))
    s.append(reply(436, 456, B + 75, DIAL, 1.4) + reply(600, 620, B + 75, DIAL, 1.4))
    # The carriage: noise in, the UNet's ε̂, an Euler step, twenty times; the VeilLayer rides here.
    module("The Carriage", 766, B - 4, 590, H + 8)
    labels.append(f'<div class="machine" style="position:absolute; left:782px; top:{B + 5}px; color:#a8925a">THE LOOP · ×20</div>')
    noise = [noise_grid(30 + k, n=12) for k in range(4)]
    s.append(latent(790, B + 34, 72, noise))
    s.append(reply(888, 906, B + 75, DIAL, 1.6))
    u = chip(910, B + 40, 104, 70, "<b>UNet</b><span>predicts the noise</span>", GOLD, .12)
    e = chip(1038, B + 40, 104, 70, "<b>Euler step</b><span>denoises the latent by one step</span>", LINE, .05)
    for c in (u, e):
        s.append(c[0])
        labels.append(c[1])
    s.append(reply(1018, 1034, B + 75, DIAL, 1.6) + reply(1146, 1162, B + 75, DIAL, 1.6))
    # The text conditions every UNet pass.
    s.append(f'<path d="M674,{B + 128} L674,{B + 136} L962,{B + 136} L962,{B + 116}" fill="none" stroke="{GOLD}" stroke-width="1.4" stroke-dasharray="4 4"/>'
             + arrowhead(962, B + 114, "up", GOLD))
    # Veil's insertion: after each step the layer is handed the step; at planned ones it decodes the model's guess at
    # the finished picture (x̂0) and checks it. Clear, the loop goes on; a match, the run halts there.
    s.append(f'<rect x="1166" y="{B + 30}" width="176" height="90" rx="10" fill="{GOLD}" fill-opacity=".16" stroke="{GOLD}" stroke-width="1.4"/>')
    guess = estimate(pic, random.Random(44), contrast=.7, noise=7)
    s.append(mosaic(1176, B + 51, guess, 3, gap=0) + frame(1176, B + 51, 48, "rgba(199,166,89,.6)"))
    labels.append(f'<div class="chipt" style="left:1226px; top:{B + 30}px; width:116px; height:90px; align-items:flex-start; text-align:left">'
                  f'<b style="color:{GOLD}; font-size:17px">VeilLayer</b><i style="font-size:13.5px; line-height:1.3; color:#cfccc4; margin-top:3px">is the picture so far a protected likeness?</i></div>')
    # Clear: around again. A match: the run stops, and no picture is made.
    s.append(f'<path d="M1254,{B + 30} L1254,{B + 22} L826,{B + 22} L826,{B + 30}" fill="none" stroke="{DIAL}" stroke-width="1.4"/>' + arrowhead(826, B + 32, "down", DIAL))
    labels.append(f'<div class="wire" style="left:960px; top:{B + 4}px">clear: on to the next step</div>')
    s.append(f'<path d="M1254,{B + 120} L1254,{B + 136}" stroke="{RED}" stroke-width="1.6"/>'
             f'<path d="M1244,{B + 138} L1264,{B + 138}" stroke="{RED}" stroke-width="2.2" stroke-linecap="round"/>')
    labels.append(f'<div class="wire" style="right:{W - 1236}px; top:{B + 130}px; color:{RED}">a likeness: halt, no picture</div>')
    s.append(reply(1346, 1386, B + 75, DIAL, 1.6))
    clean = [estimate(pic, random.Random(40 + k), contrast=.5, noise=10) for k in range(4)]
    s.append(latent(1400, B + 34, 72, clean))
    labels += [lab(347, B + H + 12, 170, "the prompt", "and an empty negative"),
               lab(529, B + H + 12, 134, "tokens", "CLIP’s vocabulary"),
               lab(674, B + H + 12, 140, "the text, encoded", "2 × 77 × 768"),
               lab(836, B + H + 12, 200, "noise, from the seed", "1 × 64 × 64 × 4"),
               lab(1445, B + H + 12, 140, "the final latent", "still 64 × 64 × 4")]

    # Row C, the darkroom: to the screen. The VAE, floats, bytes, a CGImage, and where it goes.
    module("The Darkroom", 248, C - 14, 1270, H + 28)
    labels.append(f'<div class="lane" style="left:96px; top:{C + 18}px"><b>to the screen</b><code>decode</code>'
                  f'<span>numbers become a picture</span></div>')
    labels.append(f'<div class="note" style="left:96px; top:{C + 116}px; width:146px; font-size:13.5px; line-height:1.3"><b>VAE</b>: a learned decoder; '
                  f'three ×2 upsamplings grow each latent cell into an 8 × 8 patch of pixels</div>')
    s.append(latent(262, C + 39, 60, clean))
    s.append(f'<path d="M358,{C + 50} L470,{C + 12} L470,{C + 138} L358,{C + 100} Z" fill="{GOLD}" fill-opacity=".12" stroke="{GOLD}" stroke-opacity=".55"/>')
    labels.append(f'<div style="position:absolute; left:358px; top:{C + 58}px; width:112px; text-align:center; font-size:17px; color:#ecebe5">VAE<br><span class="mono" style="font-size:11px; color:#a7a49b">×8 each side</span></div>')
    s.append(reply(342, 352, C + 75, DIAL, 1.4) + reply(476, 500, C + 75, DIAL, 1.6))
    s.append(mosaic(510, C + 11, pic, 8) + frame(510, C + 11, 128))
    labels.append(f'<div class="wire" style="left:516px; top:{C + 17}px; color:#ecebe5; background:rgba(20,20,18,.75); padding:1px 4px; border-radius:3px">0.70 0.21 −0.42</div>')
    s.append(reply(646, 670, C + 75, DIAL, 1.6))
    labels.append(f'<div class="box" style="left:678px; top:{C + 26}px; width:228px; height:98px; line-height:1.6">(x · 0.5 + 0.5) · 255\n'
                  '<em>d8 9b 4a ff</em>  d6 99 4c ff\nd1 95 4f ff  <i>…</i>\n<i>R G B A, a row at a time</i></div>')
    s.append(reply(910, 928, C + 75, DIAL, 1.6))
    cg = chip(934, C + 34, 176, 82, "<b>CGImage</b><span>sRGB · 8 bits a channel</span><span>w × 4 bytes a row</span>", BLUE, .1)
    s.append(cg[0])
    labels.append(cg[1])
    outs = [("SwiftUI Image", "the app", False), ("PNG", "ImageIO", False), ("UIImage(cgImage:)", "iOS", True), ("CVPixelBuffer", "video", True)]
    for i, (name, code, dashed) in enumerate(outs):
        y = C + 2 + i * 37
        c = chip(1158, y, 222, 31, f"<b>{name} <span style='display:inline; margin:0'>· {code}</span></b>", LINE if dashed else BLUE, .03 if dashed else .08, dashed)
        s.append(c[0])
        labels.append(c[1])
        s.append(f'<path d="M1114,{C + 75} C1132,{C + 75} 1134,{y + 15.5} 1150,{y + 15.5}" fill="none" stroke="{DIAL}" stroke-width="1.3"{" stroke-dasharray=\"4 4\"" if dashed else ""}/>')
    labels.append(f'<div class="note" style="left:1392px; top:{C + 78}px; width:118px; font-size:13.5px; line-height:1.3">dashed: <b>not in Veil</b>, the same bytes in another container</div>')
    labels += [lab(301, C + H + 24, 120, "the final latent"),
               lab(574, C + H + 24, 170, "pixels, as floats", "512 × 512 × 3, about −1…1"),
               lab(792, C + H + 24, 228, "pixels, as bytes", "RGBA8 · alpha 255"),
               lab(1022, C + H + 24, 176, "an image", "RGBAImage.cgImage()")]

    body = f"""{EXEC_CSS}
{card(70, 374, 1460, 888, head(step(1) + "From a file of numbers to a picture on screen", GOLD, "SDMODEL · SDEXECUTOR"))}
<svg width="{W}" height="1400">{"".join(s)}</svg>
{"".join(labels)}"""
    return plate("executor.png", 1344, "RAO STUDIOS · VEIL · THE EXECUTOR",
                 "Weights to pixels", "a checkpoint is only numbers; code builds the network around them, runs the loop, and hands back pixels",
                 body, "the picture, tokens and bytes are illustrative; the shapes, dtypes and steps are Stable Diffusion 1.5 in Sources/VeilSD")



# MARK: Checked in the carriage (the VeilLayer against a protected likeness)

# VeilSession hands the layer each planned step's frame (onStep) and returns .halt when the gate blocks.
# VeilLayer.attribute: probe the corpus, write and embed the tiles, prune to the identity groups worth
# searching (the prompt's names, its meaning and the picture's mean; once a run, ≤ 8, combined ≥ 0.15),
# search Thread within them, then the matrix, the sheet (soft share, coverage) and BlockGate.

def portrait(n=16):
    """An illustrative head and shoulders: hair, a face, a shirt, on a plain wall."""
    def inside(x, y, cx, cy, rx, ry):
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
    grid = []
    for r in range(n):
        row = []
        for c in range(n):
            x, y = c + .5, r + .5
            wall = mix((78, 86, 104), (54, 60, 76), r / (n - 1))
            if (r, c) in ((7, 6), (7, 9)):
                v = (58, 42, 38)
            elif r == 10 and c in (7, 8):
                v = (168, 94, 88)
            elif inside(x, y, 8, 7.4, 3.2, 4.1) and y > 4.4:
                v = mix((226, 182, 150), (182, 132, 104), abs(x - 8) / 3.4)
            elif inside(x, y, 8, 6.2, 4.0, 4.4) and y < 9.6:
                v = (58, 40, 32)
            elif abs(x - 8) < 1.3 and 11 < y < 13.2:
                v = (186, 138, 110)
            elif y > 12.6 and abs(x - 8) < 2.2 + (y - 12.6) * 3:
                v = mix((44, 76, 84), (30, 52, 58), abs(x - 8) / 7)
            else:
                v = wall
            row.append(tuple(v))
        grid.append(row)
    return grid


def likeness_heat(pic, rng):
    """Where the step's tiles match the identity's photos: the face and hair lit, the plain wall flat."""
    wall = mix((78, 86, 104), (54, 60, 76), 0)
    cats = []
    for r, row in enumerate(pic):
        out = []
        for c, v in enumerate(row):
            plain = all(abs(v[k] - mix((78, 86, 104), (54, 60, 76), r / 15)[k]) < 1 for k in range(3))
            if plain and (r < 3 or c < 2 or c > 13):
                out.append("flat")
            elif not plain and r < 13 and rng.random() > .12:
                out.append("attributed")
            elif rng.random() < .08:
                out.append("incoherent")
            else:
                out.append("below")
        cats.append(out)
    return cats


def carriage():
    face = portrait()
    est = estimate(face, random.Random(19), contrast=.93, noise=8)
    s, labels = [], []

    # The carriage: twenty steps; the layer is handed step 10, and its verdict ends the run there.
    RY = 470
    X0, DX = 262, (1504 - 262) / 19
    labels.append(f'<div class="lane" style="left:96px; top:{RY - 30}px"><b>the carriage</b><code>sd15 · 20 steps</code>'
                  f'<span>checks: 10, final</span></div>')
    stop = X0 + 9 * DX
    s.append(f'<line x1="{X0}" y1="{RY}" x2="{stop}" y2="{RY}" stroke="{LINE}" stroke-opacity=".55" stroke-width="2"/>'
             f'<line x1="{stop + 34}" y1="{RY}" x2="1504" y2="{RY}" stroke="#4a4944" stroke-width="2" stroke-dasharray="3 6"/>')
    for i in range(20):
        x = X0 + i * DX
        if i == 9:
            s.append(f'<circle cx="{x}" cy="{RY}" r="9" fill="{GOLD}" fill-opacity=".25" stroke="{GOLD}" stroke-width="2"/>')
        elif i == 19:
            s.append(f'<circle cx="{x}" cy="{RY}" r="8" fill="none" stroke="#5d5b56" stroke-width="1.6" stroke-dasharray="3 3"/>')
        elif i < 9:
            s.append(f'<circle cx="{x}" cy="{RY}" r="5" fill="{LINE}" fill-opacity=".7"/>')
        else:
            s.append(f'<circle cx="{x}" cy="{RY}" r="4" fill="none" stroke="#4a4944" stroke-width="1.4"/>')
    for i in (0, 9, 19):
        colour = GOLD if i == 9 else "#8b8a84"
        left = X0 + i * DX - (66 if i == 19 else 40)
        labels.append(f'<div class="wire" style="left:{left}px; width:80px; text-align:{"right" if i == 19 else "center"}; top:{RY - 34}px; color:{colour}">step {i + 1}</div>')
    s.append(f'<line x1="{stop + 22}" y1="{RY - 14}" x2="{stop + 22}" y2="{RY + 14}" stroke="{ORANGE}" stroke-width="3" stroke-linecap="round"/>')
    labels.append(f'<div class="wire" style="left:{stop + 70}px; top:{RY + 14}px; color:#77756f">steps 11–20 never run: the face is never finished</div>')
    # Down into the layer with the frame; back up with the verdict.
    LT = 560
    s.append(f'<line x1="{stop - 14}" y1="{RY + 12}" x2="{stop - 14}" y2="{LT - 6}" stroke="{GOLD}" stroke-width="2"/>' + arrowhead(stop - 14, LT - 4, "down", GOLD))
    s.append(f'<line x1="{stop + 22}" y1="{LT - 4}" x2="{stop + 22}" y2="{RY + 22}" stroke="{ORANGE}" stroke-width="2"/>' + arrowhead(stop + 22, RY + 20, "up", ORANGE))
    labels.append(f'<div class="wire" style="left:{stop - 156}px; top:{RY + 40}px; color:{GOLD}">onStep: x̂0, decoded</div>')
    labels.append(f'<div class="wire" style="left:{stop + 34}px; top:{RY + 40}px; color:{ORANGE}">.halt, with the verdict</div>')

    # The layer, at step 10.
    s.append(f'<rect x="96" y="{LT}" width="1408" height="250" rx="12" fill="{GOLD}" fill-opacity=".025" stroke="rgba(199,166,89,.5)" stroke-dasharray="7 6"/>')
    labels.append(f'<div class="machine" style="position:absolute; left:116px; top:{LT + 14}px; color:#a8925a">THE VEILLAYER · AT STEP 10</div>')
    Y, SZ = LT + 56, 128
    mid = Y + SZ / 2
    s.append(mosaic(116, Y, est, 8) + frame(116, Y, SZ))
    for k in range(1, 4):
        s.append(f'<line x1="{116 + k * 32}" y1="{Y}" x2="{116 + k * 32}" y2="{Y + SZ}" stroke="rgba(255,255,255,.35)" stroke-width="1"/>'
                 f'<line x1="116" y1="{Y + k * 32}" x2="{116 + SZ}" y2="{Y + k * 32}" stroke="rgba(255,255,255,.35)" stroke-width="1"/>')
    labels.append(f'<div class="words" style="left:284px; top:{Y}px; width:170px; height:{SZ}px; font-size:13px; padding:12px 12px">'
                  + "<br>".join(" ".join(words(random.Random(90 + i), 5)) for i in range(4)) + " …</div>")
    s.append(barcode(492, Y + 20, 84, SZ - 40, [max(-1, min(1, random.Random(i).gauss(0, .55))) for i in range(22)], GOLD))
    prune = ('<div class="pick"><span><b>identity A</b></span><code>0.81</code><i style="color:' + GREEN + '">✓</i></div>'
             '<div class="pick"><span><b>identity B</b></span><code>0.22</code><i style="color:' + GREEN + '">✓</i></div>'
             '<div class="pick dim"><span>identity C</span><code>0.09</code><i style="color:' + ORANGE + '">✕</i></div>'
             '<div class="pick dim"><span>… the rest</span><code>&lt; 0.15</code><i></i></div>')
    labels.append(f'<div class="picks" style="left:614px; top:{Y}px; width:232px; height:{SZ}px">{prune}</div>')
    s.append(heat(884, Y, likeness_heat(face, random.Random(5)), 8))
    sheet = ('<div class="pick"><span><b>identity A</b>, share</span><code>0.71</code></div>'
             '<div class="pick"><span>its coverage</span><code>0.52</code></div>'
             '<div class="pick"><span>share × coverage</span><code style="color:' + ORANGE + '">0.37 ≥ 0.35</code></div>'
             '<div class="pick"><span>attributed tiles</span><code>61 ≥ 8</code></div>')
    labels.append(f'<div class="picks" style="left:1050px; top:{Y}px; width:270px; height:{SZ}px">{sheet}</div>')
    v = chip(1358, Y + 24, 132, 80, "<b>blocked</b><span>at step 10</span><span>identity A</span>", ORANGE, .14)
    s.append(v[0])
    labels.append(v[1])
    for x0, x1 in ((252, 276), (462, 484), (584, 606), (854, 876), (1020, 1042), (1328, 1350)):
        s.append(reply(x0, x1, mid, DIAL, 1.6))
    labels += [lab(180, Y + SZ + 12, 150, "the step’s x̂0", "cut into 32×32 tiles"),
               lab(369, Y + SZ + 12, 170, "the same words", "rgb-veil8 · same key"),
               lab(534, Y + SZ + 12, 120, "vectors", "in Veil’s process"),
               lab(730, Y + SZ + 12, 232, "who to search", "the prompt’s names · once a run"),
               lab(948, Y + SZ + 12, 170, "against their photos", "τ 0.945 · a neighbour agrees"),
               lab(1185, Y + SZ + 12, 270, "the royalty sheet", "each identity’s part"),
               lab(1424, Y + SZ + 12, 132, "the gate", "BlockGate")]
    labels.append(f'<div class="wire" style="left:614px; top:{Y - 22}px; color:#a7a49b">“identity A, at a press event”</div>')

    labels.append(f'<div class="note" style="left:96px; top:{LT + 272}px; width:680px; font-size:15px"><b>What it catches:</b> a generation rebuilding the photos filed under a person’s identity, '
                  'tile by tile at the same offsets, halted before the picture is finished. The prompt naming them only decides <b>who is searched first</b>; the pixels decide the verdict.</div>')
    labels.append(f'<div class="note" style="left:824px; top:{LT + 272}px; width:680px; font-size:15px"><b>What it is not:</b> a face recogniser. It compares with the pictures the person filed, '
                  'so a pose or a light they never filed can pass: the protection is <b>as wide as what was filed</b>.</div>')

    body = f"""<style>
.lane {{ position: absolute; width: 150px; display: flex; flex-direction: column; }}
.lane b {{ font-weight: 400; font-size: 21px; color: #ecebe5; }}
.lane code {{ font-family: {MONO}; font-style: normal; font-size: 12px; color: #a7a49b; margin-top: 4px; }}
.lane span {{ font-size: 15px; line-height: 1.3; margin-top: 5px; }}
.words {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); border-radius: 9px; padding: 13px 14px;
         font-family: {MONO}; font-style: normal; font-size: 13.5px; line-height: 1.62; letter-spacing: .02em; color: #dcdad3; }}
.picks {{ position: absolute; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); border-radius: 9px; padding: 8px 12px;
         display: flex; flex-direction: column; justify-content: space-around; }}
.pick {{ display: grid; grid-template-columns: 1fr auto 16px; column-gap: 8px; align-items: baseline; font-size: 15px; color: #a29f97; }}
.picks .pick:not(:has(i)) {{ grid-template-columns: 1fr auto; }}
.pick b {{ font-weight: 400; color: #ecebe5; }}
.pick code {{ font-family: {MONO}; font-style: normal; font-size: 12.5px; color: #c3c0b7; }}
.pick i {{ font-style: normal; font-size: 14px; text-align: right; }}
.pick.dim {{ opacity: .6; }}
.chipt {{ position: absolute; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 0 8px; }}
.chipt b {{ font-weight: 400; font-size: 19px; color: #ecebe5; line-height: 1.2; }}
.chipt span {{ font-family: {MONO}; font-style: normal; font-size: 11px; color: #a7a49b; margin-top: 3px; }}
</style>
{card(70, 374, 1460, 550, head(step(1) + "The VeilLayer, riding the carriage", GOLD, "VEILSESSION · VEILLAYER"))}
<svg width="{W}" height="1100">{"".join(s)}</svg>
{"".join(labels)}"""
    return plate("carriage.png", 1006, "RAO STUDIOS · VEIL · LIKENESS, MID-FLIGHT",
                 "Checked in the carriage", "between steps, the VeilLayer asks whether the picture is becoming a protected person’s photos",
                 body, "the face, words, scores and heat are illustrative; the steps, τ and the gate are the code’s")



# MARK: The services (who dispatches to whom)

# The pipeline's Granite services in Sources/VeilKit/Services and the root that boots them (Sources/VeilRuntime):
# each box's reducers are its @Events, each arrow a dispatch in a reducer's effect (CarriageOps.check sends Decode to the
# Darkroom and Check to the VeilLayer; VeilLayerOps.attribute calls Veil8, Embedder and Thread; IngestOps.run the same
# three and Sewn's extractor). The companion site's Explorer draws the same chart (docs/site/data/architecture.json).

SERVICES_CSS = f"""<style>
.svc {{ position: absolute; box-sizing: border-box; padding: 12px 16px 0 22px; display: flex; flex-direction: column; }}
.svc b {{ font-weight: 400; font-size: 22px; color: #ecebe5; line-height: 1.1; }}
.svc code {{ font-family: {MONO}; font-style: normal; font-size: 12.5px; color: #dcdad3; margin-top: 6px; white-space: nowrap; }}
.svc span {{ font-size: 15px; line-height: 1.3; color: #a29f97; margin-top: 5px; white-space: nowrap; }}
.svc small {{ font-family: {MONO}; font-style: normal; font-size: 11.5px; color: #8b8a84; margin-top: 6px; white-space: nowrap; }}
.ext {{ position: absolute; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
.ext b {{ font-weight: 400; font-size: 18px; color: #ecebe5; }}
.ext span {{ font-family: {MONO}; font-style: normal; font-size: 11px; color: #8b8a84; margin-top: 4px; }}
.lanelab {{ position: absolute; font-size: 11.5px; letter-spacing: .22em; white-space: nowrap; }}
.wire.r {{ text-align: right; }}
.svcw {{ background: rgba(26,26,23,.94); padding: 1px 5px; border-radius: 4px; }}
</style>"""


def services():
    s, labels = [], []

    def lane(x, y, w, h, colour, name, bottom=False):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{colour}" fill-opacity=".045" stroke="{colour}" stroke-opacity=".28"/>')
        top = y + h - 30 if bottom else y + 14
        labels.append(f'<div class="lanelab" style="left:{x + 18}px; top:{top}px; color:{colour}">{name}</div>')

    def service(x, y, w, h, colour, name, reducers, what, path, gold=False):
        fill, stroke = (GOLD, .14, ) if gold else ("#ffffff", .03), GOLD if gold else "rgba(255,255,255,.16)"
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="11" fill="{fill[0]}" fill-opacity="{fill[1]}" stroke="{stroke}" stroke-width="{1.4 if gold else 1}"/>'
                 f'<rect x="{x}" y="{y + 10}" width="5" height="{h - 20}" rx="2.5" fill="{colour}"/>')
        rows = "".join(f"<code>{r}</code>" for r in reducers)
        labels.append(f'<div class="svc" style="left:{x}px; top:{y}px; width:{w}px; height:{h}px"><b{" style=\"color:" + GOLD + "\"" if gold else ""}>{name}</b>'
                      f'{rows}<span>{what}</span><small>{path}</small></div>')

    def ext(x, y, w, h, name, what, solid=False):
        dash = "" if solid else ' stroke-dasharray="6 5"'
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#ffffff" fill-opacity="{.035 if solid else 0}" stroke="rgba(255,255,255,.3)"{dash}/>')
        labels.append(f'<div class="ext" style="left:{x}px; top:{y}px; width:{w}px; height:{h}px"><b>{name}</b><span>{what}</span></div>')

    def curve(d, colour, both=False, end=None):
        """A dispatch along a path; `end` is (x, y, direction) for the head."""
        s.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="1.8" stroke-linecap="round"/>')
        if end:
            s.append(arrowhead(*end, colour))

    def wire(x, y, text, colour="#a7a49b", right=False):
        style = f"right:{W - x}px" if right else f"left:{x}px"
        labels.append(f'<div class="wire svcw{" r" if right else ""}" style="{style}; top:{y}px; color:{colour}">{text}</div>')

    # The front ends and the root.
    ext(650, 452, 300, 54, "veil · VeilApp", "the command line, and the app", solid=True)
    s.append(vertical(800, 506, 546, DIAL, dashed=False))
    wire(810, 516, "boot()")
    ext(540, 548, 520, 58, "VeilRoot", "VeilRuntime · boots the services, holds a relay to each", solid=True)
    ext(1114, 548, 352, 58, "VeilSD · VeilFlux · ToyExecutor", "the models, behind the executor protocols")

    # The lanes.
    lane(110, 660, 340, 540, ORANGE, "INGESTING")
    lane(560, 660, 400, 540, GREEN, "SHARED BY BOTH")
    lane(1090, 650, 400, 610, BLUE, "GENERATION HALTING", bottom=True)

    # Ingesting.
    service(134, 704, 292, 112, ORANGE, "IngestService", ["Ingest"], "load, prepare, encode, embed, file", "Services/Ingest")
    ext(134, 862, 210, 60, "Sewn, on device", "a caption and its entities")
    s.append(vertical(196, 816, 860, ORANGE, dashed=False))
    wire(206, 830, "ontology", ORANGE)
    labels.append(f'<div class="note" style="left:134px; top:966px; width:292px; font-size:15px; line-height:1.4">Each box is a <b>GraniteService</b>. Its state '
                  f'changes only through its <b>Set</b> reducer, on the main queue; its other reducers mark their start, do the work in an effect, '
                  f'and answer the caller on a ticket. An arrow is one service dispatching to another&rsquo;s reducer.</div>')

    # Shared by both.
    service(584, 704, 352, 112, GREEN, "Veil8Service", ["Encode · Key"], "rgb-veil8 under Veil’s key, in ../Veil8", "Services/Veil8")
    service(584, 842, 352, 112, GREEN, "EmbedderService", ["Embed"], "voyage-4-nano, in Veil’s process", "Services/Embedder")
    service(584, 980, 352, 128, GREEN, "ThreadService", ["Connect · Library · File · Read", "Search · Prune · Probe"], "over VeilThread’s LiveThreadBackend", "Services/Thread")
    s.append(vertical(760, 1110, 1226, DIAL, dashed=True, both=True))
    wire(772, 1160, "gRPC · Index, Documents")
    ext(584, 1228, 352, 60, "Thread, in AII", "the index every Rao app shares · ~/.rao/aii")

    # Generation halting.
    service(1114, 690, 352, 108, BLUE, "HarnessService", ["Load · Release"], "keeps the executor resident", "Services/Harness")
    service(1114, 828, 352, 108, BLUE, "CarriageService", ["Run · Check · Cancel"], "the denoising loop, a check a planned step", "Services/Carriage")
    service(1114, 966, 352, 108, BLUE, "DarkroomService", ["Decode · Export"], "a latent handle into a frame, a PNG", "Services/Darkroom")
    service(1114, 1104, 352, 108, GOLD, "VeilLayerService", ["Configure · Check"], "encode, embed, prune, search, gate", "Services/VeilLayer", gold=True)
    s.append(vertical(1290, 606, 688, BLUE, dashed=False))
    wire(1300, 640, "load · prepare", BLUE)
    for y0, text in ((798, "the resident executor"), (936, "① decode(handle)"), (1074, "② check(frame)")):
        s.append(vertical(1290, y0, y0 + 28, BLUE, dashed=False))
        wire(1300, y0 + 6, text, BLUE)
    curve("M1466,1158 C1514,1158 1514,882 1468,882", GOLD, end=(1468, 882, "left"))
    labels.append(f'<div class="wire svcw" style="left:1500px; top:930px; color:{GOLD}; transform:rotate(90deg); transform-origin:left top">③ halt, or the next step</div>')

    # The root's two calls.
    curve("M640,606 C640,652 280,650 280,702", ORANGE, end=(280, 702, "down"))
    wire(392, 626, "ingest(job)", ORANGE)
    curve("M1060,590 C1092,590 1082,882 1112,882", BLUE, end=(1112, 882, "right"))
    wire(1076, 636, "run(request)", BLUE, right=True)

    # Ingest into the shared services.
    curve("M426,746 L582,746", ORANGE, end=(582, 746, "right"))
    curve("M426,780 C506,780 504,898 582,898", ORANGE, end=(582, 898, "right"))
    curve("M392,816 C392,980 470,1044 582,1044", ORANGE, end=(582, 1044, "right"))
    wire(574, 724, "encode", ORANGE, right=True)
    wire(574, 906, "embed", ORANGE, right=True)
    wire(574, 1052, "probe · file · read", ORANGE, right=True)

    # The VeilLayer into the shared services.
    curve("M1114,1134 C1030,1134 1024,746 938,746", GOLD, end=(938, 746, "left"))
    curve("M1114,1158 C1040,1158 1030,898 938,898", GOLD, end=(938, 898, "left"))
    curve("M1114,1182 C1050,1182 1034,1044 938,1044", GOLD, end=(938, 1044, "left"))
    wire(946, 724, "encode", GOLD)
    wire(946, 876, "embed · embedPrompt", GOLD)
    wire(946, 1022, "probe · prune · search", GOLD)

    body = f"""{SERVICES_CSS}
{card(70, 374, 1460, 950, head(step(1) + "Who dispatches to whom", GOLD, "SOURCES/VEILKIT/SERVICES"))}
<svg width="{W}" height="1500">{"".join(s)}</svg>
{"".join(labels)}"""
    return plate("services.png", 1420, "RAO STUDIOS · VEIL · THE SERVICES",
                 "Eight services, two roads", "a protected picture is filed once; every generation is checked against it between denoising steps",
                 body, "every service, reducer and dispatch is the code’s, in Sources/VeilKit/Services and Sources/VeilRuntime")


ALL = ["executor", "carriage", "services", "veil8_ingest", "veil8_reverse", "veil8_step", "veil8_verdict", "garde_sign", "garde_wild"]


def main():
    targets = sys.argv[2:] or ALL
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for target in targets:
            name, height, page = globals()[target]()
            with tempfile.NamedTemporaryFile("w", suffix=".html", dir=HERE, delete=False, encoding="utf-8") as f:
                f.write(page)
                source = f.name
            try:
                tab = browser.new_page(device_scale_factor=2, viewport={"width": W, "height": height})
                tab.goto("file://" + source)
                tab.wait_for_selector("body[data-height]", state="attached")
                tab.set_viewport_size({"width": W, "height": round(float(tab.evaluate("document.body.dataset.height")))})
                tab.wait_for_timeout(100)
                path = os.path.join(OUT, name)
                tab.screenshot(path=path)
                tab.close()
            finally:
                os.unlink(source)
            with Image.open(path) as im:
                print(f"{name}: {im.size[0]}×{im.size[1]}, {os.path.getsize(path) // 1024} KB")
        browser.close()


if __name__ == "__main__":
    main()
