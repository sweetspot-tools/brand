"""Copy the Rock Salt outlines of the label text from the Fairy Tapes repository into rocksalt_glyphs.json.

The source is shared/ui/include/fairy_ui/tape_glyphs.h of sweetspot-tools/fairy-tapes (generated there from
RockSalt-Regular.ttf, Apache License 2.0, Font Diner / Sideshow; see LICENSE-RockSalt-Apache-2.0.txt next to this file).
Only the characters of LABEL are kept.

  python3 fairy-tapes/tools/extract_glyphs.py /srv/http/fairy-tapes/shared/ui/include/fairy_ui/tape_glyphs.h
"""
import json
import os
import re
import sys

LABEL = "Fairy Tapes"


def extract(header):
    src = open(header).read()
    table = re.search(r"kRockSaltGlyphs\[\] = \{(.*?)\};", src, re.S).group(1)
    glyphs = {int(c): (int(a), int(o), int(n)) for c, a, o, n in re.findall(r"\{(\d+), (-?\d+), (\d+), (\d+)\}", table)}
    stream = [int(v) for v in re.findall(r"-?\d+", re.search(r"kRockSaltStream\[\] = \{(.*?)\};", src, re.S).group(1))]
    out = {}
    for ch in sorted(set(LABEL)):
        adv, off, n = glyphs[ord(ch)]
        out[ch] = {"advance": adv, "stream": stream[off:off + n]}
    return {"font": "Rock Salt", "license": "Apache License 2.0", "unitsPerEm": 1000,
            "stream": "0 x y = move, 1 x y = line, 2 cx cy x y = quadratic, 3 = close; y up", "glyphs": out}


if __name__ == "__main__":
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rocksalt_glyphs.json")
    with open(dst, "w") as fh:
        json.dump(extract(sys.argv[1]), fh, separators=(",", ":"))
        fh.write("\n")
