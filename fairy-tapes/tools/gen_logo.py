"""Generate the Fairy Tapes logo files (a mixtape: hand-written label on masking tape, a sparkle for a reel) into
fairy-tapes/.

Everything is drawn as paths, so no font is needed to show the files:
  - the label is Rock Salt (Apache License 2.0), read from rocksalt_glyphs.json (see extract_glyphs.py);
  - the wordmark is Liberation Sans Bold (SIL Open Font License 1.1), converted to outlines.
The tape is the one of the Sweetspot Tools logo (sweetspot-tools/tools/gen_logo.py). PNG and ICO are rendered with
rsvg-convert and packed with Pillow.

  python3 fairy-tapes/tools/gen_logo.py            # writes into fairy-tapes/
  python3 -m pytest fairy-tapes/tools/test_gen_logo.py
"""
import json
import math
import os
import random
import subprocess
import sys
import tempfile

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
SANS = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
LABEL_GLYPHS = os.path.join(HERE, "rocksalt_glyphs.json")
LABEL = "Fairy Tapes"

BG, GREY, AMBER = "#161617", "#c9c9c2", "#f0b429"   # panel, silkscreen, lit button face (Fairy Tapes docs/DESIGN_SYSTEM.md)
AMBER_LIGHT = "#d99a00"                             # deeper amber, readable on light backgrounds
TAPE, TAPE_EDGE, TAPE_FIBRE = "#e6dab6", "#b9ab82", "#d2c59e"   # masking tape, as in the Sweetspot Tools logo
INK = "#1d1d1e"                                     # marker on the tape
BLACK, WHITE = "#000000", "#ffffff"

FILES = [
    "fairy-tapes-logo-dark.svg", "fairy-tapes-logo-light.svg",
    "fairy-tapes-logo-mono-black.svg", "fairy-tapes-logo-mono-white.svg",
    "fairy-tapes-mark-dark.svg", "fairy-tapes-mark-light.svg",
    "fairy-tapes-mark-mono-black.svg", "fairy-tapes-mark-mono-white.svg",
    "fairy-tapes-avatar.svg", "fairy-tapes-avatar.png",
    "favicon.svg", "favicon.ico",
]

# colour schemes: lines and wordmark, sparkle, tape (fill, edge or None, fibres or None), ink on the tape
SCHEMES = {
    "dark": dict(line=GREY, amber=AMBER, tape=TAPE, edge=None, fibre=TAPE_FIBRE, ink=INK),
    "light": dict(line=BG, amber=AMBER_LIGHT, tape=TAPE, edge=TAPE_EDGE, fibre=TAPE_FIBRE, ink=BG),
    "mono-black": dict(line=BLACK, amber=BLACK, tape=None, edge=BLACK, fibre=None, ink=BLACK),
    "mono-white": dict(line=WHITE, amber=WHITE, tape=None, edge=WHITE, fibre=None, ink=WHITE),
}

MARK_W, MARK_H = 300, 214   # cassette, in its own units
SW = 11                     # outline of the shell


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def P(r, a, cx, cy):
    return f"{f(cx + r * math.cos(a))} {f(cy + r * math.sin(a))}"


def svg(w, h, body, bg=None):
    rect = f'<rect width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}">'
            f"{rect}{body}</svg>\n")


# ---------- text ----------
def sans_text(text, x, y, size, tracking):
    font = TTFont(SANS)
    gs, cmap, k = font.getGlyphSet(), font.getBestCmap(), size / font["head"].unitsPerEm
    out, pen = [], x
    for ch in text:
        name = cmap[ord(ch)]
        sp = SVGPathPen(gs, ntos=f)
        gs[name].draw(TransformPen(sp, (k, 0, 0, -k, pen, y)))
        out.append(sp.getCommands())
        pen += font["hmtx"][name][0] * k + tracking
    return "".join(out), pen - x - tracking


def cap_height(size):
    font = TTFont(SANS)
    return font["OS/2"].sCapHeight * size / font["head"].unitsPerEm


def load_label_glyphs():
    with open(LABEL_GLYPHS) as fh:
        return json.load(fh)


def label_text(text, x, y, size):
    """Rock Salt text with the baseline at (x, y); returns (path data, width)."""
    font = load_label_glyphs()
    k, pen, d = size / font["unitsPerEm"], x, []
    for ch in text:
        g = font["glyphs"][ch]
        s, i = g["stream"], 0
        pt = lambda a, b: f"{f(pen + a * k)} {f(y - b * k)}"
        while i < len(s):
            op = s[i]
            if op == 0:
                d.append("M" + pt(s[i + 1], s[i + 2])); i += 3
            elif op == 1:
                d.append("L" + pt(s[i + 1], s[i + 2])); i += 3
            elif op == 2:
                d.append("Q" + pt(s[i + 1], s[i + 2]) + " " + pt(s[i + 3], s[i + 4])); i += 5
            else:
                d.append("Z"); i += 1
        pen += g["advance"] * k
    return "".join(d), pen - x


# ---------- tape (same drawing as the Sweetspot Tools logo) ----------
def tape_outline(w, h, seed):
    """Strip of tape w x h (top-left at 0, 0): torn short sides with uneven teeth, long sides not quite straight."""
    rnd = random.Random(seed)
    depth = min(9.0, w * 0.04)

    def torn(x, sign):
        pts, y, i = [], 0.0, 0
        while y < h:
            pts.append((x + sign * depth * (rnd.uniform(0.55, 1.0) if i % 2 else rnd.uniform(0.0, 0.25)), y))
            y += h / 10 * rnd.uniform(0.55, 1.45)
            i += 1
        pts.append((x + sign * depth * rnd.uniform(0.0, 0.25), h))
        return pts

    def side(y, x0, x1):   # a few points along a long side, off the line by a fraction of a unit
        return [(x0 + (x1 - x0) * t, y + rnd.uniform(-1, 1) * h * 0.006) for t in (0.3, 0.55, 0.8)]

    left, right = torn(0, 1), torn(w, -1)
    pts = left + side(h, left[-1][0], right[-1][0]) + list(reversed(right)) + list(reversed(side(0, left[0][0], right[0][0])))
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"


def tape(w, h, c, seed, angle, cx, cy, ink=""):
    """Tape centred on (cx, cy), turned by angle degrees, with ink (paths in tape coordinates) on it."""
    d = tape_outline(w, h, seed)
    if c["tape"]:
        stroke = f' stroke="{c["edge"]}" stroke-width="{f(h * 0.02)}"' if c["edge"] else ""
        body = f'<path d="{d}" fill="{c["tape"]}"{stroke} stroke-linejoin="round"/>'
    else:
        body = f'<path d="{d}" fill="none" stroke="{c["edge"]}" stroke-width="{f(h * 0.035)}" stroke-linejoin="round"/>'
    if c["fibre"]:   # paper fibres along the strip
        rnd = random.Random(seed + 1)
        lines = "".join(f"M{f(w * x0)} {f(h * y)}H{f(w * (x0 + ln))}" for x0, y, ln in
                        [(rnd.uniform(0.06, 0.2), 0.13, rnd.uniform(0.15, 0.25)), (rnd.uniform(0.5, 0.6), 0.88, rnd.uniform(0.2, 0.3)),
                         (rnd.uniform(0.7, 0.8), 0.2, rnd.uniform(0.08, 0.12))])
        body += f'<path d="{lines}" stroke="{c["fibre"]}" stroke-width="{f(max(1.0, h * 0.012))}" stroke-linecap="round"/>'
    return (f'<g transform="translate({f(cx)} {f(cy)}) rotate({f(angle)}) translate({f(-w / 2)} {f(-h / 2)})">'
            f"{body}{ink}</g>")


# ---------- cassette ----------
def sparkle(cx, cy, r, color, k=0.22):
    """Four-point star with concave sides."""
    pts = [P(r if i % 2 == 0 else r * k, -math.pi / 2 + i * math.pi / 4, cx, cy) for i in range(8)]
    d = "M" + pts[0] + "".join("Q" + pts[i + 1] + " " + pts[(i + 2) % 8] for i in range(0, 8, 2))
    return f'<path d="{d}Z" fill="{color}"/>'


def hub(cx, cy, r, color, sw):
    teeth = "".join(f'<path d="M{P(r * 0.42, a, cx, cy)}L{P(r * 0.78, a, cx, cy)}"/>'
                    for a in [i * math.pi / 3 for i in range(6)])
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{color}" stroke-width="{f(sw)}"/>'
            f'<g stroke="{color}" stroke-width="{f(sw * 0.8)}" stroke-linecap="round">{teeth}</g>')


def label(c, tw=246, th=62):
    """Hand-written "Fairy Tapes" on a strip of tape, in tape coordinates."""
    _, w100 = label_text(LABEL, 0, 0, 100)
    size = min(100 * (tw - 30) / w100, 40)
    _, w = label_text(LABEL, 0, 0, size)
    d, _ = label_text(LABEL, (tw - w) / 2, th / 2 + size * 0.36, size)
    return tape(tw, th, c, 5, -3, 150, 54, f'<path d="{d}" fill="{c["ink"]}"/>')


def cassette(x, y, s, c):
    """Mixtape MARK_W x MARK_H units, top-left at (x, y), scale s: label on top, window with a reel and a sparkle."""
    line = c["line"]
    return (f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">'
            f'<g fill="none" stroke="{line}" stroke-linejoin="round">'
            f'<rect x="{f(SW / 2)}" y="{f(SW / 2)}" width="{MARK_W - SW}" height="{MARK_H - SW}" rx="18" stroke-width="{SW}"/>'
            f'<rect x="56" y="100" width="188" height="56" rx="28" stroke-width="{f(SW * 0.8)}"/>'   # window
            f'<path d="M66 208L82 176H218L234 208" stroke-width="{f(SW * 0.8)}"/></g>'               # head opening
            f"{hub(100, 128, 17, line, SW * 0.7)}{sparkle(200, 128, 25, c['amber'])}{label(c)}</g>")


# ---------- files ----------
def logo(c, pad=24):
    """Horizontal lockup: mixtape, then the wordmark as on the panels (bold, spaced)."""
    s, size, gap = 0.62, 54, 40
    mw, mh = MARK_W * s, MARK_H * s
    base = pad + mh / 2 + cap_height(size) / 2
    d, ww = sans_text("FAIRY TAPES", pad + mw + gap, base, size, size * 0.16)
    body = cassette(pad, pad, s, c) + f'<path d="{d}" fill="{c["line"]}"/>'
    return svg(pad * 2 + mw + gap + ww, pad * 2 + mh, body)


def mark(c, pad=12):
    return svg(MARK_W + pad * 2, MARK_H + pad * 2, cassette(pad, pad, 1, c))


def avatar():
    s = 1.4
    return svg(512, 512, cassette(256 - MARK_W * s / 2, 256 - MARK_H * s / 2, s, SCHEMES["dark"]), BG)


def favicon():
    """Simplified mixtape for 32-48 px: blank tape label, filled hub, no teeth."""
    return svg(32, 32,
               f'<rect width="32" height="32" rx="6" fill="{BG}"/>'
               f'<g fill="none" stroke="{GREY}" stroke-linejoin="round">'
               f'<rect x="3.5" y="5" width="25" height="22" rx="2.5" stroke-width="2"/>'
               f'<rect x="8" y="16" width="16" height="6.4" rx="3.2" stroke-width="1.5"/></g>'
               f'<path d="M7 8.6L25.2 7.8L25.6 13L7.3 13.6Z" fill="{TAPE}"/>'
               f'<circle cx="11.6" cy="19.2" r="1.5" fill="{GREY}"/>'
               f"{sparkle(20.3, 19.2, 3, AMBER, 0.26)}")


def favicon16():
    """16 px only (inside favicon.ico): shell, tape label and sparkle on the pixel grid."""
    return svg(16, 16,
               f'<rect width="16" height="16" rx="3" fill="{BG}"/>'
               f'<rect x="1.5" y="2.5" width="13" height="11" rx="1.5" fill="none" stroke="{GREY}"/>'
               f'<rect x="3" y="4" width="10" height="3" fill="{TAPE}"/>'
               f'<circle cx="5.5" cy="10" r="1.2" fill="{GREY}"/>'
               f"{sparkle(10.5, 10, 2.4, AMBER, 0.3)}")


def render_png(svg_path, png_path, size):
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), svg_path, "-o", png_path], check=True)


def build(out):
    os.makedirs(out, exist_ok=True)
    w = lambda name, s: open(os.path.join(out, name), "w").write(s)
    for scheme, c in SCHEMES.items():
        w(f"fairy-tapes-logo-{scheme}.svg", logo(c))
        w(f"fairy-tapes-mark-{scheme}.svg", mark(c))
    w("fairy-tapes-avatar.svg", avatar())
    w("favicon.svg", favicon())
    render_png(os.path.join(out, "fairy-tapes-avatar.svg"), os.path.join(out, "fairy-tapes-avatar.png"), 512)

    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "favicon16.svg"), "w").write(favicon16())
        imgs = []
        for size in (16, 32, 48):   # each size rendered from the vector, not downscaled
            src = os.path.join(tmp, "favicon16.svg") if size == 16 else os.path.join(out, "favicon.svg")
            p = os.path.join(tmp, f"{size}.png")
            render_png(src, p, size)
            imgs.append(Image.open(p).convert("RGBA"))
        imgs[-1].save(os.path.join(out, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
                      append_images=imgs[:-1])


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, ".."))
