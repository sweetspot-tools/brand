"""Generate the Sweetspot Tools logo files (a torn strip of masking tape: "don't touch! it's the sweet spot"; the avatar
is that tape stuck next to a knob on a rack panel) into sweetspot-tools/.

Everything is drawn as paths: the handwriting is Homemade Apple (Apache License 2.0), the wordmark is
Liberation Sans Bold (SIL Open Font License 1.1), all converted to outlines, so no font is needed to show the files.
PNG and ICO are rendered with rsvg-convert and packed with Pillow.

  python3 sweetspot-tools/tools/gen_logo.py --fonts DIR [OUT]     # DIR holds HomemadeApple-Regular.ttf
  SWEETSPOT_FONTS=DIR python3 -m pytest sweetspot-tools/tools/test_gen_logo.py
"""
import argparse
import math
import os
import random
import subprocess
import tempfile

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

SANS = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
HOMEMADE = "HomemadeApple-Regular.ttf"

BG, GREY, AMBER = "#161617", "#c9c9c2", "#f0b429"   # panel, silkscreen, lit button face (same as Fairy Tapes)
AMBER_LIGHT = "#d99a00"                             # deeper amber, readable on light backgrounds
TAPE, TAPE_EDGE, TAPE_FIBRE = "#e6dab6", "#b9ab82", "#d2c59e"   # masking tape of the plug-in panels
INK = "#1d1d1e"                                     # marker on the tape
BLACK, WHITE = "#000000", "#ffffff"

FILES = [
    "sweetspot-tools-logo-dark.svg", "sweetspot-tools-logo-light.svg",
    "sweetspot-tools-logo-mono-black.svg", "sweetspot-tools-logo-mono-white.svg",
    "sweetspot-tools-mark-dark.svg", "sweetspot-tools-mark-light.svg",
    "sweetspot-tools-mark-mono-black.svg", "sweetspot-tools-mark-mono-white.svg",
    "sweetspot-tools-avatar.svg", "sweetspot-tools-avatar.png",
    "favicon.svg", "favicon.ico",
]

# colour schemes: wordmark, amber marker, tape (fill, edge or None, fibres or None), ink on the tape
SCHEMES = {
    "dark": dict(word=GREY, amber=AMBER, tape=TAPE, edge=None, fibre=TAPE_FIBRE, ink=INK),
    "light": dict(word=BG, amber=AMBER_LIGHT, tape=TAPE, edge=TAPE_EDGE, fibre=TAPE_FIBRE, ink=BG),
    "mono-black": dict(word=BLACK, amber=BLACK, tape=None, edge=BLACK, fibre=None, ink=BLACK),
    "mono-white": dict(word=WHITE, amber=WHITE, tape=None, edge=WHITE, fibre=None, ink=WHITE),
}


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def svg(w, h, body, bg=None):
    rect = f'<rect width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}">'
            f"{rect}{body}</svg>\n")


class Font:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.gs, self.cmap = self.tt.getGlyphSet(), self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm

    def text(self, s, x, y, size, tracking=0.0, wobble=None):
        """Outline of s with its baseline starting at (x, y): (path data, advance width, ink bounds).

        wobble=(seed, amount): each letter turned and lifted a little, as handwriting on the panel tape (same seed,
        same letters)."""
        k, pen, out = size / self.upm, x, []
        rnd = random.Random(wobble[0]) if wobble else None
        bp = BoundsPen(self.gs)
        for ch in s:
            name = self.cmap[ord(ch)]
            a = math.radians(rnd.uniform(-1, 1) * 4 * wobble[1]) if rnd else 0.0
            dy = rnd.uniform(-1, 1) * 0.025 * size * wobble[1] if rnd else 0.0
            ca, sa = math.cos(a), math.sin(a)
            m = (k * ca, k * sa, k * sa, -k * ca, pen, y + dy)
            sp = SVGPathPen(self.gs, ntos=f)
            self.gs[name].draw(TransformPen(sp, m))
            self.gs[name].draw(TransformPen(bp, m))
            out.append(sp.getCommands())
            pen += self.tt["hmtx"][name][0] * k + tracking
        return "".join(out), pen - x - tracking, bp.bounds

    def centred(self, s, cx, cy, size, wobble=None):
        """Outline of s with its ink box centred on (cx, cy)."""
        _, _, (x0, y0, x1, y1) = self.text(s, 0, 0, size, wobble=wobble)
        return self.text(s, cx - (x0 + x1) / 2, cy - (y0 + y1) / 2, size, wobble=wobble)[0]

    def cap_height(self, size):
        return self.tt["OS/2"].sCapHeight * size / self.upm


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


def marker_arrow(x0, y0, x1, y1, color, sw, bend=0.9, seed=1):
    """Marker arrow from (x0, y0) bending down onto (x1, y1): the stroke thickens as the pen presses, the head is two
    separate strokes of slightly different length."""
    rnd = random.Random(seed)
    c1 = (x0 + (x1 - x0) * bend, y0 - sw * 0.6)
    c2 = (x1 + sw * 0.3, y0 + (y1 - y0) * 0.35)
    bez = lambda t, i: ((1 - t) ** 3 * x0 if i == 0 else (1 - t) ** 3 * y0) + 3 * (1 - t) ** 2 * t * c1[i] \
        + 3 * (1 - t) * t ** 2 * c2[i] + t ** 3 * (x1 if i == 0 else y1)
    n = 48
    pts = [(bez(t / n, 0), bez(t / n, 1)) for t in range(n + 1)]
    left, right = [], []
    for i, (px, py) in enumerate(pts):
        qx, qy = pts[min(i + 1, n)] if i < n else pts[i]
        rx, ry = pts[max(i - 1, 0)]
        tx, ty = (qx - rx), (qy - ry)
        ln = math.hypot(tx, ty) or 1
        hw = sw * (0.32 + 0.22 * i / n)   # half width: thin start, full near the head
        left.append((px - ty / ln * hw, py + tx / ln * hw))
        right.append((px + ty / ln * hw, py - tx / ln * hw))
    shaft = "M" + "L".join(f"{f(x)} {f(y)}" for x, y in left + list(reversed(right))) + "Z"
    a = math.atan2(y1 - pts[-4][1], x1 - pts[-4][0])
    head = ""
    for spread, ln in ((0.62, 3.3), (-0.55, 2.9)):
        L = sw * ln * rnd.uniform(0.92, 1.08)
        hx, hy = x1 + L * math.cos(a + math.pi - spread), y1 + L * math.sin(a + math.pi - spread)
        head += f"M{f(hx)} {f(hy)}L{f(x1)} {f(y1)}"
    return (f'<path d="{shaft}" fill="{color}"/>'
            f'<circle cx="{f(x0)}" cy="{f(y0)}" r="{f(sw * 0.32)}" fill="{color}"/>'
            f'<path d="{head}" fill="none" stroke="{color}" stroke-width="{f(sw * 1.05)}" stroke-linecap="round"/>')


def dot(cx, cy, r, color, seed=5):
    """Marker dot: a round blob, not a perfect circle."""
    rnd = random.Random(seed)
    n = 9
    pts = [(cx + r * rnd.uniform(0.93, 1.07) * math.cos(2 * math.pi * i / n),
            cy + r * rnd.uniform(0.93, 1.07) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    mid = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    d = f"M{f(mid(pts[-1], pts[0])[0])} {f(mid(pts[-1], pts[0])[1])}"
    for i in range(n):
        m = mid(pts[i], pts[(i + 1) % n])
        d += f"Q{f(pts[i][0])} {f(pts[i][1])} {f(m[0])} {f(m[1])}"
    return f'<path d="{d}Z" fill="{color}"/>'


def note(fonts, c, x, y, tw, th=96):
    """The "don't touch! it's the sweet spot" tape with its top-left corner near (x, y)."""
    hand = fonts["homemade"]
    line1 = hand.centred("don't touch!", tw / 2, th * 0.37, 31, wobble=(3, 1))
    line2 = hand.centred("it's the sweet spot", tw / 2, th * 0.72, 21, wobble=(4, 0.8))
    ink = f'<path d="{line1}" fill="{c["ink"]}"/><path d="{line2}" fill="{c["ink"]}"/>'
    return tape(tw, th, c, 7, 2.5, x + tw / 2, y + th / 2, ink)


def logo(fonts, c, pad=28):
    """Horizontal lockup: the tape, the wordmark, and the amber arrow landing on the dot after it."""
    size = 30
    ww = fonts["sans"].text("SWEETSPOT TOOLS", pad, 0, size, size * 0.16)[1]
    tw, th = ww * 0.8, 96
    cap = fonts["sans"].cap_height(size)
    base = pad + th + 40 + cap
    word = fonts["sans"].text("SWEETSPOT TOOLS", pad, base, size, size * 0.16)[0]
    r = size * 0.25
    dx, dy = pad + ww + size * 0.8, base - cap / 2
    body = (note(fonts, c, pad, pad, tw, th)
            + f'<path d="{word}" fill="{c["word"]}"/>'
            + marker_arrow(pad + tw + 12, pad + th * 0.5, dx, dy - r - 10, c["amber"], 5)
            + dot(dx, dy, r, c["amber"]))
    return svg(dx + r + pad, base + pad, body)


def mark(fonts, c, pad=24):
    """The logo without the wordmark: the tape, and the arrow landing on the dot below its end."""
    tw, th, r = 380, 96, 7.5
    dx, dy = pad + tw + 46, pad + th + 52
    body = (note(fonts, c, pad, pad, tw, th)
            + marker_arrow(pad + tw + 12, pad + th * 0.5, dx, dy - r - 10, c["amber"], 5)
            + dot(dx, dy, r, c["amber"]))
    return svg(dx + r + pad, dy + r + pad, body)


# --- the avatar: a close-up of a rack panel (grain, scratches, screws), an aluminium knob as on The Stripper, the tape
# stuck next to it and the amber arrow pointing at the marker dot drawn on the panel where the knob sounds right

PANEL_LIGHT, PANEL_DARK, SCRATCH = "#1f1f21", "#0e0e0f", "#34343a"
ALU, ALU_HI, ALU_INLAY, SKIRT = "#232427", "#3c3d41", "#d4d1c5", "#0e0e0f"   # knob of stripper_rack.html
SCREW, SCREW_RIM, SCREW_CENTRE, SCREW_SLOT = "#2b2b2e", "#4c4c50", "#202022", "#050505"


def grain(w, h, n, seed):
    """Fine grain of the panel finish: tiny lighter and darker squares."""
    rnd = random.Random(seed)
    light, dark = [], []
    for _ in range(n):
        x, y, q = rnd.uniform(0, w), rnd.uniform(0, h), rnd.choice((1, 1, 1.5, 2))
        (light if rnd.random() < 0.5 else dark).append(f"M{f(x)} {f(y)}h{f(q)}v{f(q)}h{f(-q)}z")
    return f'<path d="{"".join(light)}" fill="{PANEL_LIGHT}"/><path d="{"".join(dark)}" fill="{PANEL_DARK}"/>'


def scratches(w, h, n, seed):
    """Light scratches on the black panel, thin and slightly curved."""
    rnd = random.Random(seed)
    d = []
    for _ in range(n):
        x, y, ln, a = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(14, 60), rnd.uniform(0, math.pi)
        ex, ey = x + ln * math.cos(a), y + ln * math.sin(a)
        mx, my = (x + ex) / 2 + rnd.uniform(-4, 4), (y + ey) / 2 + rnd.uniform(-4, 4)
        d.append(f"M{f(x)} {f(y)}Q{f(mx)} {f(my)} {f(ex)} {f(ey)}")
    return f'<path d="{"".join(d)}" fill="none" stroke="{SCRATCH}" stroke-width="1.1" stroke-linecap="round"/>'


def screw(cx, cy, r, angle, cross):
    """Panel screw (stripper_rack.html): solid head, darker centre, slot or cross recess, turned by angle."""
    k = r / 6.6   # the panel screw has a 6.6 radius
    arm = lambda w, h: (f'<rect x="{f(cx - w / 2)}" y="{f(cy - h / 2)}" width="{f(w)}" height="{f(h)}" rx="{f(0.6 * k)}" '
                        f'fill="{SCREW_SLOT}"/>')
    recess = arm(9.6 * k, 2 * k) + arm(2 * k, 9.6 * k) if cross else arm(10 * k, 2.2 * k)
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{SCREW}" stroke="{SCREW_RIM}" stroke-width="{f(k)}"/>'
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(4.6 * k)}" fill="{SCREW_CENTRE}" opacity="0.7"/>'
            f'<g transform="rotate({f(angle)} {f(cx)} {f(cy)})">{recess}</g>')


def polar(cx, cy, r, deg):
    return cx + r * math.cos(math.radians(deg)), cy - r * math.sin(math.radians(deg))


def knob(cx, cy, R, value, scale_color, fonts=None):
    """Aluminium knob with its printed scale (11 dots, 0 and 10 at the ends); value 0..1 over 270 degrees."""
    z = R / 56
    out = ""
    for i in range(11):   # printed scale
        x, y = polar(cx, cy, R + 24 * z, 225 - 270 * i / 10)
        out += dot(x, y, (3.4 if i % 5 == 0 else 2.2) * z, scale_color, seed=i)
    if fonts:
        for label, deg, anchor in (("0", 225, "end"), ("10", -45, "start")):
            x, y = polar(cx, cy, R + 24 * z, deg)
            d, w, _ = fonts["sans"].text(label, 0, 0, 15 * z)
            x = x - w - 12 * z if anchor == "end" else x + 12 * z
            out += f'<path d="{fonts["sans"].text(label, x, y + 22 * z, 15 * z)[0]}" fill="{scale_color}"/>'
    out += (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R * 1.1)}" fill="{SKIRT}"/>'
            f'<circle cx="{f(cx - 0.6 * z)}" cy="{f(cy - 0.7 * z)}" r="{f(R * 1.1)}" fill="none" stroke="{ALU_HI}" '
            f'stroke-width="{f(1.6 * z)}" opacity="0.55"/>'
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="{ALU}"/>')
    n = 30
    for q in range(1, n + 1):   # turning marks
        out += (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R * q / n * 0.97)}" fill="none" '
                f'stroke="{"#ffffff" if q % 2 else "#000000"}" stroke-width="{f(0.8 * z)}" opacity="{0.06 if q % 2 else 0.12}"/>')
    out += (f'<circle cx="{f(cx - 0.5 * z)}" cy="{f(cy - 0.6 * z)}" r="{f(R * 0.93)}" fill="none" stroke="#8f9196" '
            f'stroke-width="{f(2.2 * z)}" opacity="0.45"/>'
            f'<circle cx="{f(cx - 0.5 * z)}" cy="{f(cy - 0.6 * z)}" r="{f(R - 0.5 * z)}" fill="none" stroke="#ffffff" '
            f'stroke-width="{f(1.2 * z)}" opacity="0.1"/>')
    deg = 225 - 270 * value
    x0, y0 = polar(cx, cy, R * 0.3, deg)
    x1, y1 = polar(cx, cy, R * 0.86, deg)
    out += (f'<path d="M{f(x0)} {f(y0)}L{f(x1)} {f(y1)}" stroke="#000000" stroke-width="{f(4.6 * z)}" '
            f'stroke-linecap="round" opacity="0.28"/>'
            f'<path d="M{f(x0)} {f(y0)}L{f(x1)} {f(y1)}" stroke="{ALU_INLAY}" stroke-width="{f(3.2 * z)}" stroke-linecap="round"/>')
    return out


SWEET = 0.72   # where the knob sounds right (0..1)


def avatar(fonts):
    c = SCHEMES["dark"]
    cx, cy, R = 262, 318, 86
    mx, my = polar(cx, cy, R + 58, 225 - 270 * SWEET)   # the marker dot, just outside the scale
    hand = fonts["homemade"]
    tw, th = 286, 84
    words = hand.centred("don't touch!", tw / 2, th / 2, 40, wobble=(3, 1))
    ink = f'<path d="{words}" fill="{INK}"/>'
    body = (grain(512, 512, 2600, 21) + scratches(512, 512, 9, 22)
            + screw(58, 58, 15, 28, True) + screw(454, 454, 15, 117, False)
            + knob(cx, cy, R, SWEET, GREY, fonts)
            + tape(tw, th, c, 9, -6, 196, 116, ink)
            + marker_arrow(352, 104, mx, my - 30, AMBER, 9, bend=0.75, seed=3)
            + dot(mx, my, 13, AMBER))
    return svg(512, 512, body, BG)


FAV_KNOB, FAV_RIM = "#45464b", "#5c5d62"   # the knob a little lighter than on the panel, or it vanishes at 16-48 px


def favicon(fonts):
    """32 px: the same scene reduced to a strip of tape, the knob with its pointer and the marker dot."""
    cx, cy, R = 14.5, 19.5, 8
    deg = 225 - 270 * SWEET
    x0, y0 = polar(cx, cy, R * 0.2, deg)
    x1, y1 = polar(cx, cy, R * 0.85, deg)
    mx, my = polar(cx, cy, R + 6, deg)
    return svg(32, 32, f'<rect width="32" height="32" rx="6" fill="{BG}"/>'
               f'<rect x="3" y="3.5" width="14" height="5" fill="{TAPE}" transform="rotate(-6 10 6)"/>'
               f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R + 1.2)}" fill="{SKIRT}"/>'
               f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="{FAV_KNOB}" stroke="{FAV_RIM}" stroke-width="0.8"/>'
               f'<path d="M{f(x0)} {f(y0)}L{f(x1)} {f(y1)}" stroke="{ALU_INLAY}" stroke-width="2" stroke-linecap="round"/>'
               + dot(mx, my, 2.7, AMBER))


def favicon16():
    """16 px only (inside favicon.ico): tape as a bar, knob, pointer and marker dot on the pixel grid."""
    return svg(16, 16, f'<rect width="16" height="16" rx="3" fill="{BG}"/>'
               f'<rect x="2" y="2" width="7" height="2" fill="{TAPE}"/>'
               f'<circle cx="7" cy="10" r="4.5" fill="{FAV_KNOB}"/>'
               f'<path d="M7 10L9.6 7.4" stroke="{ALU_INLAY}" stroke-width="1.4" stroke-linecap="round"/>'
               + dot(13.2, 4.8, 1.9, AMBER))


def render_png(svg_path, png_path, size):
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), svg_path, "-o", png_path], check=True)


def load_fonts(fonts_dir):
    return {"sans": Font(SANS), "homemade": Font(os.path.join(fonts_dir, HOMEMADE))}


def build(out, fonts_dir):
    fonts = load_fonts(fonts_dir)
    os.makedirs(out, exist_ok=True)
    w = lambda name, s: open(os.path.join(out, name), "w").write(s)
    for scheme, c in SCHEMES.items():
        w(f"sweetspot-tools-logo-{scheme}.svg", logo(fonts, c))
        w(f"sweetspot-tools-mark-{scheme}.svg", mark(fonts, c))
    w("sweetspot-tools-avatar.svg", avatar(fonts))
    w("favicon.svg", favicon(fonts))
    render_png(os.path.join(out, "sweetspot-tools-avatar.svg"), os.path.join(out, "sweetspot-tools-avatar.png"), 512)

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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--fonts", default=os.environ.get("SWEETSPOT_FONTS"), required="SWEETSPOT_FONTS" not in os.environ,
                    help="folder with HomemadeApple-Regular.ttf")
    a = ap.parse_args()
    build(a.out, a.fonts)
