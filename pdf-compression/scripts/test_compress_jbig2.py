#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "pillow",
#     "pymupdf",
# ]
# ///
"""Regression tests for the --jbig2 backend in compress.py.

Run with:
    uv run --no-project --with pymupdf,pillow <skill-dir>/scripts/test_compress_jbig2.py

Covers two bugs found in PR review (franklinbaldo/skills#17):

  P1: _set_jbig2_stream() reused an existing image xref without clearing
      leftover keys (/Decode, /ImageMask, ...), which could invert colors
      or turn the image into a stencil mask.

  P2: the JBIG2-vs-CCITT-G4 size comparison used the CCITT candidate's raw
      TIFF container size instead of what actually ends up embedded in the
      saved PDF (MuPDF decodes the TIFF and re-encodes on save, typically
      to FlateDecode over the raw bitmap -- a much smaller number).

Tests that need the real jbig2 binary are skipped (not failed) when it's
not on PATH, matching compress.py's own graceful-fallback behavior.
"""
import io
import os
import sys
import unittest.mock

sys.path.insert(0, os.path.dirname(__file__))
import compress
import fitz
from PIL import Image, ImageDraw

FAILURES = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if not condition:
        FAILURES.append(name)


def skip(name, reason):
    print(f"[SKIP] {name} ({reason})")


def make_bitonal_image(width=200, height=100):
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 40, 180, 60], fill=0)
    return img


def make_tiff_g4(bw_img):
    out_io = io.BytesIO()
    bw_img.save(out_io, format="TIFF", compression="group4")
    return out_io.getvalue()


def render_bw(doc, page, width, height):
    pix = page.get_pixmap(dpi=72, colorspace=fitz.csGRAY)
    decoded = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    return decoded.convert("1", dither=Image.Dither.NONE)


def build_existing_image_xref(bw_img, extra_key=None, extra_value=None):
    """Simulate an xref as it exists in a real scanned PDF before JBIG2 swap-in."""
    width, height = bw_img.size
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    gray_buf = io.BytesIO()
    bw_img.convert("L").save(gray_buf, format="JPEG")
    xref = page.insert_image(fitz.Rect(0, 0, width, height), stream=gray_buf.getvalue())
    if extra_key is not None:
        doc.xref_set_key(xref, extra_key, extra_value)
    return doc, page, xref


def test_p1_decode_array_normalized():
    if not compress.JBIG2_BIN:
        skip("p1_decode_array_normalized", "jbig2 binary not on PATH")
        return
    bw_img = make_bitonal_image()
    jbig2_bytes = compress.encode_jbig2_lossless(bw_img, make_tiff_g4(bw_img))
    if jbig2_bytes is None:
        # image too small for JBIG2 to win on size; get raw bytes directly
        # to still exercise _set_jbig2_stream's dict-normalization behavior.
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "p.pbm")
            bw_img.save(src, format="PPM")
            jbig2_bytes = subprocess.run([compress.JBIG2_BIN, "-p", src], capture_output=True, check=True).stdout

    doc, page, xref = build_existing_image_xref(bw_img, extra_key="Decode", extra_value="[1 0]")
    compress._set_jbig2_stream(doc, xref, jbig2_bytes, *bw_img.size)
    decode_after = doc.xref_get_key(xref, "Decode")
    decoded = render_bw(doc, page, *bw_img.size)
    doc.close()

    check("p1_decode_array_cleared", decode_after[0] == "null")
    check("p1_decode_array_renders_correctly", decoded.tobytes() == bw_img.tobytes())


def test_p1_imagemask_normalized():
    if not compress.JBIG2_BIN:
        skip("p1_imagemask_normalized", "jbig2 binary not on PATH")
        return
    bw_img = make_bitonal_image()
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "p.pbm")
        bw_img.save(src, format="PPM")
        jbig2_bytes = subprocess.run([compress.JBIG2_BIN, "-p", src], capture_output=True, check=True).stdout

    doc, page, xref = build_existing_image_xref(bw_img, extra_key="ImageMask", extra_value="true")
    compress._set_jbig2_stream(doc, xref, jbig2_bytes, *bw_img.size)
    imagemask_after = doc.xref_get_key(xref, "ImageMask")
    colorspace_after = doc.xref_get_key(xref, "ColorSpace")
    decoded = render_bw(doc, page, *bw_img.size)
    doc.close()

    check("p1_imagemask_cleared", imagemask_after[0] == "null")
    check("p1_colorspace_set_after_imagemask", colorspace_after == ("name", "/DeviceGray"))
    check("p1_imagemask_renders_correctly", decoded.tobytes() == bw_img.tobytes())


def test_p2_rejects_jbig2_that_only_beats_tiff_container():
    """The bug: comparing against the TIFF container size (not the real
    saved size) would accept a JBIG2 candidate that's smaller than the TIFF
    file but *larger* than what CCITT G4 actually ends up as in the saved
    PDF -- making the output bigger, contradicting the "only when smaller"
    guarantee. Force that exact gap deterministically via mocking so the
    test doesn't depend on tuning image content to hit a specific ratio.
    """
    if not compress.JBIG2_BIN:
        skip("p2_rejects_jbig2_that_only_beats_tiff_container", "jbig2 binary not on PATH")
        return
    bw_img = make_bitonal_image()
    tiff_bytes = make_tiff_g4(bw_img)
    assert len(tiff_bytes) > 100, "test assumption: TIFF container has non-trivial overhead"

    with unittest.mock.patch.object(compress, "_verify_and_measure_jbig2", return_value=(True, 90)), \
         unittest.mock.patch.object(compress, "_g4_embedded_size", return_value=50):
        # jbig2 "size" (90) beats the TIFF container size but loses to the
        # real final G4 size (50) -- must be rejected.
        result = compress.encode_jbig2_lossless(bw_img, tiff_bytes)

    check("p2_rejects_when_only_beating_tiff_not_real_g4", result is None)


def test_p2_accepts_jbig2_that_beats_real_g4_size():
    if not compress.JBIG2_BIN:
        skip("p2_accepts_jbig2_that_beats_real_g4_size", "jbig2 binary not on PATH")
        return
    bw_img = make_bitonal_image()
    tiff_bytes = make_tiff_g4(bw_img)

    with unittest.mock.patch.object(compress, "_verify_and_measure_jbig2", return_value=(True, 40)), \
         unittest.mock.patch.object(compress, "_g4_embedded_size", return_value=50):
        result = compress.encode_jbig2_lossless(bw_img, tiff_bytes)

    check("p2_accepts_when_beating_real_g4_size", result is not None)


def test_g4_embedded_size_reflects_save_time_reencoding():
    """Sanity check the premise behind P2: MuPDF re-encodes on save, so the
    TIFF container size and the actual saved size are meaningfully different
    numbers -- if they were always equal this bug wouldn't have existed.
    """
    bw_img = make_bitonal_image(1200, 1600)
    tiff_bytes = make_tiff_g4(bw_img)
    real_size = compress._g4_embedded_size(tiff_bytes, *bw_img.size)
    check("g4_embedded_size_differs_from_tiff_container_size", real_size != len(tiff_bytes))


def test_install_hint_never_promises_broken_fedora_command():
    with unittest.mock.patch.object(compress.shutil, "which", side_effect=lambda name: "/usr/bin/dnf" if name == "dnf" else None):
        hint = compress._jbig2_install_hint()
    check("install_hint_fedora_no_bad_dnf_command", "dnf install" not in hint)
    check("install_hint_fedora_mentions_no_official_package", "official repos don't package" in hint)


def test_install_hint_never_promises_broken_arch_command():
    with unittest.mock.patch.object(compress.shutil, "which", side_effect=lambda name: "/usr/bin/pacman" if name == "pacman" else None):
        hint = compress._jbig2_install_hint()
    check("install_hint_arch_no_bad_pacman_dash_s_command", "pacman -S jbig2enc" not in hint and "pacman -S --noconfirm jbig2enc" not in hint)
    check("install_hint_arch_mentions_aur", "AUR" in hint)


def test_install_hint_apt_still_direct():
    with unittest.mock.patch.object(compress.shutil, "which", side_effect=lambda name: "/usr/bin/apt-get" if name == "apt-get" else None):
        hint = compress._jbig2_install_hint()
    check("install_hint_apt_command_present", "apt-get install -y jbig2" in hint)


def test_end_to_end_matches_g4_pixels():
    """Full compress_pdf() run with --jbig2 must render pixel-identical to
    the G4-only run for every page (the whole point of the roundtrip gate)."""
    if not compress.JBIG2_BIN:
        skip("end_to_end_matches_g4_pixels", "jbig2 binary not on PATH")
        return
    import random
    import tempfile

    random.seed(7)
    W, H = 900, 1100
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)
    y = 60
    while y < H - 60:
        x = 60
        while x < W - 60:
            w = random.randint(8, 20)
            if random.random() < 0.7:
                draw.rectangle([x, y, x + w, y + 16], fill=0)
            x += w + 6
        y += 26

    with tempfile.TemporaryDirectory() as tmp:
        src_pdf = os.path.join(tmp, "source.pdf")
        g4_pdf = os.path.join(tmp, "g4.pdf")
        jbig2_pdf = os.path.join(tmp, "jbig2.pdf")

        doc = fitz.open()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        page = doc.new_page(width=W, height=H)
        page.insert_image(fitz.Rect(0, 0, W, H), stream=buf.getvalue())
        doc.save(src_pdf)
        doc.close()

        compress.compress_pdf(src_pdf, g4_pdf, mode="bw", use_jbig2=False)
        compress.compress_pdf(src_pdf, jbig2_pdf, mode="bw", use_jbig2=True)

        d1 = fitz.open(g4_pdf)
        d2 = fitz.open(jbig2_pdf)
        p1 = d1[0].get_pixmap(dpi=72, colorspace=fitz.csGRAY)
        p2 = d2[0].get_pixmap(dpi=72, colorspace=fitz.csGRAY)
        i1 = Image.frombytes("L", (p1.width, p1.height), p1.samples)
        i2 = Image.frombytes("L", (p2.width, p2.height), p2.samples)
        pixel_match = i1.tobytes() == i2.tobytes()
        jbig2_smaller_or_equal = os.path.getsize(jbig2_pdf) <= os.path.getsize(g4_pdf)
        d1.close()
        d2.close()

    check("end_to_end_pixel_identical", pixel_match)
    check("end_to_end_jbig2_not_larger_than_g4_output", jbig2_smaller_or_equal)


def test_missing_binary_falls_back_gracefully():
    original = compress.JBIG2_BIN
    compress.JBIG2_BIN = None
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            src_pdf = os.path.join(tmp, "source.pdf")
            out_pdf = os.path.join(tmp, "out.pdf")
            doc = fitz.open()
            page = doc.new_page(width=200, height=100)
            buf = io.BytesIO()
            make_bitonal_image().convert("RGB").save(buf, format="JPEG")
            page.insert_image(fitz.Rect(0, 0, 200, 100), stream=buf.getvalue())
            doc.save(src_pdf)
            doc.close()
            compress.compress_pdf(src_pdf, out_pdf, mode="bw", use_jbig2=True)
            check("missing_binary_still_produces_output", os.path.exists(out_pdf))
    finally:
        compress.JBIG2_BIN = original


def main():
    tests = [
        test_p1_decode_array_normalized,
        test_p1_imagemask_normalized,
        test_p2_rejects_jbig2_that_only_beats_tiff_container,
        test_p2_accepts_jbig2_that_beats_real_g4_size,
        test_g4_embedded_size_reflects_save_time_reencoding,
        test_install_hint_never_promises_broken_fedora_command,
        test_install_hint_never_promises_broken_arch_command,
        test_install_hint_apt_still_direct,
        test_end_to_end_matches_g4_pixels,
        test_missing_binary_falls_back_gracefully,
    ]
    for t in tests:
        print(f"\n--- {t.__name__} ---")
        t()

    print(f"\n{len(FAILURES)} failure(s).")
    if FAILURES:
        for name in FAILURES:
            print(f"  FAILED: {name}")
        sys.exit(1)
    print("All tests passed (or skipped without a jbig2 binary).")


if __name__ == "__main__":
    main()
