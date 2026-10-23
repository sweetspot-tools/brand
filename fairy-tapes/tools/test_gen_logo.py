"""Checks of the generated brand files: pure paths, expected colours, sizes."""
import os
import xml.etree.ElementTree as ET

import pytest

import gen_logo

NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("brand")
    gen_logo.build(str(d))
    return d


def test_all_files_written(out):
    assert sorted(os.listdir(out)) == sorted(gen_logo.FILES)


@pytest.mark.parametrize("name", [n for n in gen_logo.FILES if n.endswith(".svg")])
def test_svg_is_paths_only(out, name):
    root = ET.parse(out / name).getroot()
    assert root.tag == NS + "svg" and root.get("viewBox")
    tags = {el.tag.replace(NS, "") for el in root.iter()}
    assert not tags & {"text", "image", "style", "font"}


def colours(path):
    return {c.lower() for el in ET.parse(path).getroot().iter() for c in (el.get("fill"), el.get("stroke"))
            if c and c.startswith("#")}


@pytest.mark.parametrize("kind", ["logo", "mark"])
def test_colour_variants(out, kind):
    dark, light = colours(out / f"fairy-tapes-{kind}-dark.svg"), colours(out / f"fairy-tapes-{kind}-light.svg")
    assert {gen_logo.AMBER, gen_logo.GREY, gen_logo.TAPE, gen_logo.INK} <= dark
    assert {gen_logo.AMBER_LIGHT, gen_logo.BG, gen_logo.TAPE, gen_logo.TAPE_EDGE} <= light
    assert colours(out / f"fairy-tapes-{kind}-mono-black.svg") == {gen_logo.BLACK}
    assert colours(out / f"fairy-tapes-{kind}-mono-white.svg") == {gen_logo.WHITE}


def test_label_glyphs_cover_the_label():
    assert set(gen_logo.LABEL) <= set(gen_logo.load_label_glyphs()["glyphs"])


def test_label_is_on_the_mark(out):
    # the hand-written label is the only paths drawn in ink on the dark mark
    root = ET.parse(out / "fairy-tapes-mark-dark.svg").getroot()
    ink = [el for el in root.iter(f"{NS}path") if (el.get("fill") or "").lower() == gen_logo.INK]
    assert ink and all(len(el.get("d")) > 500 for el in ink)


def test_favicon_ico_sizes(out):
    from PIL import Image
    with Image.open(out / "favicon.ico") as im:
        assert {(16, 16), (32, 32), (48, 48)} <= set(im.info["sizes"])


def test_avatar_png_size(out):
    from PIL import Image
    with Image.open(out / "fairy-tapes-avatar.png") as im:
        assert im.size == (512, 512)
