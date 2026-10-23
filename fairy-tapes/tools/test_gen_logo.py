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


def test_colour_variants(out):
    read = lambda n: (out / n).read_text().lower()
    assert gen_logo.AMBER in read("fairy-tapes-logo-dark.svg") and gen_logo.GREY in read("fairy-tapes-logo-dark.svg")
    assert gen_logo.AMBER_LIGHT in read("fairy-tapes-logo-light.svg") and gen_logo.BG in read("fairy-tapes-logo-light.svg")
    for n in ("fairy-tapes-logo-mono-black.svg", "fairy-tapes-mark-mono-black.svg"):
        assert gen_logo.AMBER not in read(n) and gen_logo.GREY not in read(n)


def test_favicon_ico_sizes(out):
    from PIL import Image
    with Image.open(out / "favicon.ico") as im:
        assert {(16, 16), (32, 32), (48, 48)} <= set(im.info["sizes"])


def test_avatar_png_size(out):
    from PIL import Image
    with Image.open(out / "fairy-tapes-avatar.png") as im:
        assert im.size == (512, 512)
