"""Generate the Fairy Tapes logo files (cassette with a sparkle for a reel) into fairy-tapes/.

Everything is drawn as paths: the wordmark is Liberation Sans Bold (SIL Open Font License 1.1) converted to outlines, so
no font is needed to show the files. PNG and ICO are rendered with rsvg-convert and packed with Pillow.

  python3 fairy-tapes/tools/gen_logo.py            # writes into fairy-tapes/
  python3 -m pytest fairy-tapes/tools/test_gen_logo.py
"""
import math
import os
import subprocess
import sys
import tempfile

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

SANS = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
BG, GREY, AMBER = "#161617", "#c9c9c2", "#f0b429"   # panel, silkscreen, lit button face (Fairy Tapes docs/DESIGN_SYSTEM.md)
AMBER_LIGHT = "#d99a00"                             # deeper amber, readable on light backgrounds
BLACK, WHITE = "#000000", "#ffffff"

FILES = [
    "fairy-tapes-logo-dark.svg", "fairy-tapes-logo-light.svg",
    "fairy-tapes-logo-mono-black.svg", "fairy-tapes-logo-mono-white.svg",
    "fairy-tapes-mark-dark.svg", "fairy-tapes-mark-light.svg",
    "fairy-tapes-mark-mono-black.svg", "fairy-tapes-mark-mono-white.svg",
    "fairy-tapes-avatar.svg", "fairy-tapes-avatar.png",
    "favicon.svg", "favicon.ico",
]

# colour schemes: (lines and wordmark, sparkle)
SCHEMES = {"dark": (GREY, AMBER), "light": (BG, AMBER_LIGHT), "mono-black": (BLACK, BLACK), "mono-white": (WHITE, WHITE)}

MARK_W, MARK_H = 300, 190   # cassette, in its own units


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def P(r, a, cx, cy):
    return f"{f(cx + r * math.cos(a))} {f(cy + r * math.sin(a))}"


def svg(w, h, body, bg=None):
    rect = f'<rect width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}">'
            f"{rect}{body}</svg>\n")


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


def sparkle(cx, cy, r, color, k=0.22):
    """Four-point star with concave sides."""
    pts = [P(r if i % 2 == 0 else r * k, -math.pi / 2 + i * math.pi / 4, cx, cy) for i in range(8)]
    d = "M" + pts[0] + "".join("Q" + pts[i + 1] + " " + pts[(i + 2) % 8] for i in range(0, 8, 2))
    return f'<path d="{d}Z" fill="{color}"/>'


def hub(cx, cy, r, color, sw):
    teeth = "".join(f'<path d="M{P(r * 0.42, a, cx, cy)}L{P(r * 0.78, a, cx, cy)}"/>'
                    for a in [i * math.pi / 3 for i in range(6)])
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" stroke-width="{f(sw)}"/>'
            f'<g stroke-width="{f(sw * 0.8)}" stroke-linecap="round">{teeth}</g>')


def cassette(x, y, s, line, accent):
    """Cassette MARK_W x MARK_H units, top-left at (x, y), scale s."""
    sw = 11
    return (f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})" fill="none" stroke="{line}" stroke-linejoin="round">'
            f'<rect x="{f(sw / 2)}" y="{f(sw / 2)}" width="{MARK_W - sw}" height="{MARK_H - sw}" rx="18" stroke-width="{sw}"/>'
            f'<rect x="44" y="40" width="212" height="84" rx="42" stroke-width="{f(sw * 0.8)}"/>'   # label window
            f'<path d="M62 184L80 146H220L238 184" stroke-width="{f(sw * 0.8)}"/>'               # head opening
            f"{hub(98, 82, 24, line, sw * 0.8)}"
            f"{sparkle(202, 82, 34, accent)}</g>")


def logo(line, accent, pad=24):
    """Horizontal lockup: cassette, then the wordmark as on the panels (bold, spaced)."""
    s, size, gap = 0.62, 54, 40
    mw, mh = MARK_W * s, MARK_H * s
    base = pad + mh / 2 + cap_height(size) / 2
    d, ww = sans_text("FAIRY TAPES", pad + mw + gap, base, size, size * 0.16)
    body = cassette(pad, pad, s, line, accent) + f'<path d="{d}" fill="{line}"/>'
    return svg(pad * 2 + mw + gap + ww, pad * 2 + mh, body)


def mark(line, accent, pad=12):
    return svg(MARK_W + pad * 2, MARK_H + pad * 2, cassette(pad, pad, 1, line, accent))


def avatar():
    s = 1.3
    return svg(512, 512, cassette(256 - MARK_W * s / 2, 256 - MARK_H * s / 2, s, GREY, AMBER), BG)


def favicon():
    """Simplified cassette for 16-48 px: thicker lines, filled hub, no teeth."""
    return svg(32, 32,
               f'<rect width="32" height="32" rx="6" fill="{BG}"/>'
               f'<g fill="none" stroke="{GREY}" stroke-linejoin="round">'
               f'<rect x="3.5" y="7" width="25" height="18" rx="2.5" stroke-width="2"/>'
               f'<rect x="7" y="10.3" width="18" height="7.4" rx="3.7" stroke-width="1.6"/>'
               f'<path d="M9.5 25L11 21.6H21L22.5 25" stroke-width="1.6"/></g>'
               f'<circle cx="11.6" cy="14" r="1.7" fill="{GREY}"/>'
               f"{sparkle(20.3, 14, 3.3, AMBER, 0.26)}")


def favicon16():
    """16 px only (inside favicon.ico): body, hub and sparkle on the pixel grid; the window and head do not fit."""
    return svg(16, 16,
               f'<rect width="16" height="16" rx="3" fill="{BG}"/>'
               f'<rect x="1.5" y="3.5" width="13" height="9" rx="1.5" fill="none" stroke="{GREY}"/>'
               f'<circle cx="5.5" cy="8" r="1.5" fill="{GREY}"/>'
               f"{sparkle(10.5, 8, 2.9, AMBER, 0.3)}")


def render_png(svg_path, png_path, size):
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), svg_path, "-o", png_path], check=True)


def build(out):
    os.makedirs(out, exist_ok=True)
    w = lambda name, s: open(os.path.join(out, name), "w").write(s)
    for scheme, (line, accent) in SCHEMES.items():
        w(f"fairy-tapes-logo-{scheme}.svg", logo(line, accent))
        w(f"fairy-tapes-mark-{scheme}.svg", mark(line, accent))
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
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
